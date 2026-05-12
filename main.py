import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="Q_Alpha v2.0 Dashboard", layout="wide")
st.title("🚀 Q_Alpha v2.0 Real-time Scanner")

# 2. 종목 리스트 (질문자님 전용 15개 종목)
TICKERS = ['FITB', 'NTRS', 'LNT', 'PAA', 'MO', 'SBUX', 'CAKE', 'ADAM', 'BIIB', 'WERN', 'HCSG', 'FFBC', 'VLY', 'MNST', 'HAS']

@st.cache_data(ttl=3600) # 1시간마다 데이터 갱신
def get_data(ticker):
    df = yf.download(ticker, period='1y', interval='1d')
    # 지표 계산
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    
    # ATR 계산
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['ATR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
    
    # Q_Alpha v2.0 점수화
    df['P_Score'] = ((df['Close'] > df['SMA20']) & (df['SMA20'] > df['SMA50'])).astype(int) * 0.4
    df['A_Score'] = (1 - (np.abs(df['Close'] - df['SMA20']) / df['SMA20'])).clip(0, 1) * 0.4
    df['V_Score'] = (df['Volume'] > df['Volume'].rolling(20).mean()).astype(int) * 0.2
    df['Score'] = df['P_Score'] + df['A_Score'] + df['V_Score']
    return df

# 3. 메인 화면 구성
cols = st.columns(3)
scan_results = []

for i, ticker in enumerate(TICKERS):
    data = get_data(ticker)
    curr = data.iloc[-1]
    prev = data.iloc[-2]
    
    # 하이브리드 전략 기반 가격 계산[span_0](start_span)[span_0](end_span)
    entry_price = curr['SMA20'] * 1.01
    target_price = entry_price + (curr['ATR'] * 2)
    stop_loss = curr['SMA20'] * 0.95
    
    # 상태 진단
    status = "Wait"
    if curr['Score'] >= 0.9:
        if curr['Low'] <= entry_price: status = "BUY NOW"
        elif curr['Close'] > entry_price * 1.03: status = "Wait for Pullback"
        else: status = "Buy Zone"
    
    scan_results.append({
        "Ticker": ticker,
        "Score": round(curr['Score'], 2),
        "Price": round(curr['Close'], 2),
        "Status": status,
        "Entry": round(entry_price, 2),
        "Target": round(target_price, 2)
    })

# 4. 요약 테이블 출력[span_1](start_span)[span_1](end_span)
st.subheader("📊 Market Scan Summary")
res_df = pd.DataFrame(scan_results)
st.dataframe(res_df.style.applymap(lambda x: 'background-color: #004d00' if x == 'BUY NOW' else ('background-color: #4d4d00' if x == 'Buy Zone' else ''), subset=['Status']))

# 5. 개별 종목 차트 (상세 분석)
selected_ticker = st.selectbox("Select Ticker for Detailed Chart", TICKERS)
chart_data = get_data(selected_ticker)

fig = go.Figure(data=[go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="Candlestick")])
fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['SMA20'], line=dict(color='orange', width=1), name="SMA20"))
st.plotly_chart(fig, use_container_width=True)
