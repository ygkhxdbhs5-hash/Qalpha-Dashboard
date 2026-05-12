import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ftplib import FTP
import time

# 1. 앱 설정
st.set_page_config(page_title="Q_Alpha v2.0 Global Scanner", layout="wide")
st.title("🏆 Q_Alpha v2.0 나스닥 3,300종목 전수 스캐너")

# 2. 나스닥 전체 리스트 수집
@st.cache_data(ttl=86400)
def get_full_nasdaq():
    try:
        ftp = FTP('ftp.nasdaqtrader.com')
        ftp.login()
        ftp.cwd('SymbolDirectory')
        lines = []
        ftp.retrlines('RETR nasdaqlisted.txt', lines.append)
        ftp.quit()
        # 테스트를 위해 상위 종목부터 추출
        return [line.split('|')[0] for line in lines[1:-1] if "Test" not in line]
    except:
        return ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']

# 3. 분석 엔진 (image_41.png 에러 방지 포함)
def analyze_engine(ticker):
    try:
        # 속도 향상을 위해 기간을 1년에서 6개월로 단축
        df = yf.download(ticker, period='6mo', interval='1d', progress=False)
        if df.empty or len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.copy().dropna()
        close = df['Close'].astype(float)
        vol = df['Volume'].astype(float)
        
        # 토스 검색용 거래량 필터 (5만 주 이상)
        if vol.iloc[-1] < 50000: return None

        # 지표 계산
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        
        p_score = ((close.iloc[-1] > sma20.iloc[-1]) & (sma20.iloc[-1] > sma50.iloc[-1])) * 0.4
        dist = np.abs(close.iloc[-1] - sma20.iloc[-1]) / sma20.iloc[-1]
        a_score = max(0, (1 - dist)) * 0.4
        v_score = (vol.iloc[-1] > vol.rolling(20).mean().iloc[-1]) * 0.2
        
        total_score = round(float(p_score + a_score + v_score), 2)
        
        return {
            "Ticker": ticker,
            "Score": total_score,
            "Price": round(float(close.iloc[-1]), 2),
            "Volume": int(vol.iloc[-1]),
            "Signal": "🔥 BUY" if close.iloc[-1] <= (sma20.iloc[-1] * 1.01) else "✅ Watch"
        }
    except:
        return None

# 4. 실행 섹션
all_symbols = get_full_nasdaq()
st.sidebar.write(f"총 분석 대상: {len(all_symbols)}개 종목")

if st.sidebar.button("🚀 나스닥 전수 조사 시작"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    start_time = time.time()
    
    # 3,300개를 다 돌리기 위해 반복문 실행
    for i, ticker in enumerate(all_symbols):
        # 주기적으로 진행 상황 표시
        if i % 10 == 0:
            status_text.text(f"🔍 분석 중: {ticker} ({i}/{len(all_symbols)})")
            progress_bar.progress(i / len(all_symbols))
            
        res = analyze_engine(ticker)
        if res:
            results.append(res)
            
        # Streamlit Cloud 타임아웃 방지를 위해 매우 짧은 휴식 (옵션)
        if i % 500 == 0 and i > 0:
            time.sleep(1)

    end_time = time.time()
    st.success(f"✅ 분석 완료! (소요 시간: {int(end_time - start_time)}초)")

    if results:
        # 상위 50개 추출
        top_50 = pd.DataFrame(results).sort_values(by="Score", ascending=False).head(50)
        # image_41.png 에러 방지를 위해 기본 dataframe 사용
        st.subheader("🏆 Q_Alpha v2.0 실시간 점수 TOP 50")
        st.dataframe(top_50, use_container_width=True)
    else:
        st.warning("분석 결과 조건에 맞는 종목이 없습니다.")
else:
    st.info("사이드바의 버튼을 누르면 나스닥 전체 종목 전수 조사를 시작합니다. (약 3~5분 소요)")
