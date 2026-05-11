import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
import pandas as pd
import numpy as np
import time
import re

# 1. 페이지 설정
st.set_page_config(page_title="Project Master-Key v4.6.1", layout="wide")

# 🔐 [보안] 사모님과 주인님만 아는 비밀번호 설정 (원하시는 4자리로 변경 가능)
PASSWORD = "0116"

def check_password():
    """비밀번호 인증 시스템: 세션 기반으로 로그인 상태 유지"""
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
                st.success("인증 성공! 시스템을 가동합니다...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    return False

if not check_password():
    st.stop()

# --- 🎯 마스터키 엔진 가동 ---
# 구글 스프레드시트 커넥션 (Secrets 설정 기반)
conn = st.connection("gsheets", type=GSheetsConnection)

# [전략 A] 섹터별 전수 조사 유니버스 (8개 그룹)
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

# 빠른 검색 옵션
QUICK_SEARCH = {
    "🇺🇸 엔비디아 (NVDA)": "NVDA",
    "🇺🇸 테슬라 (TSLA)": "TSLA",
    "🇰🇷 삼성전자 (005930.KS)": "005930.KS",
    "🇰🇷 코스메카코리아 (229200.KQ)": "229200.KQ",
    "🔍 직접 입력 모드": "MANUAL"
}

KOR_NAME_MAP = {v: k.split(" ")[1] for k, v in QUICK_SEARCH.items() if v != "MANUAL"}

def load_data():
    """구글 시트로부터 실시간 포트폴리오 로드"""
    try: return conn.read(ttl=0)
    except: return pd.DataFrame(columns=["owner", "ticker", "buy_price", "quantity"])

def calculate_indicators(df):
    """기술적 분석 엔진: 이평선, 볼린저 밴드, RSI 산출 (Syntax Error 수정됨)"""
    if len(df) < 20: return None, None, None, None
    try:
        ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
        ma120 = df['Close'].rolling(window=120).mean().iloc[-1] if len(df) >= 120 else None
        std20 = df['Close'].rolling(window=20).std().iloc[-1]
        bb_lower = ma20 - (2 * std20)
        
        delta = df['Close'].diff()
        up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rsi = 100 - (100 / (1 + (ema_up / ema_down)))
        return ma20, ma120, bb_lower, rsi.iloc[-1]
    except Exception:
        return None, None, None, None

def analyze_ticker(ticker):
    """주인님의 심층 종목 판독 엔진"""
    try:
        t = yf.Ticker(ticker)
        h = t.history(period="1y")
        if h.empty: return None
        cp = float(h['Close'].iloc[-1])
        try:
            inf = t.info
            tp, en, sc = inf.get('targetMeanPrice', 0), inf.get('shortName', ticker), inf.get('sector', 'N/A')
            eps = (inf.get('earningsQuarterlyGrowth', 0) * 100)
            cns = inf.get('recommendationKey', 'N/A').upper()
        except: tp, en, sc, eps, cns = 0, ticker, "N/A", 0, "N/A"
        
        m20, m120, bbl, rsi = calculate_indicators(h)
        
        # 추세 판정 로직
        ta = "📈 정배열" if cp > m20 > (m120 or 0) else ("🔵 밴드하단" if cp <= (bbl or 0) * 1.02 else ("⚠️ 역배열" if m120 and cp < m120 else "➖ 관망"))
        ups = ((tp / cp) - 1) * 100 if tp > 0 else 0
        
        return {"티커": ticker, "종목명": en, "섹터": sc, "현재가": cp, "목표가": tp, "차트": ta, "의견": cns, "업사이드": ups, "EPS": eps, "RSI": rsi, "MA20": m20, "MA120": m120, "BBL": bbl}
    except: return None

# --- UI 섹션 ---
st.title("🛡️ Project Master-Key v4.6.1")
df_p = load_data()

with st.sidebar:
    st.header("👤 소유주 및 종목 등록")
    owner = st.radio("사용자", ["킹병윤 주인님", "존경하는 사모님"])
    st.markdown("---")
    
    q_sel = st.selectbox("빠른 종목 선택", list(QUICK_SEARCH.keys()))
    if QUICK_SEARCH[q_sel] == "MANUAL":
        mkt = st.radio("시장 선택", ["🇺🇸 해외", "🇰🇷 코스피", "🇰🇷 코스닥"])
        raw_t = st.text_input("코드/티커 입력").strip()
        t_in = raw_t.upper() if "해외" in mkt else (re.sub(r'\D', '', raw_t) + (".KS" if "코스피" in mkt else ".KQ") if raw_t else "")
    else: t_in = QUICK_SEARCH[q_sel]
    
    bp = st.number_input("매수 단가", min_value=0.0)
    qt = st.number_input("매수 수량", min_value=0.0)
    
    if st.button("영구 저장"):
        if t_in:
            new = pd.DataFrame([{"owner": owner, "ticker": t_in, "buy_price": bp, "quantity": qt}])
            conn.update(data=pd.concat([df_p, new], ignore_index=True))
            st.success("금고에 저장되었습니다!"); time.sleep(1); st.rerun()

    if st.button("🗑️ 해당 소유주 금고 비우기"):
        conn.update(data=df_p[df_p['owner'] != owner])
        st.warning("데이터가 삭제되었습니다."); time.sleep(1); st.rerun()

t1, t2, t3, t4 = st.tabs(["🤵 주인님 금고", "💃 사모님 금고", "🔍 심층 판독기", "✨ 섹터 스캐너"])

def get_p_fmt(tk, v): return f"{v:,.0f}" if ".K" in tk else f"{v:,.2f}"

with t1:
    d = df_p[df_p['owner'] == "킹병윤 주인님"]
    if d.empty: st.info("내역 없음")
    else:
        res = []
        for _, r in d.iterrows():
            a = analyze_ticker(r['ticker'])
            if a:
                p = ((a['현재가'] - r['buy_price']) / r['buy_price'] * 100) if r['buy_price'] > 0 else 0
                res.append({"종목": a['종목명'], "현재가": get_p_fmt(a['티커'], a['현재가']), "수익률": f"{p:+.2f}%", "신호": a['차트']})
        st.table(pd.DataFrame(res))

with t2:
    d = df_p[df_p['owner'] == "존경하는 사모님"]
    if d.empty: st.info("내역 없음")
    else:
        res = []
        for _, r in d.iterrows():
            a = analyze_ticker(r['ticker'])
            if a:
                p = ((a['현재가'] - r['buy_price']) / r['buy_price'] * 100) if r['buy_price'] > 0 else 0
                res.append({"종목": a['종목명'], "현재가": get_p_fmt(a['티커'], a['현재가']), "수익률": f"{p:+.2f}%", "신호": a['차트']})
        st.table(pd.DataFrame(res))

with t3:
    st.header("🔍 심층 종목 판독기")
    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1: target = st.text_input("분석할 티커 또는 코드를 입력하십시오").strip()
    with c2: m_sel = st.radio("시장 구분 선택", ["🇺🇸 해외", "🇰🇷 코스피", "🇰🇷 코스닥"], horizontal=True)
    
    if st.button("🚀 정밀 분석 가동", use_container_width=True):
        if target:
            s_t = target.upper() if "해외" in m_sel else (re.sub(r'\D', '', target) + (".KS" if "코스피" in m_sel else ".KQ"))
            with st.spinner("마스터키 분석 중..."):
                d = analyze_ticker(s_t)
                if d:
                    st.markdown(f"### 📊 {d['종목명']} ({d['티커']}) 정밀 리포트")
                    cl = st.columns(5)
                    cl[0].metric("현재가", get_p_fmt(d['티커'], d['현재가']))
                    cl[1].metric("EPS 성장률", f"{d['EPS']:+.1f}%")
                    cl[2].metric("기대수익률", f"{d['업사이드']:+.1f}%")
                    cl[3].metric("RSI 수치", f"{d['RSI']:.1f}")
                    cl[4].metric("차트 신호", d['차트'])
                    
                    st.markdown("---")
                    ca, cb = st.columns(2)
                    with ca:
                        st.write("**[기본적 분석: 무엇을 살 것인가?]**")
                        st.write(f"- 🏭 산업 섹터: {d['섹터']}")
                        st.write(f"- 🎯 목표 주가: {get_p_fmt(d['티커'], d['목표가'])}")
                        st.write(f"- 🏦 기관 컨센서스: {d['의견']}")
                    with cb:
                        st.write("**[기술적 분석: 언제 살 것인가?]**")
                        st.write(f"- 📏 20일 이동평균: {get_p_fmt(d['티커'], (d['MA20'] or 0))}")
                        st.write(f"- 📏 120일 생명선: {get_p_fmt(d['티커'], (d['MA120'] or 0))}")
                        st.write(f"- 🔵 밴드 하단값: {get_p_fmt(d['티커'], (d['BBL'] or 0))}")
                else: st.error("데이터 로드 실패.")

with t4:
    st.header("✨ 섹터별 마스터키 스캐너")
    sec_sel = st.selectbox("산업군을 선택하십시오", list(SCAN_UNIVERSE.keys()))
    if st.button("🚀 섹터 전수 조사 시작"):
        with st.spinner(f"{sec_sel} 스캔 중..."):
            res = []
            pb = st.progress(0)
            for i, tk in enumerate(SCAN_UNIVERSE[sec_sel]):
                d = analyze_ticker(tk)
                if d:
                    res.append({
                        "종목명": d['종목명'], "현재가": get_p_fmt(d['티커'], d['현재가']), 
                        "기대수익": f"{d['업사이드']:+.1f}%", "EPS성장": f"{d['EPS']:+.1f}%", 
                        "RSI": f"{d['RSI']:.1f}", "추세상태": d['차트']
                    })
                pb.progress((i+1)/len(SCAN_UNIVERSE[sec_sel]))
            if res:
                st.table(pd.DataFrame(res).sort_values(by="기대수익", ascending=False))

# --- 📖 [복구] 마스터키 투자 지표 가이드 (Full Version) ---
st.markdown("---")
st.markdown("### 📖 [전문 용어 사전] 마스터키 투자 지표 가이드")
st.info("""
**[기본적 분석: 무엇을 살 것인가?]**
* **섹터 (Sector):** 해당 기업이 속한 산업군입니다. (예: Technology = 기술주, Healthcare = 헬스케어)
* **EPS 성장률 (Earnings Per Share Growth):** 전년 동기 대비 기업의 순이익 증가율입니다. 장기 투자의 절대적인 나침반입니다.
* **목표가 / 기대수익률 (Upside):** 글로벌 애널리스트들이 제시한 평균 목표 주가입니다. 현재가 대비 얼마나 더 오를 수 있는지를 나타냅니다.
* **기관의견 (Consensus):** 월스트리트 투자은행들이 내린 평균적인 투자 등급입니다.

**[기술적 분석: 언제 살 것인가?]**
* **RSI (상대강도지수):** 70 이상은 과열(조심), 30 이하는 침체(기회)를 뜻합니다.
* **볼린저 밴드 하단 (🔵):** 주가가 최근 20일 변동성의 최하단에 도달했다는 뜻입니다. 단기적으로 튀어 오를 확률이 높은 **'저점 매수 기회'**일 수 있습니다.
* **정배열 (📈):** 현재가 > 20일선 > 120일선 순서로 위치한 상태입니다. 주가가 탄탄한 **'상승 궤도'**에 안착했음을 의미합니다.
* **역배열 (⚠️):** 주가가 장기 생명선(120일선) 아래로 뚫고 내려간 상태로, 하락 추세이므로 접근에 주의가 필요합니다.
""")
