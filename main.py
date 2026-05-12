import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ftplib import FTP

# 1. 앱 설정
st.set_page_config(page_title="Q_Alpha v2.0 Top 50", layout="wide")
st.title("🏆 Q_Alpha v2.0 나스닥 고득점 Top 50 스캐너")

# 2. 나스닥 전체 리스트 가져오기
@st.cache_data(ttl=86400)
def get_nasdaq_list():
    try:
        ftp = FTP('ftp.nasdaqtrader.com')
        ftp.login()
        ftp.cwd('SymbolDirectory')
        lines = []
        ftp.retrlines('RETR nasdaqlisted.txt', lines.append)
        ftp.quit()
        return [line.split('|')[0] for line in lines[1:-1]]
    except:
        return ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'AMZN', 'META']

# 3. 핵심 분석 함수 (image_40.png 오류 방지 적용)
def analyze_stock(ticker):
    try:
        df = yf.download(ticker, period='1y', interval='1d', progress=False)
        if df.empty or len(df) < 60: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().dropna()
        # 점수 계산 로직
        close = df['Close'].astype(float)
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        vol = df['Volume'].astype(float)
        
        # P-Score (정배열)
        p_score = ((close > sma20) & (sma20 > sma50)).astype(int).iloc[-1] * 0.4
        # A-Score (눌림목)
        dist = np.abs(close.iloc[-1] - sma20.iloc[-1]) / sma20.iloc[-1]
        a_score = max(0, (1 - dist)) * 0.4
        # V-Score (거래량)
        v_score = (vol.iloc[-1] > vol.rolling(20).mean().iloc[-1]).astype(int) * 0.2
        
        total_score = round(p_score + a_score + v_score, 2)
        
        # 토스 검색 가능 조건 (거래량 5만 주 이상)
        if vol.iloc[-1] < 50000: return None
        
        return {
            "Ticker": ticker,
            "Score": total_score,
            "Price": f"${round(float(close.iloc[-1]), 2)}",
            "Volume": int(vol.iloc[-1]),
            "Signal": "🔥 BUY" if close.iloc[-1] <= (sma20.iloc[-1] * 1.01) else "✅ Watch"
        }
    except:
        return None

# 4. 분석 실행 섹션
nasdaq_symbols = get_nasdaq_list()

st.sidebar.header("🕹️ 스캔 컨트롤")
batch_size = st.sidebar.number_input("스캔할 종목 수 (최대 500 추천)", 10, 1000, 100)
start_btn = st.sidebar.button("🚀 분석 시작")

if start_btn:
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 서버 안정성을 위해 입력받은 수만큼 분석
    scan_list = nasdaq_symbols[:batch_size] 
    
    for i, ticker in enumerate(scan_list):
        status_text.text(f"분석 중: {ticker} ({i+1}/{len(scan_list)})")
        res = analyze_stock(ticker)
        if res:
            all_results.append(res)
        progress_bar.progress((i + 1) / len(scan_list))
    
    st.subheader(f"📈 분석 완료 (점수 상위 50개)")
    if all_results:
        # 점수 순으로 정렬 후 상위 50개 추출
        top_50 = pd.DataFrame(all_results).sort_values(by="Score", ascending=False).head(50)
        st.dataframe(top_50.style.background_gradient(subset=['Score'], cmap='RdYlGn'), use_container_width=True)
    else:
        st.warning("조건에 맞는 종목을 찾지 못했습니다.")
else:
    st.info("사이드바에서 '분석 시작' 버튼을 눌러주세요. (A~Z 순서대로 스캔하여 고득점주를 찾아냅니다.)")
