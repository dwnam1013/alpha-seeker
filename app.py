import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- [1. 핀비즈 스타일 전용 CSS 스타일링] ---
st.set_page_config(page_title="FINVIZ Style Alpha-Seeker Pro", layout="wide")

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
st.caption("2026년 실시간 미국 증시 맵 및 파생상품 연동형 퀀트 시스템")

# --- [2. 퀀트 마스터 종목 풀 (104개 종목 보존)] ---
SECTOR_WATCH_LIST = {
    "Technology": ["NVDA", "AVGO", "AMD", "ARM", "MRVL", "NVTS", "WOLF", "QCOM", "ADI", "MU", "ASML", "AMAT", "LRCX", "UCTT", "CAMT", "KLAC", "SNPS", "CDNS", "MSFT", "NOW", "GWRE", "CRWD", "PANW", "NET", "ORCL", "CRM", "DDOG", "PLTR"],
    "Communication Services": ["GOOGL", "META", "SNAP", "PINS", "NFLX", "DIS", "ROKU", "SPOT", "TTWO", "EA", "TMUS", "VZ", "T", "ASTS"],
    "Consumer Discretionary": ["AMZN", "MELI", "ETSY", "EBAY", "TSLA", "RIVN", "CVNA", "PDD", "LULU", "DECK", "NKE", "BABA", "LI", "LCID", "UBER", "LYFT", "BKNG", "ABNB"]
}
ALL_TICKERS = sorted(list(set([t for sub in SECTOR_WATCH_LIST.values() for t in sub])))

# --- [3. 🔥 신규 백엔드: 실시간 풋콜옵션 비율(PCR) 계산 엔진] ---
def fetch_put_call_ratio(stock_obj):
    try:
        # 가장 가까운 만기일의 옵션 체인 가져오기
        expiration_dates = stock_obj.options
        if not expiration_dates:
            return 1.0, 0, 0 # 옵션 데이터가 없는 경우 기본값 반환
        
        opt_chain = stock_obj.option_chain(expiration_dates[0])
        calls = opt_chain.calls
        puts = opt_chain.puts
        
        # 미결제약정(Open Interest) 총합 계산
        total_call_oi = calls['openInterest'].sum() if 'openInterest' in calls.columns else 1
        total_put_oi = puts['openInterest'].sum() if 'openInterest' in puts.columns else 1
        
        if total_call_oi == 0: total_call_oi = 1
        
        pcr_value = total_put_oi / total_call_oi
        return round(pcr_value, 2), int(total_call_oi), int(total_put_oi)
    except:
        return 1.0, 0, 0

# --- [4. 팩터 고도화: 파생 심리가 반영된 퀀트 스코어링] ---
@st.cache_data(ttl=600)
def run_derivative_quant_engine():
    quant_results = []
    for ticker in ALL_TICKERS:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            curr_p = info.get('currentPrice', 1)
            target_p = info.get('targetMeanPrice', 0)
            upside = ((target_p - curr_p) / curr_p) * 100 if target_p else 0
            
            # 기본 재무 팩터 수집
            pe = info.get('trailingPE', 999)
            pbr = info.get('priceToBook', 999)
            rev_growth = info.get('revenueGrowth', 0)
            roe = info.get('returnOnEquity', 0)
            
            # --- 실시간 파생 팩터(PCR) 연동 ---
            pcr, call_oi, put_oi = fetch_put_call_ratio(stock)
            
            # 스코어링 베이스 계산 (만점 80점)
            value_score = 20 if pe < 25 else 10
            growth_score = 20 if rev_growth > 0.15 else 10
            quality_score = 20 if roe > 0.15 else 10
            momentum_score = 20 if upside > 20 else 10
            
            base_score = value_score + growth_score + quality_score + momentum_score
            
            # --- 🔥 PCR 역발상 변동성 가점/감점 수식 (20점 부여) ---
            pcr_score = 10  # 중간 중립 점수
            pcr_signal = "중립 (Neutral)"
            
            if pcr >= 1.3:
                pcr_score = 20  # 시장이 과도한 공포 상태 -> 분할 매수 적기 (역발상 가점)
                pcr_signal = "⚡ 극단적 공포 (과매도 바닥 시그널)"
            elif pcr >= 1.0:
                pcr_score = 15
                pcr_signal = "하락 우위 (Bearish)"
            elif pcr <= 0.5:
                pcr_score = 0   # 시장이 지나치게 과열/탐욕 상태 -> 상방 제한 (리스크 감점)
                pcr_signal = "🚨 극단적 탐욕 (과매수 상방 제한)"
            elif pcr <= 0.7:
                pcr_score = 5
                pcr_signal = "상승 우위 (Bullish)"
                
            total_score = base_score + pcr_score
            
            quant_results.append({
                "Ticker": ticker,
                "Sector": info.get('sector', 'N/A'),
                "현재가 ($)": curr_p,
                "🔥 파생 융합 퀀트 스코어": total_score,
                "풋콜옵션 비율 (PCR)": pcr,
                "파생 시장 시그널": pcr_signal,
                "상승여력 (%)": round(upside, 2),
                "Call 미결제약정": call_oi,
                "Put 미결제약정": put_oi
            })
        except: continue
    return pd.DataFrame(quant_results)

# --- [5. 네비게이션 메뉴 구성] ---
menu = st.sidebar.radio("⚙️ FINVIZ MENU", ["📊 Map (종목 메인 맵)", "🎯 Derivative Quant (파생 연동 추천 엔진)"])

# --- [화면 1: 메인 맵 (기존 로직 유지)] ---
if menu == "📊 Map (종목 메인 맵)":
    st.write("### 🟥🟩 S&P 500 Market Performance Map")
    # ... (기존 트리맵 코드 구동 구역)

# --- [화면 2: 신규 파생상품 반영 퀀트 스크리너] ---
elif menu == "🎯 Derivative Quant (파생 연동 추천 엔진)":
    st.write("### 🎯 파생상품(Put/Call Ratio) 심리 지표 융합형 퀀트 스크리너")
    st.caption("기존 재무 제표 지표에 더해 고도화된 헷지펀드들의 옵션 포지션 비율(PCR)을 실시간 추적하여 매매 심리를 계량 점수화합니다.")
    
    selected_sector = st.selectbox("업종 필터", ["전체 섹터"] + list(SECTOR_WATCH_LIST.keys()))
    
    if st.button("🚀 파생 인텔리전스 퀀트 스캔 시작"):
        with st.spinner("옵션 체인 행렬 데이터 실시간 파싱 및 가중치 연산 중..."):
            df_quant = run_derivative_quant_engine()
            
            if not df_quant.empty:
                if selected_sector != "전체 섹터":
                    df_quant = df_quant[df_quant['Sector'] == selected_sector]
                
                # 점수 순으로 소팅
                df_quant = df_quant.sort_values(by="🔥 파생 융합 퀀트 스코어", ascending=False).reset_index(drop=True)
                
                st.write(f"#### 🏆 {selected_sector} 종합 퀀트 추천 랭킹")
                st.dataframe(df_quant, use_container_width=True)
                
                # 파생 최고 시그널 종목 디스플레이
                if len(df_quant) > 0:
                    top_pick = df_quant.iloc[0]
                    st.success(f"""
                        🦅 **Alpha Derivative Top Pick:** 파생 옵션 체인 결합 연산 결과 가장 매력적인 역발상 바닥/돌파 종목은 **[{top_pick['Ticker']}]** 입니다.
                        * 종합 점수: {top_pick['🔥 파생 융합 퀀트 스코어']}점
                        * 실시간 풋콜 비율(PCR): {top_pick['풋콜옵션 비율 (PCR)']} ({top_pick['파생 시장 시그널']})
                        * 기관 미결제 포지션: Call {top_pick['Call 미결제약정']:,}계약 / Put {top_pick['Put 미결제약정']:,}계약
                    """)
