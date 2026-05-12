import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ftplib import FTP

# 1. 앱 기본 설정
st.set_page_config(page_title="Q_Alpha v2.0 Global Scanner", layout="wide")
st.title("🚀 Q_Alpha v2.0 나스닥 전체 스캐너")

# 2. 나스닥 전체 종목 리스트 가져오기 (실시간 수집)
@st.cache_data(ttl=86400) # 리스트는 하루에 한 번만 업데이트
def get_nasdaq_symbols():
    try:
        ftp = FTP('ftp.nasdaqtrader.com')
        ftp.login()
        ftp.cwd('SymbolDirectory')
        lines = []
        ftp.retrlines('RETR nasdaqlisted.txt', lines.append)
        ftp.quit()
        # 데이터 정리
        data = [line.split('|') for line in lines[1:-1]]
        df = pd.DataFrame(data, columns=lines[0].split('|'))
        return df['Symbol'].tolist()
    except:
        # FTP 실패 시 기존 질문자님 리스트를 기본값으로 사용
        return ['FITB', 'NTRS', 'LNT', 'PAA', 'MO', 'SBUX', 'CAKE', 'ADAM', 'BIIB', 'WERN', 'HCSG', 'FFBC', 'VLY', 'MNST', 'HAS']

all_nasdaq = get_nasdaq_symbols()
st.sidebar.write(f"현재 나스닥 상장 종목 수: {len(all_nasdaq)}개")

# 3. 분석 대상 선택 (서버 과부하 방지를 위해 상위 N개 선택 가능하게)
scan_count = st.sidebar.slider("스캔할 종목 수", 10, 100, 30)
target_tickers = all_nasdaq[:scan_count]

@st.cache_data(ttl=3600)
def get_safe_data(ticker):
    try:
        df = yf.download(ticker, period='1y', interval='1d', progress=False)
        if df.empty or len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = df.copy().astype(float)
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        
        # Q_Alpha v2.0 로직
        df['P_Score'] = ((df['Close'] > df['SMA20']) & (df['SMA20'] > df['SMA50'])).astype(int) * 0.4
        dist = np.abs(df['Close'] - df['SMA20']) / df['SMA20']
        df['A_Score'] = (1 - dist).clip(0, 1) * 0.4
        df['V_Score'] = (df['Volume'] > df['Volume'].rolling(20).mean()).astype(int) * 0.2
        df['Total_Score'] = df['P_Score'] + df['A_Score'] + df['V_Score']
        return df
    except:
        return None

# 4. 실시간 스캔 및 결과 표시
st.subheader(f"📊 실시간 스캔 결과 (상위 {scan_count} 종목)")
results = []

with st.spinner("나스닥 데이터를 분석 중입니다..."):
    for ticker in target_tickers:
        df = get_safe_data(ticker)
        if df is not None:
            curr = df.iloc[-1]
            entry_p = curr['SMA20'] * 1.01
            target_p = entry_p + (curr['ATR'] * 2)
            
            if curr['Total_Score'] >= 0.7: # 필터링 기준: 0.7점 이상만 표시
                results.append({
                    "Ticker": ticker,
                    "Score": round(float(curr['Total_Score']), 2),
                    "Price": round(float(curr['Close']), 2),
                    "Entry": round(float(entry_p), 2),
                    "Target": round(float(target_p), 2),
                    "Status": "🔥 BUY NOW" if curr['Low'] <= entry_p else "✅ Watch"
                })

if results:
    st.dataframe(pd.DataFrame(results).sort_values(by="Score", ascending=False))
else:
    st.info("현재 조건에 맞는 종목이 없습니다. 스캔 범위를 늘려보세요.")
