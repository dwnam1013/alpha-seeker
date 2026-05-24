import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.optimize import minimize
import feedparser
import time

# --- [1. 스타일링 설정] ---
st.set_page_config(page_title="Alpha-Seeker Pro Full-Scale Edition", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #11151a !important; color: #e1e3e6 !important; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #21262d; }
    .finviz-logo { font-family: 'Arial Black', sans-serif; font-size: 32px; color: #ffffff; letter-spacing: -1px; }
    .finviz-logo span { color: #ff4b4b; }
    div.stButton > button { background-color: #21262d !important; color: #c9d1d9 !important; border: 1px solid #30363d !important; border-radius: 4px; }
    div.stButton > button:hover { border-color: #8b949e !important; color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="finviz-logo">ALPHA<span>SEEKER</span>.com</div>', unsafe_allow_html=True)

# --- [2. 상세 종목 데이터 관리 (104개)] ---
SECTOR_WATCH_LIST = {
    "Technology": ["NVDA", "AVGO", "AMD", "ARM", "MRVL", "NVTS", "WOLF", "QCOM", "ADI", "MU", "ASML", "AMAT", "LRCX", "UCTT", "CAMT", "KLAC", "SNPS", "CDNS", "MSFT", "NOW", "GWRE", "CRWD", "PANW", "NET", "ORCL", "CRM", "DDOG", "PLTR"],
    "Communication Services": ["GOOGL", "META", "SNAP", "PINS", "NFLX", "DIS", "ROKU", "SPOT", "TTWO", "EA", "TMUS", "VZ", "T", "ASTS"],
    "Consumer Discretionary": ["AMZN", "MELI", "ETSY", "EBAY", "TSLA", "RIVN", "CVNA", "PDD", "LULU", "DECK", "NKE", "BABA", "LI", "LCID", "UBER", "LYFT", "BKNG", "ABNB"]
}
ALL_TICKERS = sorted(list(set([t for sub in SECTOR_WATCH_LIST.values() for t in sub])))

# --- [3. 정교화된 백엔드 데이터 함수] ---
def get_detailed_news(ticker):
    """구글 뉴스 RSS를 상세 파싱"""
    url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:8]:
        items.append({"title": entry.title, "link": entry.link})
    return items

def get_option_metrics(ticker):
    """옵션 체인 데이터 연산"""
    try:
        s = yf.Ticker(ticker)
        exp = s.options[0]
        opt = s.option_chain(exp)
        c_oi = opt.calls['openInterest'].sum()
        p_oi = opt.puts['openInterest'].sum()
        pcr = p_oi / (c_oi if c_oi > 0 else 1)
        return round(pcr, 3), int(c_oi), int(p_oi)
    except:
        return 1.0, 0, 0

def calculate_advanced_score(info, pcr):
    """다중 팩터 스코어링 수식"""
    pe = info.get('trailingPE', 999)
    roe = info.get('returnOnEquity', 0)
    rev_g = info.get('revenueGrowth', 0)
    target = info.get('targetMeanPrice', 0)
    curr = info.get('currentPrice', 1)
    upside = ((target - curr) / curr) * 100 if target else 0
    
    # 세부 점수 가중치 산출
    s = 0
    s += 20 if pe < 25 else 10
    s += 20 if rev_g > 0.15 else 10
    s += 20 if roe > 0.15 else 10
    s += 20 if upside > 20 else 10
    # 파생 심리 가점
    if pcr >= 1.3: s += 20
    elif pcr <= 0.5: s -= 10
    return s

# --- [4. 메뉴 구현] ---
menu = st.sidebar.radio("SYSTEM MENU", ["📊 대시보드", "🎯 파생 퀀트 스크리너", "⚖️ 포트폴리오 최적화", "🧪 백테스팅"])
ticker_input = st.sidebar.text_input("분석할 종목", value="NVDA").upper()

if menu == "📊 대시보드":
    st.write(f"### {ticker_input} 분석")
    col1, col2 = st.columns([2, 1])
    with col1:
        data = yf.download(ticker_input, period="6mo")
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        for news in get_detailed_news(ticker_input):
            st.markdown(f"[{news['title']}]({news['link']})")

elif menu == "🎯 파생 퀀트 스크리너":
    if st.button("스캔 시작"):
        res = []
        for t in ALL_TICKERS:
            try:
                s = yf.Ticker(t)
                pcr, co, po = get_option_metrics(s)
                sc = calculate_advanced_score(s.info, pcr)
                res.append({"Ticker": t, "Score": sc, "PCR": pcr})
            except: continue
        st.dataframe(pd.DataFrame(res).sort_values("Score", ascending=False))

elif menu == "⚖️ 포트폴리오 최적화":
    st.write("### MPT 최적화 엔진")
    data = yf.download(ALL_TICKERS, period="1y")['Adj Close']
    ret = data.pct_change().dropna()
    cov = ret.cov() * 252
    def obj(w): return np.sqrt(w.T @ cov @ w)
    res = minimize(obj, [1/len(ALL_TICKERS)]*len(ALL_TICKERS), bounds=[(0, 0.5)]*len(ALL_TICKERS), constraints={'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    st.bar_chart(pd.Series(res.x, index=ALL_TICKERS))

elif menu == "🧪 백테스팅":
    s, l = st.slider("기간", 5, 200, (20, 100))
    df = yf.download(ticker_input, period="2y")
    df['SMA_S'] = df['Close'].rolling(s).mean()
    df['SMA_L'] = df['Close'].rolling(l).mean()
    df['Ret'] = df['Close'].pct_change() * np.where(df['SMA_S'] > df['SMA_L'], 1, 0)
    st.line_chart(df['Ret'].cumsum())
