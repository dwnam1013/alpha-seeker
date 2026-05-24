import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import minimize
import feedparser
import logging
import time

# --- [1. 로그 및 환경 설정] ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Alpha-Seeker Pro Enterprise", layout="wide")

# --- [2. 상세 스타일링] ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117 !important; }
    .finviz-logo { font-family: 'Arial Black', sans-serif; font-size: 40px; color: #ffffff; padding: 10px; }
    .finviz-logo span { color: #ff4b4b; }
    .report-card { background: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="finviz-logo">ALPHA<span>SEEKER</span>.com</div>', unsafe_allow_html=True)
st.caption("2026 Enterprise Quantitative Intelligence Platform")

# --- [3. 104개 종목 마스터 풀 관리] ---
WATCH_LIST = {
    "Technology": ["NVDA", "AVGO", "AMD", "ARM", "MRVL", "NVTS", "WOLF", "QCOM", "ADI", "MU", "ASML", "AMAT", "LRCX", "UCTT", "CAMT", "KLAC", "SNPS", "CDNS", "MSFT", "NOW", "GWRE", "CRWD", "PANW", "NET", "ORCL", "CRM", "DDOG", "PLTR"],
    "Communication": ["GOOGL", "META", "SNAP", "PINS", "NFLX", "DIS", "ROKU", "SPOT", "TTWO", "EA", "TMUS", "VZ", "T", "ASTS"],
    "Consumer": ["AMZN", "MELI", "ETSY", "EBAY", "TSLA", "RIVN", "CVNA", "PDD", "LULU", "DECK", "NKE", "BABA", "LI", "LCID", "UBER", "LYFT", "BKNG", "ABNB"]
}
FLAT_LIST = sorted(list(set([t for sub in WATCH_LIST.values() for t in sub])))

# --- [4. 데이터 연산 엔진 모듈] ---
def fetch_ticker_data(ticker):
    """실시간 야후 파이낸스 데이터 정밀 수집"""
    try:
        s = yf.Ticker(ticker)
        hist = s.history(period="1y")
        info = s.info
        return s, hist, info
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return None, None, None

def get_option_chain_analysis(s):
    """파생상품 미결제약정 정밀 분석"""
    try:
        exp = s.options[0]
        chain = s.option_chain(exp)
        call_oi = chain.calls['openInterest'].sum()
        put_oi = chain.puts['openInterest'].sum()
        return put_oi / (call_oi if call_oi > 0 else 1)
    except: return 1.0

# --- [5. 메뉴 로직 및 대시보드] ---
menu = st.sidebar.selectbox("메뉴", ["시장 분석", "퀀트 스크리너", "포트폴리오", "전략 테스트"])

if menu == "시장 분석":
    ticker = st.text_input("분석할 종목", "NVDA").upper()
    s, hist, info = fetch_ticker_data(ticker)
    if s:
        c1, c2 = st.columns([3, 1])
        with c1:
            fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.write("### 주요 지표")
            st.metric("현재가", info.get('currentPrice', 0))
            st.write("#### 최신 뉴스")
            for n in feedparser.parse(f"https://news.google.com/rss/search?q={ticker}").entries[:5]:
                st.write(f"- [{n.title}]({n.link})")

elif menu == "퀀트 스크리너":
    if st.button("전체 종목 퀀트 스캔 시작"):
        prog = st.progress(0)
        results = []
        for i, t in enumerate(FLAT_LIST):
            s, _, info = fetch_ticker_data(t)
            if s:
                pcr = get_option_chain_analysis(s)
                score = (info.get('trailingPE', 0) * 0.1) + (info.get('returnOnEquity', 0) * 100)
                results.append({"Ticker": t, "Score": score, "PCR": pcr})
            prog.progress((i+1)/len(FLAT_LIST))
        st.dataframe(pd.DataFrame(results).sort_values("Score", ascending=False))

elif menu == "포트폴리오":
    st.write("### MPT 최적화 엔진")
    data = yf.download(FLAT_LIST, period="1y")['Adj Close']
    ret = data.pct_change().dropna()
    cov = ret.cov() * 252
    def obj(w): return np.sqrt(w.T @ cov @ w)
    res = minimize(obj, [1/len(FLAT_LIST)]*len(FLAT_LIST), bounds=[(0, 0.4)]*len(FLAT_LIST), constraints={'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    st.bar_chart(pd.Series(res.x, index=FLAT_LIST).sort_values(ascending=False))

elif menu == "전략 테스트":
    st.write("### 이동평균 백테스트")
    s, l = st.slider("단기/장기 기간", 5, 200, (20, 100))
    ticker = st.text_input("백테스트 종목", "NVDA").upper()
    df = yf.download(ticker, period="2y")
    df['SMA_S'] = df['Close'].rolling(s).mean()
    df['SMA_L'] = df['Close'].rolling(l).mean()
    # 108번 줄을 삭제하고 아래 내용으로 교체
signal = pd.Series(np.where(df['SMA_S'] > df['SMA_L'], 1, 0), index=df.index)
df['Ret'] = df['Close'].pct_change() * signal
    st.line_chart(df['Ret'].cumsum())
