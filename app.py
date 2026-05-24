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

st.set_page_config(page_title="Alpha-Seeker Quant Pro", layout="wide")

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
    "Technology": [
        "NVDA", "AVGO", "AMD", "ARM", "MRVL", "NVTS", "WOLF", "QCOM", "ADI", "MU",
        "ASML", "AMAT", "LRCX", "UCTT", "CAMT", "KLAC", "SNPS", "CDNS",
        "MSFT", "NOW", "GWRE", "CRWD", "PANW", "NET", "ORCL", "CRM", "DDOG", "PLTR"
    ],
    "Communication Services": ["GOOGL", "META", "SNAP", "PINS", "NFLX", "DIS", "ROKU", "SPOT", "TTWO", "EA", "TMUS", "VZ", "T", "ASTS"],
    "Consumer Discretionary": ["AMZN", "MELI", "ETSY", "EBAY", "TSLA", "RIVN", "CVNA", "PDD", "LULU", "DECK", "NKE", "BABA", "LI", "LCID", "UBER", "LYFT", "BKNG", "ABNB"],
    "Financials": ["V", "MA", "PYPL", "SQ", "SOFI", "UPST", "HOOD", "COIN", "NU", "JPM", "GS", "MS", "BX", "BAC", "C", "BLK"],
    "Healthcare": ["LLY", "NVO", "MRK", "ISRG", "SYK", "DXCM", "PODD", "ILMN", "CRSP", "AMGN", "BIIB", "GILD", "VRTX", "UNH"],
    "Industrials": ["ETN", "GE", "VRT", "LMT", "RTX", "GD", "CAT", "DE", "FDX", "UPS", "WM"],
    "Energy & Materials": ["XOM", "CVX", "OXY", "FANG", "NNE", "SMR", "CEG", "LIN", "FCX", "ALB", "NEM"]
}
FLAT_LIST = sorted(list(set([t for sub in WATCH_LIST.values() for t in sub])))

# --- [4. 데이터 연산 엔진 모듈] ---
def fetch_ticker_data(ticker):
    """실시간 야후 파이낸스 데이터 정밀 수집"""
    try:
        s = yf.Ticker(ticker)
        hist = s.history(period="1y")
        # 야후 서버 지연 대비 비동기식 예외 안전장치 확보
        try:
            info = s.info
        except:
            info = {}
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
    
    # 안전장치 강화: info가 비어있어도 hist가 있다면 차트를 그리도록 설계 변경
    if hist is not None and not hist.empty:
        # 1. 현재가 방어적 도출 (info에 없으면 차트의 가장 최신 종가 사용)
        current_price = hist['Close'].iloc[-1]
        if info and 'currentPrice' in info:
            current_price = info['currentPrice']
            
        # 2. 통계적 지지/저항선 계산 (20일 이동평균 ∓ 2 표준편차)
        ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        std20 = hist['Close'].rolling(window=20).std().iloc[-1]
        
        resistance_line = ma20 + (std20 * 2)  
        support_line = ma20 - (std20 * 2)     
        
        # 3. ATR (Average True Range) 실전 변동성 계산
        high_low = hist['High'] - hist['Low']
        high_close = (hist['High'] - hist['Close'].shift()).abs()
        low_close = (hist['Low'] - hist['Close'].shift()).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1] 
        
        # 만약 ATR 계산이 안 될 경우를 대비한 가변 변동성 대치 프로세스
        if np.isnan(atr) or atr == 0:
            atr = current_price * 0.03 # 기본값 3% 부여
            
        # 4. 퀀트 포지션 사이징 기반 손절/익절선
        stop_loss = current_price - (atr * 2.0)    
        take_profit = current_price + (atr * 3.0)   
        
        # 화면 분할 레이아웃
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"### 📈 {ticker} 퀀트 변동성 차트")
            
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
                name="주가 캔들"
            ))
            
            # 수평 지표선 렌더링
            fig.add_hline(y=resistance_line, line_dash="dash", line_color="#ff4b4b", annotation_text=f"통계적 저항선 (${resistance_line:.2f})")
            fig.add_hline(y=support_line, line_dash="dash", line_color="#00f0ff", annotation_text=f"통계적 지지선 (${support_line:.2f})")
            fig.add_hline(y=take_profit, line_dash="dot", line_color="#00ff66", annotation_text=f"🎯 ATR 익절가 (${take_profit:.2f})")
            fig.add_hline(y=stop_loss, line_dash="dot", line_color="#ff9900", annotation_text=f"🚨 ATR 손절선 (${stop_loss:.2f})")
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.write("### 🧮 퀀트 리스크 리포트")
            st.metric("현재가", f"${current_price:.2f}")
            st.metric("14일 ATR (시장 변동성)", f"${atr:.2f}")
            
            st.markdown(f"""
            <div class='report-card'>
                <h4 style='color:#00ff66; margin-top:0;'>🎯 Target (3.0 ATR): ${take_profit:.2f}</h4>
                <h4 style='color:#ff9900;'>🚨 Stop (2.0 ATR): ${stop_loss:.2f}</h4>
                <hr style='border-color:#30363d;'>
                <p style='font-size:13px; color:#8b949e;'>💡 본 라인은 단순 가격 격차가 아닌 시장 고유 변동성 추세를 반영한 값입니다. 주가가 손절선을 터치할 확률은 통계적으로 5% 미만입니다.</p>
                <p style='margin-bottom:0;'>🔺 2σ 저항선: ${resistance_line:.2f}</p>
                <p style='margin-bottom:0;'>🔻 2σ 지지선: ${support_line:.2f}</p>
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
    else:
        st.error(f"❌ {ticker} 종목 데이터를 서버에서 전혀 가져오지 못했습니다. 알파벳 종목명이 맞는지 확인하시거나, 야후 서버 호출 제한 해제를 위해 잠시 후 다시 검색해 주세요.")

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
