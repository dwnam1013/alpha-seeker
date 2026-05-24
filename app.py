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

# --- [3. 104개 종목 마스터 풀 관리 (오타 수정 완료)] ---
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
st.sidebar.write(f"📍 현재 메뉴: {menu}")

if menu == "시장 분석":
    ticker = st.text_input("분석할 종목", "NVDA").upper()
    s, hist, info = fetch_ticker_data(ticker)
    
    if s and hist is not None and not hist.empty:
        # --- [트레이딩 핵심 선행 지표 계산] ---
        current_price = info.get('currentPrice', hist['Close'].iloc[-1])
        
        # 최근 20일간의 최고가/최저가 기준으로 저항선/지지선 도출
        recent_hist = hist.tail(20)
        resistance_line = recent_hist['High'].max()
        support_line = recent_hist['Low'].min()
        
        # 최근 20일 표준편차를 활용한 정밀 손절/익절선 계산
        volatility = recent_hist['Close'].pct_change().std() * current_price
        stop_loss = current_price - (volatility * 1.5)
        take_profit = current_price + (volatility * 2.0)
        
        # 화면 분할 레이아웃
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"### 📈 {ticker} 차트 및 기술적 기준선")
            
            # 메인 캔들스틱 차트 생성
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
                name="주가 캔들"
            ))
            
            # 지지/저항/손절/익절 지표선을 수평선으로 가시화
            fig.add_hline(y=resistance_line, line_dash="dash", line_color="#ff4b4b", annotation_text=f"저항선 (${resistance_line:.2f})")
            fig.add_hline(y=support_line, line_dash="dash", line_color="#00f0ff", annotation_text=f"지지선 (${support_line:.2f})")
            fig.add_hline(y=take_profit, line_dash="dot", line_color="#00ff66", annotation_text=f"🎯 목표가(익절) (${take_profit:.2f})")
            fig.add_hline(y=stop_loss, line_dash="dot", line_color="#ff9900", annotation_text=f"🚨 손절선 (${stop_loss:.2f})")
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.write("### 📊 실시간 트레이딩 가이드")
            st.metric("현재가", f"${current_price:.2f}")
            
            # 정보 카드 배치
            st.markdown(f"""
            <div class='report-card'>
                <h4 style='color:#00ff66;'>🎯 익절 목표: ${take_profit:.2f}</h4>
                <h4 style='color:#ff4b4b;'>🚨 손절 기준: ${stop_loss:.2f}</h4>
                <hr style='border-color:#30363d;'>
                <p>📈 주요 저항선: ${resistance_line:.2f}</p>
                <p>📉 주요 지지선: ${support_line:.2f}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("#### 최신 뉴스")
            try:
                news_feed = feedparser.parse(f"https://news.google.com/rss/search?q={ticker}+stock&hl=ko&gl=KR")
                if news_feed.entries:
                    for n in news_feed.entries[:4]:
                        st.write(f"- [{n.title}]({n.link})")
                else:
                    st.write("가져올 수 있는 최신 뉴스가 없습니다.")
            except Exception as news_err:
                st.write("⚠️ 뉴스 서버 피드를 일시적으로 불러올 수 없습니다.")

elif menu == "퀀트 스크리너":
    if st.button("전체 종목 퀀트 스캔 시작"):
        prog = st.progress(0)
        results = []
        for i, t in enumerate(FLAT_LIST):
            time.sleep(0.1)
            s, _, info = fetch_ticker_data(t)
            if s and info and 'trailingPE' in info:
                pcr = get_option_chain_analysis(s)
                score = (info.get('trailingPE', 0) * 0.1) + (info.get('returnOnEquity', 0) * 100)
                results.append({"Ticker": t, "Score": score, "PCR": pcr})
            prog.progress((i+1)/len(FLAT_LIST))
            
        df_results = pd.DataFrame(results)
        if not df_results.empty:
            st.dataframe(df_results.sort_values("Score", ascending=False), use_container_width=True)
        else:
            st.warning("데이터 수집에 실패했습니다. 잠시 후 다시 시도하세요.")

elif menu == "포트폴리오":
    st.write("### MPT 최적화 엔진")
    df_download = yf.download(FLAT_LIST, period="1y")
    if 'Close' in df_download.columns:
        data = df_download['Close']
        if not data.empty:
            ret = data.pct_change().dropna()
            cov = ret.cov() * 252
            def obj(w): return np.sqrt(w.T @ cov @ w)
            res = minimize(obj, [1/len(FLAT_LIST)]*len(FLAT_LIST), bounds=[(0, 0.4)]*len(FLAT_LIST), constraints={'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
            st.bar_chart(pd.Series(res.x, index=FLAT_LIST).sort_values(ascending=False))
    else:
        st.error("데이터 셋을 생성할 수 없습니다.")

elif menu == "전략 테스트":
    st.write("### 이동평균 백테스트")
    s, l = st.slider("단기/장기 기간", 5, 200, (20, 100))
    ticker = st.text_input("백테스트 종목", "NVDA").upper()
    df = yf.download(ticker, period="2y")
    if not df.empty:
        df['SMA_S'] = df['Close'].rolling(s).mean()
        df['SMA_L'] = df['Close'].rolling(l).mean()
        signal = pd.Series(np.where(df['SMA_S'] > df['SMA_L'], 1, 0), index=df.index)
        df['Ret'] = df['Close'].pct_change() * signal
        st.line_chart(df['Ret'].cumsum())
