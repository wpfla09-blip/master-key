import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
import pandas as pd
import numpy as np
import time
import re

# 1. 페이지 설정
st.set_page_config(page_title="Project Master-Key v4.6", layout="wide")

# 🔐 [보안] 사모님 공유용 비밀번호 (기본값: 1234)
PASSWORD = "0116"

def check_password():
    """비밀번호 인증: 사모님께서 로그인 없이 편리하게 접속하시도록 설계"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct:
        return True
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🛡️ Master-Key 보안 인증")
        st.info("존경하는 주인님과 사모님 전용 자산 관리 시스템입니다.")
        password_input = st.text_input("접속 비밀번호를 입력하십시오", type="password")
        if st.button("인증 및 시스템 가동"):
            if password_input == PASSWORD:
                st.session_state.password_correct = True
                st.success("인증에 성공했습니다. 금고를 개방합니다...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    return False

if not check_password():
    st.stop()

# --- 🎯 마스터키 엔진 가동 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# [전략 A] 섹터별 전수 조사 유니버스 (주인님 요청으로 8개 전 섹터 복구)
SCAN_UNIVERSE = {
    "💻 AI 및 글로벌 빅테크": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE", "CRM"],
    "🔌 반도체 및 장비": ["TSM", "AVGO", "ASML", "AMD", "QCOM", "TXN", "INTC", "AMAT", "MU", "LRCX"],
    "💊 헬스케어 및 바이오": ["LLY", "NVO", "UNH", "JNJ", "MRK", "ABBV", "PFE", "ISRG", "SYK", "VRTX"],
    "🛡️ 방산 및 항공우주": ["LMT", "RTX", "NOC", "GD", "BA", "LHX", "TDG", "TXT", "HII"],
    "🏦 글로벌 금융 및 결제": ["JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "BLK", "PYPL"],
    "⚡ 원전 / 전력망 / 인프라": ["VRT", "CEG", "PWR", "GE", "ETN", "PCG", "SO", "DUK", "EXC", "AEP"],
    "🇰🇷 한국 코스피 핵심": ["005930.KS", "000660.KS", "005380.KS", "000270.KS", "105560.KS", "055550.KS", "035420.KS", "012450.KS"],
    "🇰🇷 한국 코스닥 리딩": ["247540.KQ", "196170.KQ", "028300.KQ", "348370.KQ", "278280.KQ", "041510.KQ", "145020.KQ", "229200.KQ", "356680.KQ"]
}

# [검색 편의] 자주 찾는 종목 맵핑
QUICK_SEARCH = {
    "🇺🇸 엔비디아 (NVDA)": "NVDA",
    "🇺🇸 테슬라 (TSLA)": "TSLA",
    "🇰🇷 삼성전자 (005930.KS)": "005930.KS",
    "🇰🇷 코스메카코리아 (229200.KQ)": "229200.KQ",
    "🔍 직접 입력 모드": "MANUAL"
}

def load_data():
    """구글 시트로부터 실시간 포트폴리오 로드"""
    try: return conn.read(ttl=0)
    except: return pd.DataFrame(columns=["owner", "ticker", "buy_price", "quantity"])

def calculate_indicators(df):
    """기술적 분석 엔진: 주인님의 매매 타이밍 산출 로직"""
    if len(df) < 20: return None, None, None, None
    try:
        ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
        ma1
