import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
import pandas as pd
import numpy as np
import time
import re

# 1. 페이지 설정
st.set_page_config(page_title="Project Master-Key v4.4", layout="wide")

# 🔐 [보안] 비밀번호 설정 (사모님 공유용)
PASSWORD = "0116"

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct:
        return True
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🛡️ Master-Key 보안 인증")
        st.info("존경하는 주인님과 사모님 전용 시스템입니다.")
        password_input = st.text_input("접속 비밀번호를 입력하십시오", type="password")
        if st.button("인증 및 금고 개방"):
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

# --- 🎯 시스템 시작 ---
conn = st.connection("gsheets", type=GSheetsConnection)

SCAN_UNIVERSE = {
    "💻 AI 및 글로벌 빅테크": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE", "CRM"],
    "🔌 반도체 및 장비": ["TSM", "AVGO", "ASML", "AMD", "QCOM", "TXN", "INTC", "AMAT", "MU", "LRCX"],
    "🇰🇷 한국 코스피 핵심": ["005930.KS", "000660.KS", "005380.KS", "000270.KS", "105560.KS", "055550.KS", "035420.KS", "012450.KS"],
    "🇰🇷 한국 코스닥 리딩": ["247540.KQ", "196170.KQ", "028300.KQ", "348370.KQ", "278280.KQ", "041510.KQ", "145020.KQ", "229200.KQ", "356680.KQ"]
}

SEARCH_OPTIONS = {
    "🇺🇸 애플 (AAPL)": "AAPL",
    "🇺🇸 엔비디아 (NVDA)": "NVDA",
    "🇰🇷 삼성전자 (005930.KS)": "005930.KS",
    "🇰🇷 코스메카코리아 [229200]": "229200.KQ",
    "🔍 기타 종목 (직접 입력)": "MANUAL"
}

KOR_NAME_MAP = {v: k.split(" ")[1] for k, v in SEARCH_OPTIONS.items() if v != "MANUAL"}

def load_data():
    try: return conn.read(ttl=0)
    except: return pd.DataFrame(columns=["owner", "ticker", "buy_price", "quantity"])

def calculate_technical_indicators(df):
    if len(df) < 20: return None, None, None, None, None
    try:
        ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
        ma120 = df['Close'].rolling(window=120).mean().iloc[-1] if len(df) >= 120 else None
        std20 = df['Close'].rolling(window=20).std().iloc[-1]
        bb_lower = ma20 - (2 * std20)
        delta = df['Close'].diff()
        up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean(); ema_down = down.ewm(com=13, adjust=False).mean()
        rsi = 100 - (100 / (1 + (ema_up / ema_down)))
        return ma20, ma120, None, bb_lower, rsi.iloc[-1]
    except: return None, None, None, None, None

def analyze_ticker(ticker_name):
    try:
        t = yf.Ticker(ticker_name)
        hist = t.history(period="1y") 
        if hist.empty: return None
        curr_p = float(hist['Close'].iloc[-1])
        try:
            info = t.info
            target_p = info.get('targetMeanPrice', 0)
            eng_name = info.get('shortName', ticker_name)
            sector = info.get('sector', 'N/A')
            eps_growth = (info.get('earningsQuarterlyGrowth', 0) * 100)
            consensus = info.get('recommendationKey', 'N/A').upper()
        except: target_p, eng_name, sector, eps_growth, consensus = 0, ticker_name, "N/A", 0, "N/A"

        kor_name = KOR_NAME_MAP.get(ticker_name, "")
        display_name = f"{kor_name} ({eng_name})" if kor_name else eng_name
        ma20, ma120, _, bb_lower, rsi = calculate_technical_indicators(hist)
        
        ta_signal = "➖ 관망"
        if curr_p and bb_lower and curr_p <= bb_lower * 1.02: ta_signal = "🔵 밴드하단"
        elif curr_p and ma20 and ma120 and curr_p > ma20 > ma120: ta_signal = "📈 정배열"
        elif curr_p and ma120 and curr_p < ma120 * 0.95: ta_signal = "⚠️ 역배열"
        upside = ((target_p / curr_p) - 1) * 100 if target_p and curr_p else 0

        return {
            "티커": ticker_name, "종목명": display_name, "섹터": sector,
            "현재가": curr_p, "목표가": target_p, "차트": ta_signal,
            "기관의견": consensus, "업사이드": upside, "EPS성장": eps_growth, "RSI": rsi,
            "MA20": ma20, "MA120": ma120, "BB_L": bb_lower
        }
    except: return None

# --- UI 레이아웃 ---
st.title("🛡️ Project Master-Key v4.4")
st.subheader("존경하는 킹병윤 주인님 & 사모님 통합 시스템")

df_portfolio = load_data()

with st.sidebar:
    st.header("👤 소유주 선택")
    owner = st.radio("소유주", ["킹병윤 주인님", "존경하는 사모님"])
    st.markdown("---")
    st.header("📥 금고 등록")
    m_market = st.radio("시장", ["🇺🇸 해외", "🇰🇷 코스피", "🇰🇷 코스닥"], key="side_mkt")
    raw_t = st.text_input("코드/티커 입력 (예: NVDA, 005930)").strip()
    ticker_input = ""
    if raw_t:
        if "🇰🇷" in m_market: ticker_input = re.sub(r'[^0-9]', '', raw_t) + (".KS" if "코스피" in m_market else ".KQ")
        else: ticker_input = raw_t.upper()
    
    buy_p = st.number_input("매수 단가", min_value=0.0); qty = st.number_input("수량", min_value=0.0)
    if st.button("영구 저장"):
        if ticker_input:
            new_row = pd.DataFrame([{"owner": owner, "ticker": ticker_input, "buy_price": buy_p, "quantity": qty}])
            conn.update(data=pd.concat([df_portfolio, new_row], ignore_index=True))
            st.success("저장 완료!"); time.sleep(1); st.rerun()

m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["🤵 주인님 금고", "💃 사모님 금고", "🔍 심층 판독기", "✨ 섹터 스캐너"])

def get_p_fmt(tk, v): return f"{v:,.0f}" if ".K" in tk else f"{v:,.2f}"

def show_portfolio(name):
    t_list = df_portfolio[df_portfolio['owner'] == name]
    if t_list.empty: st.info("금고가 비어있습니다."); return
    res = []
    for _, row in t_list.iterrows():
        d = analyze_ticker(row['ticker'])
        if d:
            pft = ((d['현재가'] - row['buy_price']) / row['buy_price'] * 100) if row['buy_price'] > 0 else 0
            res.append({"티커": d['티커'], "종목명": d['종목명'], "현재가": get_p_fmt(d['티커'], d['현재가']), "수익률": f"{pft:+.2f}%", "차트": d['차트']})
    st.table(pd.DataFrame(res))

with m_tab1: show_portfolio("킹병윤 주인님")
with m_tab2: show_portfolio("존경하는 사모님")

# --- 🔍 [심층 종목 판독기] 주인님 요청 사항 반영 버전 ---
with m_tab3:
    st.header("🔍 심층 종목 판독기")
    st.markdown("---")
    
    # 💡 시장 선택 라디오 버튼과 입력창 배치
    c1, c2 = st.columns([2, 1])
    with c1:
        target = st.text_input("분석할 티커 또는 종목코드를 입력하십시오", placeholder="예: AAPL, 000660").strip()
    with c2:
        mkt_choice = st.radio("시장 구분", ["🇺🇸 해외", "🇰🇷 코스피", "🇰🇷 코스닥"], horizontal=True)

    if st.button("🚀 정밀 분석 가동", use_container_width=True):
        if target:
            # 티커 정제 로직
            s_tk = target.upper()
            if "코스피" in mkt_choice: s_tk = re.sub(r'[^0-9]', '', target) + ".KS"
            elif "코스닥" in mkt_choice: s_tk = re.sub(r'[^0-9]', '', target) + ".KQ"
            
            with st.spinner(f"{s_tk} 데이터 분석 중..."):
                d = analyze_ticker(s_tk)
                if d:
                    st.markdown(f"### 📊 {d['종목명']} ({d['티커']})")
                    
                    # 수치 분석 지표 노출
                    cols = st.columns(5)
                    cols[0].metric("현재가", get_p_fmt(d['티커'], d['현재가']))
                    cols[1].metric("EPS 성장률", f"{d['EPS성장']:+.1f}%")
                    cols[2].metric("기대수익률", f"{d['업사이드']:+.1f}%")
                    cols[3].metric("RSI 수치", f"{d['RSI']:.1f}")
                    cols[4].metric("기관 의견", d['기관의견'])
                    
                    st.markdown("---")
                    ca, cb = st.columns(2)
                    with ca:
                        st.write("**[기본적 분석: 무엇을 살 것인가?]**")
                        st.write(f"- 🏭 섹터: {d['섹터']}")
                        st.write(f"- 🎯 목표 주가: {get_p_fmt(d['티커'], d['목표가'])}")
                        st.write(f"- 📈 순이익 성장 여부: {'🟢 성장 중' if d['EPS성장'] > 0 else '🔴 정체/하락'}")
                    with cb:
                        st.write("**[기술적 분석: 언제 살 것인가?]**")
                        st.write(f"- 📏 20일 이동평균: {get_p_fmt(d['티커'], d['MA20'])}")
                        st.write(f"- 📏 120일 생명선: {get_p_fmt(d['티커'], d['MA120'])}")
                        st.write(f"- 🔔 현재 신호: {d['차트']}")
                    
                    # 마스터키 종합 판정
                    st.markdown("---")
                    score = sum([d['업사이드'] > 10, d['EPS성장'] > 0, d['RSI'] < 45, d['차트'] == "📈 정배열"])
                    if score >= 3: st.success("🏆 [종합 의견] 마스터키 기준 매우 우수한 종목입니다. 매수를 적극 검토하십시오.")
                    elif score >= 1: st.info("⚖️ [종합 의견] 지표가 엇갈리고 있습니다. 분할 매수로 신중히 접근하십시오.")
                    else: st.error("🚨 [종합 의견] 현재 진입하기엔 리스크가 큽니다. 관망을 권장합니다.")
                else: st.error("종목을 찾을 수 없습니다. 티커와 시장 선택을 확인해 주십시오.")

with m_tab4:
    st.header("✨ 섹터별 스캐너")
    sec = st.selectbox("산업군 선택", list(SCAN_UNIVERSE.keys()))
    if st.button("🚀 섹터 전수 조사 시작"):
        with st.spinner("스캔 중..."):
            res_s = []
            for tk in SCAN_UNIVERSE[sec]:
                d = analyze_ticker(tk)
                if d: res_s.append({"티커": d['티커'], "종목명": d['종목명'], "현재가": get_p_fmt(d['티커'], d['현재가']), "상승여력": f"{d['업사이드']:+.1f}%", "추세": d['차트']})
            st.table(pd.DataFrame(res_s).sort_values(by="상승여력", ascending=False))

# --- 📖 투자 지표 가이드 (각주) ---
st.markdown("---")
st.markdown("### 📖 [전문 용어 사전] 마스터키 투자 지표 가이드")
st.info("""
**[기본적 분석: 무엇을 살 것인가?]**
* **섹터 (Sector):** 해당 기업이 속한 산업군입니다.
* **EPS 성장률:** 전년비 순이익 증가율. 장기 투자의 절대적인 나침반입니다.
* **목표가 / 기대수익률 (Upside):** 애널리스트 평균 목표가 대비 현재가의 상승 여력입니다.
* **기관의견 (Consensus):** 월가 투자은행들의 평균 투자 등급입니다.

**[기술적 분석: 언제 살 것인가?]**
* **RSI (상대강도지수):** 70 이상 과열, 30 이하 침체(기회)를 뜻합니다.
* **볼린저 밴드 하단 (🔵):** 단기적으로 튀어 오를 확률이 높은 '저점 매수 기회'일 수 있습니다.
* **정배열 (📈):** 현재가 > 20일선 > 120일선 순서입니다. 탄탄한 '상승 궤도'를 의미합니다.
* **역배열 (⚠️):** 장기 생명선 아래로 뚫고 내려간 상태로 하락 추세 주의가 필요합니다.
""")
