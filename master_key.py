import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
import pandas as pd
import numpy as np
import time
import re

# 1. 페이지 설정
st.set_page_config(page_title="Project Master-Key v4.0", layout="wide")

# 💡 [핵심] 구글 스프레드시트 커넥션 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🎯 데이터 로드 함수 ---
def load_data():
    try:
        # 구글 시트에서 데이터를 읽어옵니다. (실시간 반영을 위해 ttl=0 설정)
        return conn.read(ttl=0)
    except Exception as e:
        # 데이터가 아예 없을 경우를 대비한 기본 구조 생성
        return pd.DataFrame(columns=["owner", "ticker", "buy_price", "quantity"])

# --- 🛠️ 분석 엔진 (v3.6 최신 로직 탑재) ---
def calculate_technical_indicators(df):
    if len(df) < 20: return None, None, None, None, None
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
        return ma20, ma120, None, bb_lower, rsi.iloc[-1]
    except: return None, None, None, None, None

def analyze_ticker(ticker_name):
    try:
        t = yf.Ticker(ticker_name)
        hist = t.history(period="1y") 
        if hist.empty: return None
        
        # 💡 실시간 가격 보정 로직 (차트 마지막 종가 사용)
        curr_p = float(hist['Close'].iloc[-1])
        
        try:
            info = t.info
            target_p = info.get('targetMeanPrice', 0)
            eng_name = info.get('shortName', ticker_name)
            sector = info.get('sector', 'N/A')
            eps_growth = (info.get('earningsQuarterlyGrowth', 0) * 100)
            consensus = info.get('recommendationKey', 'N/A').upper()
        except:
            target_p, eng_name, sector, eps_growth, consensus = 0, ticker_name, "N/A", 0, "N/A"

        ma20, ma120, _, bb_lower, rsi = calculate_technical_indicators(hist)
        
        ta_signal = "➖ 관망"
        if curr_p and bb_lower and curr_p <= bb_lower * 1.02: ta_signal = "🔵 밴드하단"
        elif curr_p and ma20 and ma120 and curr_p > ma20 > ma120: ta_signal = "📈 정배열"
        elif curr_p and ma120 and curr_p < ma120 * 0.95: ta_signal = "⚠️ 역배열"
        
        upside = ((target_p / curr_p) - 1) * 100 if target_p and curr_p else 0

        return {
            "티커": ticker_name, "종목명": eng_name, "섹터": sector,
            "현재가": curr_p, "목표가": target_p, "차트": ta_signal,
            "기관의견": consensus, "업사이드": upside, "EPS성장": eps_growth, "RSI": rsi,
            "MA20": ma20, "MA120": ma120, "BB_L": bb_lower
        }
    except: return None

# --- UI 메인 섹션 ---
st.title("🛡️ Project Master-Key v4.0")
st.subheader("존경하는 킹병윤 주인님 & 사모님 통합 시스템 (구글 클라우드 DB)")

# 최신 포트폴리오 데이터 로드
df_portfolio = load_data()

with st.sidebar:
    st.header("👤 소유주 선택")
    owner = st.radio("소유주", ["킹병윤 주인님", "존경하는 사모님"])
    st.markdown("---")
    st.header("📥 금고 등록")
    
    m_market = st.radio("시장", ["🇺🇸 해외", "🇰🇷 코스피", "🇰🇷 코스닥"])
    raw_t = st.text_input("코드/티커 입력 (예: 229200, NVDA)").strip()
    
    ticker_input = ""
    if raw_t:
        if "🇰🇷" in m_market:
            if re.search(r'[가-힣]', raw_t): 
                st.error("한글 말고 숫자를 넣어주세요!")
            else:
                ticker_input = re.sub(r'[^0-9]', '', raw_t) + (".KS" if "코스피" in m_market else ".KQ")
        else:
            ticker_input = raw_t.upper()
    
    buy_p = st.number_input("매수 단가", min_value=0.0, step=0.01)
    qty = st.number_input("수량", min_value=0.0, step=0.1)
    
    if st.button("구글 시트에 영구 저장"):
        if ticker_input:
            # 새로운 행 데이터 생성
            new_row = pd.DataFrame([{"owner": owner, "ticker": ticker_input, "buy_price": buy_p, "quantity": qty}])
            # 기존 데이터와 병합
            updated_df = pd.concat([df_portfolio, new_row], ignore_index=True)
            # 💡 [핵심] 구글 시트 업데이트 명령
            conn.update(data=updated_df)
            st.success(f"{ticker_input}이(가) 구글 시트 금고에 영구 저장되었습니다!")
            time.sleep(1)
            st.rerun()

    if st.button("🗑️ 선택된 소유주 금고 비우기"):
        updated_df = df_portfolio[df_portfolio['owner'] != owner]
        conn.update(data=updated_df)
        st.warning(f"{owner}의 모든 데이터가 삭제되었습니다.")
        time.sleep(1)
        st.rerun()

# --- 탭 구성 ---
m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["🤵 주인님 금고", "💃 사모님 금고", "🔍 심층 종목 판독기", "✨ 섹터별 스캐너"])

def get_p_fmt(tk, v):
    if not v: return "N/A"
    return f"{v:,.0f}" if ".K" in tk else f"{v:,.2f}"

def show_portfolio(name):
    t_list = df_portfolio[df_portfolio['owner'] == name]
    if t_list.empty:
        st.info(f"{name}의 등록된 종목이 없습니다.")
        return
    
    res = []
    for _, row in t_list.iterrows():
        d = analyze_ticker(row['ticker'])
        if d:
            pft = ((d['현재가'] - row['buy_price']) / row['buy_price'] * 100) if row['buy_price'] > 0 else 0
            res.append({
                "티커": d['티커'], "종목명": d['종목명'], 
                "현재가": get_p_fmt(d['티커'], d['현재가']), 
                "내단가": f"{row['buy_price']:,.2f}", 
                "수익률": f"{pft:+.2f}%", 
                "차트": d['차트'], "기관의견": d['기관의견']
            })
    if res:
        st.table(pd.DataFrame(res))

with m_tab1: show_portfolio("킹병윤 주인님")
with m_tab2: show_portfolio("존경하는 사모님")

with m_tab3:
    st.header("🔍 심층 종목 판독기")
    c1, c2 = st.columns([2, 1])
    with c1: target = st.text_input("코드 입력 (예: 229200, NVDA)", key="anal_input").strip()
    with c2: mkt = st.radio("시장", ["해외", "코스피", "코스닥"], key="an_mkt")
    if st.button("🚀 정밀 분석"):
        if target:
            s_tk = target.upper()
            if "코스피" in mkt: s_tk = re.sub(r'[^0-9]', '', target) + ".KS"
            elif "코스닥" in mkt: s_tk = re.sub(r'[^0-9]', '', target) + ".KQ"
            d = analyze_ticker(s_tk)
            if d:
                st.markdown(f"### 📊 {d['종목명']} ({d['티커']}) 리포트")
                cols = st.columns(5)
                cols[0].metric("현재가", get_p_fmt(d['티커'], d['현재가']))
                cols[1].metric("목표가", get_p_fmt(d['티커'], d['목표가']) if d['목표가'] else "N/A")
                cols[2].metric("EPS성장", f"{d['EPS성장']:+.1f}%")
                cols[3].metric("RSI", f"{d['RSI']:.1f}")
                cols[4].metric("Upside", f"{d['업사이드']:+.1f}%")
                st.markdown("---")
                ca, cb = st.columns(2)
                with ca:
                    st.write("**[기본적 분석]**")
                    st.write(f"- 섹터: {d['섹터']} | - 기관의견: {d['기관의견']}")
                with cb:
                    st.write("**[기술적 분석]**")
                    st.write(f"- 20일선: {get_p_fmt(d['티커'], d['MA20'])} | - 120일선: {get_p_fmt(d['티커'], d['MA120'])}")
                st.markdown("---")
                sc = 0
                if d['업사이드'] > 10: sc += 1; st.write("🟢 **가치:** 10% 이상 저평가")
                if d['EPS성장'] > 0: sc += 1; st.write(f"🟢 **성장:** 순이익 성장 중")
                if d['RSI'] < 40: sc += 1; st.write(f"🟢 **타이밍:** RSI 침체 (기회)")
                if d['차트'] == "📈 정배열": sc += 1; st.write("🟢 **추세:** 상승 정배열")
                if sc >= 3: st.success("🏆 강력 매수 검토")
                elif sc >= 1: st.info("⚖️ 중립")
                else: st.error("🚨 보수적 접근")

# (섹터 스캐너 및 각주 생략 - v3.6과 동일하게 하단에 유지)
st.markdown("---")
st.markdown("### 📖 [전문 용어 사전] 마스터키 투자 지표 가이드")
st.info("""
**[기본적 분석]**
*   **EPS 성장률:** 전년비 순이익 증가율. (장기 투자의 핵심)
*   **목표가 / 기대수익률 (Upside):** 애널리스트 평균 목표가 대비 상승 여력.
**[기술적 분석]**
*   **RSI:** 70 이상 과열, 30 이하 침체.
*   **정배열 (📈):** 현재가 > 20일선 > 120일선. (상승 추세)
""")
