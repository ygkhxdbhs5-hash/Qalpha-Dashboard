import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. 앱 기본 설정
st.set_page_config(page_title="Q_Alpha v2.0 Dashboard", layout="wide")
st.title("🚀 Q_Alpha v2.0 실시간 대시보드")

# 2. 분석 대상 종목 (질문자님 Top 15)
TICKERS = ['FITB', 'NTRS', 'LNT', 'PAA', 'MO', 'SBUX', 'CAKE', 'ADAM', 'BIIB', 'WERN', 'HCSG', 'FFBC', 'VLY', 'MNST', 'HAS']

@st.cache_data(ttl=3600)
def get_safe_data(ticker):
    try:
        # 데이터 로드
        df = yf.download(ticker, period='1y', interval='1d')
        
        if df.empty or len(df) < 50:
            return None

        # [중요] image_40.png의 ValueError 해결을 위한 데이터 정리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy()
        
        # 지표 계산 (안정성을 위해 float 변환)
        close = df['Close'].astype(float)
        df['SMA20'] = close.rolling(window=20).mean()
        df['SMA50'] = close.rolling(window=50).mean()
        
        # ATR 계산
        high = df['High'].astype(float)
        low = df['Low'].astype(float)
        high_low = high - low
        df['ATR'] = high_low.rolling(14).mean()
        
        # [Q_Alpha v2.0 스코어링] image_30.png 공식 반영
        # P_Score: 정배열 (0.4)
        df['P_Score'] = ((close > df['SMA20']) & (df['SMA20'] > df['SMA50'])).astype(int) * 0.4
        # A_Score: SMA20 인근 눌림목 (0.4)
        dist = np.abs(close - df['SMA20']) / df['SMA20']
        df['A_Score'] = (1 - dist).clip(0, 1) * 0.4
        # V_Score: 거래량 동반 (0.2)
        df['V_Score'] = (df['Volume'] > df['Volume'].rolling(20).mean()).astype(int) * 0.2
        
        df['Total_Score'] = df['P_Score'] + df['A_Score'] + df['V_Score']
        return df
    except:
        return None

# 3. 메인 화면: 실시간 스캔 결과
st.subheader("📊 실시간 종목 스캔 (Buy Zone)")
results = []

for ticker in TICKERS:
    df = get_safe_data(ticker)
    if df is not None and not df.empty:
        curr = df.iloc[-1]
        
        # 전략 가격 계산
        entry_p = curr['SMA20'] * 1.01
        target_p = entry_p + (curr['ATR'] * 2)
        
        # 상태 진단
        status = "관망"
        if curr['Total_Score'] >= 0.9:
            status = "🔥 BUY NOW" if curr['Low'] <= entry_p else "✅ Buy Zone"
            
        results.append({
            "Ticker": ticker,
            "Score": round(float(curr['Total_Score']), 2),
            "Price": round(float(curr['Close']), 2),
            "Entry": round(float(entry_p), 2),
            "Target": round(float(target_p), 2),
            "Status": status
        })

if results:
    res_df = pd.DataFrame(results)
    st.dataframe(res_df.style.highlight_max(axis=0, subset=['Score'], color='#004d00'))

# 4. 개별 차트 분석
st.subheader("📈 상세 기술적 분석")
selected = st.selectbox("종목 선택", TICKERS)
detail_df = get_safe_data(selected)

if detail_df is not None:
    fig = go.Figure(data=[go.Candlestick(
        x=detail_df.index, open=detail_df['Open'], high=detail_df['High'],
        low=detail_df['Low'], close=detail_df['Close'], name="Candle"
    )])
    fig.add_trace(go.Scatter(x=detail_df.index, y=detail_df['SMA20'], line=dict(color='orange'), name="SMA20"))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("데이터를 불러올 수 없습니다.")
