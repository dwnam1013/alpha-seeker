import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import minimize

# 기본 설정
st.set_page_config(page_title="FINVIZ Alpha-Seeker Pro", layout="wide")
st.title("📊 FINVIZ Alpha-Seeker Pro: 퀀트 터미널")

# 종목 풀
SECTOR_WATCH_LIST = {"Tech": ["NVDA", "MSFT", "AAPL", "AMD"], "Finance": ["JPM", "GS", "BAC"]}
ALL_TICKERS = sorted(list(set([t for sub in SECTOR_WATCH_LIST.values() for t in sub])))

# 메뉴
menu = st.sidebar.radio("MENU", ["🎯 Quant Screener", "📈 Quant Chart", "⚖️ Portfolio Optimizer"])

if menu == "🎯 Quant Screener":
    st.write("### 🎯 멀티팩터 알고리즘 추천")
    if st.button("스캔 시작"):
        st.write("종목 분석 데이터를 로딩합니다...")

elif menu == "📈 Quant Chart":
    st.write("### 📈 기술적 지표 분석")
    ticker = st.selectbox("종목 선택", ALL_TICKERS)
    df = yf.Ticker(ticker).history(period="1y")
    st.line_chart(df['Close'])

elif menu == "⚖️ Portfolio Optimizer":
    st.write("### ⚖️ 최적 포트폴리오 비중")
    st.info("선택한 종목들의 변동성을 최소화하는 비중을 계산합니다.")
