"""
스윙매매 통합 대시보드 v1.0
=============================
실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json, os, time, hashlib
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import requests, warnings
warnings.filterwarnings('ignore')

# ── SSL 우회 ─────────────────────────────────────────────────
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import urllib3; urllib3.disable_warnings()
_orig = requests.Session.request
def _nv(self, *a, **kw): kw.setdefault('verify', False); return _orig(self, *a, **kw)
requests.Session.request = _nv

# ── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(
    page_title="스윙 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",  # 모바일 기본 사이드바 닫힘
)

# ── 전역 CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

/* 기본 */
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.main .block-container { padding: 1rem 1rem 2rem; max-width: 100%; }

/* 카드 */
.card {
    background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
    border: 1px solid #2d3561;
    border-radius: 16px;
    padding: 1.2rem;
    margin: 0.4rem 0;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}
.card-profit { border-left: 4px solid #00d4aa; }
.card-loss   { border-left: 4px solid #ff4b6e; }
.card-info   { border-left: 4px solid #4e9eff; }

/* 수치 */
.big-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem; font-weight: 700;
}
.profit-color { color: #00d4aa; }
.loss-color   { color: #ff4b6e; }
.neutral-color{ color: #4e9eff; }
.label        { color: #8892a4; font-size: 0.8rem; margin-bottom: 0.2rem; }

/* 알림바 */
.alert-red {
    background: linear-gradient(90deg, #ff4b6e22, #ff4b6e11);
    border: 1px solid #ff4b6e;
    border-radius: 10px; padding: 0.8rem 1rem;
    color: #ff4b6e; font-weight: 600; margin: 0.3rem 0;
    animation: pulse 1.5s ease-in-out infinite;
}
.alert-yellow {
    background: linear-gradient(90deg, #ffd76622, #ffd76611);
    border: 1px solid #ffd766;
    border-radius: 10px; padding: 0.8rem 1rem;
    color: #ffd766; font-weight: 600; margin: 0.3rem 0;
}
.alert-green {
    background: linear-gradient(90deg, #00d4aa22, #00d4aa11);
    border: 1px solid #00d4aa;
    border-radius: 10px; padding: 0.8rem 1rem;
    color: #00d4aa; font-weight: 600; margin: 0.3rem 0;
}
@keyframes pulse {
    0%,100% { opacity:1; } 50% { opacity:0.6; }
}

/* 테이블 행 강조 */
.blink-row { animation: blink 1s step-start infinite; }
@keyframes blink { 50% { background: #ff4b6e22; } }

/* 모바일 최적화 */
@media (max-width: 768px) {
    .big-num { font-size: 1.1rem; }
    .main .block-container { padding: 0.3rem 0.3rem 1rem; }
    .card { padding: 0.7rem; border-radius: 10px; }
    /* 테이블 가로 스크롤 */
    .stDataFrame { overflow-x: auto !important; }
    /* Plotly 그래프 높이 축소 */
    .js-plotly-plot { max-height: 220px; }
    /* 버튼 터치 영역 확대 */
    .stButton > button { min-height: 44px; font-size: 0.9rem; }
    /* 사이드바 기본 숨김 */
    [data-testid="stSidebar"] { min-width: 0 !important; }
}
@media (max-width: 480px) {
    .big-num { font-size: 0.95rem; }
    .label { font-size: 0.7rem; }
}

/* 버튼 */
.stButton > button {
    background: linear-gradient(135deg, #4e9eff, #2d3561);
    color: white; border: none; border-radius: 10px;
    font-weight: 600; width: 100%;
    transition: all 0.2s;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(78,158,255,0.4);
}

/* 사이드바 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1117 0%, #1a1f2e 100%);
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  데이터 저장 / 로드 (사용자별 격리)
# ════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════
# 📌 텔레그램 설정 (st.secrets 사용)
# ──────────────────────────────────────────────────────
# [로컬 실행 시] 프로젝트 폴더에 .streamlit/secrets.toml 파일 생성:
#   [telegram]
#   token   = "여기에_봇토큰"
#   chat_id = "여기에_챗ID"
#
# [Streamlit Cloud 배포 시] 대시보드 → 앱 설정 → Secrets 메뉴에서
#   위와 동일한 내용을 붙여넣기하면 됩니다.
# ══════════════════════════════════════════════════════
def _get_tg_token() -> str:
    try:
        return st.secrets["telegram"]["token"]
    except Exception:
        return ""

def _get_tg_chat_id() -> str:
    try:
        return st.secrets["telegram"]["chat_id"]
    except Exception:
        return ""

# 데이터 저장 경로: 앱 파일 기준 상대경로 (로컬/클라우드 모두 호환)
try:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")
except Exception:
    DATA_DIR = os.path.join(os.getcwd(), "user_data")
TOTAL_SEED = 2_000_000
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        return json.load(open(USERS_FILE, encoding="utf-8"))
    # 기본 계정
    default = {"admin": {"pw": hash_pw("1234"), "seed": 2_000_000}}
    save_users(default)
    return default

def save_users(users: dict):
    json.dump(users, open(USERS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def user_file(username: str, fname: str) -> str:
    d = os.path.join(DATA_DIR, username)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, fname)

def load_portfolio(username: str) -> list:
    f = user_file(username, "portfolio.json")
    if os.path.exists(f):
        return json.load(open(f, encoding="utf-8"))
    return []

def save_portfolio(username: str, data: list):
    json.dump(data, open(user_file(username, "portfolio.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=2)

def fix_portfolio_realized(username: str):
    """보유 중 종목의 잘못된 realized_pnl 강제 0 리셋 (1회성)"""
    data    = load_portfolio(username)
    changed = False
    for p in data:
        if p.get("status") != "청산" and p.get("realized_pnl", 0) != 0:
            p["realized_pnl"] = 0
            changed = True
    if changed:
        save_portfolio(username, data)
    return changed

def load_watchlist(username: str) -> list:
    """모닝체크 활성 목록 (오늘 볼 종목)"""
    f = user_file(username, "watchlist.json")
    try:
        if os.path.exists(f):
            data = json.load(open(f, encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []

def save_vault(username: str, data: list):
    """스윙 관심종목 보관함 전체 저장"""
    json.dump(data, open(user_file(username, "vault.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=2)

def load_vault(username: str) -> list:
    """스윙 관심종목 보관함 로드"""
    f = user_file(username, "vault.json")
    try:
        if os.path.exists(f):
            data = json.load(open(f, encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []

def save_watchlist(username: str, data: list):
    """관심종목 즉시 파일 저장 — 폴더 없으면 자동 생성"""
    path = user_file(username, "watchlist.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_to_watchlist(username: str, ticker: str, name: str,
                     source: str, entry: float, target: float,
                     stoploss: float, rsi="-", rr_ratio="-",
                     market: str = "", scan_date: str = "",
                     base_price: float = 0.0) -> str:
    """관심종목 추가/업데이트 — 출처·날짜·기준가 포함 즉시 저장"""
    wl    = load_watchlist(username)
    today = datetime.now().strftime("%Y-%m-%d")
    item  = {
        "id":          int(time.time()),
        "ticker":      str(ticker).zfill(6),
        "name":        str(name),
        "market":      str(market),
        "source":      str(source),         # "퀀트" | "스윙" | "수동"
        "reg_date":    scan_date or today,   # 추가한 날짜
        "base_price":  float(base_price or entry),  # 추가 당시 기준가
        "entry":       int(entry),
        "target":      int(target),
        "stoploss":    int(stoploss),
        "rsi":         rsi,
        "rr_ratio":    rr_ratio,
        "is_active":   True,                # 모닝체크 포함 여부
    }
    for i, w in enumerate(wl):
        if w.get("ticker") == item["ticker"]:
            item["id"]         = w["id"]
            item["reg_date"]   = w.get("reg_date", today)
            item["base_price"] = w.get("base_price", item["base_price"])
            item["is_active"]  = w.get("is_active", True)
            wl[i] = item
            save_watchlist(username, wl)
            return "updated"
    wl.append(item)
    save_watchlist(username, wl)
    return "added"


def get_stock_list() -> pd.DataFrame:
    rows = []
    try:
        import FinanceDataReader as fdr
        for market in ["KOSPI", "KOSDAQ"]:
            df = fdr.StockListing(market)
            df.columns = [c.strip() for c in df.columns]
            code_col = next((c for c in df.columns if c in ["Code","Symbol","종목코드"]), None)
            name_col = next((c for c in df.columns if c in ["Name","종목명","ISU_ABBRV"]), None)
            if not code_col or not name_col: continue
            for _, r in df.iterrows():
                code = str(r[code_col]).strip().zfill(6)
                name = str(r[name_col]).strip()
                if code.isdigit() and name:
                    rows.append({"code": code, "name": name, "market": market,
                                 "display": f"{name} ({code})"})
    except:
        pass
    return pd.DataFrame(rows).drop_duplicates("code").reset_index(drop=True)

@st.cache_data(ttl=300)
def get_price(ticker: str) -> float:
    try:
        import FinanceDataReader as fdr
        end   = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
        df = fdr.DataReader(ticker, start, end)
        if df is not None and len(df) > 0:
            for c in df.columns:
                if c.strip().lower() in ("close", "adj close"):
                    return float(df[c].iloc[-1])
    except:
        pass
    return 0.0

@st.cache_data(ttl=300)
def get_ohlcv_cached(ticker: str, days: int = 130):
    try:
        import FinanceDataReader as fdr
        end   = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        df = fdr.DataReader(ticker, start, end)
        if df is None or len(df) == 0:
            return None
        col_map = {}
        for c in df.columns:
            cl = c.strip().lower()
            if cl == "open":    col_map[c] = "open"
            elif cl == "high":  col_map[c] = "high"
            elif cl == "low":   col_map[c] = "low"
            elif cl in ("close","adj close"): col_map[c] = "close"
            elif cl == "volume": col_map[c] = "volume"
        df = df.rename(columns=col_map)
        for col in ["open","high","low","close","volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.dropna(subset=["close"])
    except:
        return None

# ════════════════════════════════════════════════════════════
#  로그인 화면
# ════════════════════════════════════════════════════════════
def show_login():
    st.markdown("""
    <div style='text-align:center; padding: 3rem 0 1rem;'>
        <div style='font-size:3rem;'>📈</div>
        <h1 style='color:#4e9eff; font-size:1.8rem; margin:0.5rem 0;'>스윙 대시보드</h1>
        <p style='color:#8892a4;'>로그인하여 시작하세요</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        users = load_users()
        tab1, tab2 = st.tabs(["🔐 로그인", "📝 회원가입"])

        with tab1:
            username = st.text_input("아이디", key="login_id")
            password = st.text_input("비밀번호", type="password", key="login_pw")
            if st.button("로그인", key="btn_login"):
                if username in users and users[username]["pw"] == hash_pw(password):
                    st.session_state["user"] = username
                    st.session_state["seed"] = users[username].get("seed", 2_000_000)
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")
            st.caption("기본 계정: admin / 1234")

        with tab2:
            new_id  = st.text_input("새 아이디", key="reg_id")
            new_pw  = st.text_input("새 비밀번호", type="password", key="reg_pw")
            new_pw2 = st.text_input("비밀번호 확인", type="password", key="reg_pw2")
            if st.button("회원가입", key="btn_reg"):
                if not new_id or not new_pw:
                    st.error("아이디와 비밀번호를 입력하세요.")
                elif new_pw != new_pw2:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif new_id in users:
                    st.error("이미 존재하는 아이디입니다.")
                else:
                    users[new_id] = {"pw": hash_pw(new_pw), "seed": 2_000_000}
                    save_users(users)
                    st.success("가입 완료! 로그인하세요.")

# ════════════════════════════════════════════════════════════
#  알림바
# ════════════════════════════════════════════════════════════
def load_notifications(username: str) -> list:
    f = user_file(username, "notifications.json")
    try:
        if os.path.exists(f):
            data = json.load(open(f, encoding="utf-8"))
            return data if isinstance(data, list) else []
    except: pass
    return []

def add_notification(username: str, msg: str, level: str = "info"):
    """알림 추가 (최근 30개 유지)"""
    try:
        nots = load_notifications(username)
        nots.insert(0, {"msg": msg, "level": level,
                        "time": datetime.now().strftime("%H:%M")})
        nots = nots[:30]
        path = user_file(username, "notifications.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(nots, open(path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    except: pass

def send_telegram(message: str):
    """텔레그램 메시지 전송 (st.secrets 기반)"""
    token   = _get_tg_token()
    chat_id = _get_tg_chat_id()
    if not token or not chat_id:
        st.warning("텔레그램 설정이 없습니다. .streamlit/secrets.toml을 확인하세요.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10, verify=False)
        if resp.status_code != 200:
            st.warning(f"텔레그램 오류: {resp.text[:100]}")
    except Exception as e:
        st.warning(f"텔레그램 전송 실패: {e}")


def show_notification_bar(username: str):
    """알림바 — 비활성화됨 (모닝체크 카드로 대체)"""
    pass

# ════════════════════════════════════════════════════════════
#  [1] 대시보드
# ════════════════════════════════════════════════════════════
def page_dashboard(username: str):
    st.markdown("## 📊 대시보드")
    # 보유 종목의 잘못된 realized_pnl 1회 리셋
    if fix_portfolio_realized(username):
        st.toast("📌 실현손익 데이터 정상화 완료")
    portfolio = load_portfolio(username)
    seed      = st.session_state.get("seed", 2_000_000)

    if not portfolio:
        st.info("포트폴리오에 종목을 추가하면 대시보드가 활성화됩니다.")
        return

    # 실현손익: 반드시 청산(매도) 처리된 항목만 합산
    realized = sum(float(p.get("realized_pnl", 0)) for p in portfolio if p.get("status") == "청산")
    rows       = []
    total_cost = 0.0
    total_cur  = 0.0

    for p in portfolio:
        if p.get("status") == "청산":
            continue
        qty       = int(p.get("qty", 1))
        buy_price = float(p.get("buy_price", 0))
        cost      = float(p.get("total_amount", buy_price * qty))
        cur       = float(get_price(p["ticker"]) or buy_price)
        val       = cur * qty
        pnl       = val - cost
        pnl_pct   = pnl / cost * 100 if cost else 0
        total_cost += cost
        total_cur  += val
        rows.append({**p, "cur_price": cur, "pnl": pnl, "pnl_pct": pnl_pct})

    unrealized    = total_cur - total_cost          # 미실현 손익
    total_pnl     = unrealized + realized            # 총손익 = 미실현 + 실현
    # 총수익률 = 총손익 / 총매수금액 * 100
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0

    # 카드 3개
    c1, c2, c3 = st.columns(3)
    with c1:
        cls = "profit-color" if unrealized >= 0 else "loss-color"
        sign = "+" if unrealized >= 0 else ""
        st.markdown(f"""
        <div class="card {'card-profit' if unrealized>=0 else 'card-loss'}">
            <div class="label">미실현 손익</div>
            <div class="big-num {cls}">{sign}{unrealized:,.0f}원</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        cls = "profit-color" if realized >= 0 else "loss-color"
        sign = "+" if realized >= 0 else ""
        st.markdown(f"""
        <div class="card {'card-profit' if realized>=0 else 'card-loss'}">
            <div class="label">실현 손익</div>
            <div class="big-num {cls}">{sign}{realized:,.0f}원</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        cls = "profit-color" if total_pnl >= 0 else "loss-color"
        sign = "+" if total_pnl >= 0 else ""
        st.markdown(f"""
        <div class="card card-info">
            <div class="label">총 수익률 (시드 대비)</div>
            <div class="big-num {cls}">{sign}{total_pnl_pct:.2f}%</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 수익률 파이 차트
    if rows:
        labels = [r["name"] for r in rows]
        values = [r["cur_price"] * r["qty"] for r in rows]
        colors = ["#00d4aa","#4e9eff","#ffd766","#ff4b6e","#a78bfa","#fb923c"]
        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.6,
            marker=dict(colors=colors[:len(labels)]),
            textfont=dict(size=12),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            legend=dict(font=dict(color="#8892a4")),
            margin=dict(t=10,b=10,l=10,r=10),
            height=260,
        )
        st.plotly_chart(fig, use_container_width=True)

    # 브라우저 푸시 알림 JS
    st.markdown("""
    <script>
    if ('Notification' in window && Notification.permission !== 'denied') {
        Notification.requestPermission();
    }
    function pushAlert(title, body) {
        if (Notification.permission === 'granted') {
            new Notification(title, { body: body, icon: '📈' });
        }
    }
    </script>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  [2] 내 포트폴리오
# ════════════════════════════════════════════════════════════
def page_portfolio(username: str):
    st.markdown("## 💼 내 포트폴리오")
    portfolio = load_portfolio(username)

    # 매매 기록 입력
    with st.expander("➕ 매매 기록 추가", expanded=False):
        with st.spinner("종목 목록 불러오는 중..."):
            stock_df = get_stock_list()

        if stock_df.empty:
            st.warning("종목 목록 불러오기 실패. 직접 입력하세요.")
            sel_name   = st.text_input("종목명")
            sel_ticker = st.text_input("종목코드")
        else:
            selected = st.selectbox("🔍 종목 검색 (종목명 입력)", stock_df["display"].tolist(),
                                    index=None, placeholder="종목명을 입력하세요...")
            if selected:
                matched    = stock_df[stock_df["display"] == selected].iloc[0]
                sel_name   = matched["name"]
                sel_ticker = matched["code"]
                info_html  = f'<div style="background:#1a1f2e;border:1px solid #2d3561;border-radius:8px;padding:0.6rem 1rem;margin:0.3rem 0;font-size:0.88rem;color:#4e9eff;">✅ <b>{sel_name}</b> | 코드: <b>{sel_ticker}</b> | {matched["market"]}</div>'
                st.markdown(info_html, unsafe_allow_html=True)
            else:
                sel_name, sel_ticker = "", ""

        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
        with c1:
            trade_dt = st.date_input("거래일", value=datetime.today())
        with c2:
            qty = st.number_input("보유수량 (주)", min_value=1, value=1, step=1)
        with c3:
            total_amount = st.number_input("총 매수금액 (원)", min_value=0, value=0, step=10000,
                                           help="실제 매수에 사용한 총 금액")
        with c4:
            kind = st.selectbox("구분", ["매수", "매도"])

        if qty > 0 and total_amount > 0:
            avg_price = total_amount / qty
            avg_html  = f'<div style="background:#0f3460;border-radius:8px;padding:0.5rem 1rem;font-size:0.88rem;color:#4e9eff;margin:0.3rem 0;">💡 자동 계산 평단가: <b style="color:white">{avg_price:,.0f}원/주</b> &nbsp;|&nbsp; 총 매수금액: <b style="color:white">{total_amount:,.0f}원</b></div>'
            st.markdown(avg_html, unsafe_allow_html=True)
        else:
            avg_price = 0

        if st.button("💾 기록 저장", disabled=(not sel_name or avg_price == 0)):
            entry = {
                "id":           int(time.time()),
                "kind":         kind,
                "name":         sel_name,
                "ticker":       sel_ticker,
                "date":         str(trade_dt),
                "qty":          int(qty),
                "buy_price":    round(avg_price, 2),
                "total_amount": int(total_amount),
                "status":       "보유" if kind == "매수" else "청산",
                "realized_pnl": 0,
            }
            portfolio.append(entry)
            save_portfolio(username, portfolio)
            st.success(f"✅ {sel_name} {kind} 기록 저장! (평단가: {avg_price:,.0f}원)")
            st.rerun()

    # 보유 종목 리스트
    active = [p for p in portfolio if p.get("status") == "보유"]
    if not active:
        st.info("보유 중인 종목이 없습니다.")
        return

    st.markdown("### 📋 보유 종목 현황")

    for p in active:
        cur     = get_price(p["ticker"])
        cost    = p["buy_price"] * p["qty"]
        val     = (cur or p["buy_price"]) * p["qty"]
        pnl     = val - cost
        pnl_pct = pnl / cost * 100 if cost else 0

        # 매매 가이드 계산
        df_hist = get_ohlcv_cached(p["ticker"], days=60)
        high20  = df_hist["high"].rolling(20).max().iloc[-1] if df_hist is not None and len(df_hist) >= 20 else None
        ma20    = df_hist["close"].rolling(20).mean().iloc[-1] if df_hist is not None and len(df_hist) >= 20 else None
        target  = p["buy_price"] * 1.20
        stoploss_pct = p["buy_price"] * 0.93
        stoploss = max(stoploss_pct, ma20) if ma20 else stoploss_pct

        # 알림은 모닝체크/관심종목 탭에서만 발생

        # 상태 색상
        if pnl_pct >= 20:
            border = "#00d4aa"; badge = "🎯 익절 구간"
        elif pnl_pct <= -7:
            border = "#ff4b6e"; badge = "🚨 손절 구간"
        elif pnl_pct <= -3:
            border = "#ffd766"; badge = "⚠️ 주의"
        else:
            border = "#4e9eff"; badge = "📌 보유 중"

        blink = 'class="blink-row"' if pnl_pct <= -7 or pnl_pct >= 20 else ''

        sign = "+" if pnl >= 0 else ""
        pnl_col = "#00d4aa" if pnl >= 0 else "#ff4b6e"

        st.markdown(f"""
        <div {blink} style="
            background:#1a1f2e; border:1px solid {border};
            border-left: 4px solid {border};
            border-radius:12px; padding:1rem; margin:0.5rem 0;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-weight:700; font-size:1.05rem;">{p['name']}</span>
                    <span style="color:#8892a4; font-size:0.8rem; margin-left:0.5rem;">{p['ticker']}</span>
                    <span style="background:{border}22; color:{border}; border-radius:6px;
                        padding:2px 8px; font-size:0.75rem; margin-left:0.5rem;">{badge}</span>
                </div>
                <div style="color:{pnl_col}; font-family:'JetBrains Mono',monospace;
                    font-weight:700; font-size:1.1rem;">
                    {sign}{pnl_pct:.2f}%
                </div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.5rem; margin-top:0.8rem; font-size:0.85rem;">
                <div><span style="color:#8892a4">평단가</span><br><b>{int(p.get('buy_price',0)):,}원</b></div>
                <div><span style="color:#8892a4">현재가</span><br><b style="color:{pnl_col}">{cur:,.0f}원</b></div>
                <div><span style="color:#8892a4">평가손익</span><br><b style="color:{pnl_col}">{sign}{pnl:,.0f}원</b></div>
                <div><span style="color:#8892a4">수량</span><br><b>{p['qty']}주</b></div>
                <div><span style="color:#8892a4">목표가 (+20%)</span><br><b style="color:#00d4aa">{target:,.0f}원</b></div>
                <div><span style="color:#8892a4">손절가 (-7%/MA20)</span><br><b style="color:#ff4b6e">{stoploss:,.0f}원</b></div>
            </div>
            {'<div style="margin-top:0.5rem; color:#ffd766; font-size:0.8rem;">📊 20일 신고가: ' + f'{high20:,.0f}원' + '</div>' if high20 else ''}
        </div>
        """, unsafe_allow_html=True)

        col_d, col_e, col_s = st.columns([1, 1, 1])
        with col_d:
            if st.button(f"청산 처리", key=f"sell_{p['id']}"):
                realized = (cur - p["buy_price"]) * p["qty"]
                for item in portfolio:
                    if item["id"] == p["id"]:
                        item["status"]       = "청산"
                        item["realized_pnl"] = realized
                        item["sell_price"]   = cur
                save_portfolio(username, portfolio)
                st.success(f"{p['name']} 청산 완료 (실현손익: {realized:+,.0f}원)")
                st.rerun()
        with col_e:
            if st.button(f"✏️ 수정", key=f"edit_{p['id']}"):
                st.session_state[f"editing_{p['id']}"] = True
        with col_s:
            if st.button(f"삭제", key=f"del_{p['id']}"):
                portfolio = [x for x in portfolio if x["id"] != p["id"]]
                save_portfolio(username, portfolio)
                st.rerun()

        # 수정 폼
        if st.session_state.get(f"editing_{p['id']}", False):
            with st.container():
                st.markdown("**✏️ 정보 수정**")
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    new_qty   = st.number_input("보유수량 (주)", value=int(p.get("qty",1)),
                                                 key=f"eq_{p['id']}", min_value=1)
                    new_date  = st.text_input("거래일", value=p.get("date",""), key=f"ed_{p['id']}")
                with ec2:
                    cur_total = int(p.get("total_amount", int(p.get("buy_price",0)) * int(p.get("qty",1))))
                    new_total = st.number_input("총 매수금액 (원)", value=cur_total,
                                                 key=f"ep_{p['id']}", step=10000, min_value=0)
                with ec3:
                    if new_qty > 0 and new_total > 0:
                        new_avg = new_total / new_qty
                        st.metric("자동 계산 평단가", f"{new_avg:,.0f}원")
                    else:
                        new_avg = 0
                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.button("💾 저장", key=f"esave_{p['id']}"):
                        for item in portfolio:
                            if item["id"] == p["id"]:
                                item["qty"]          = new_qty
                                item["total_amount"] = new_total
                                item["buy_price"]    = round(new_avg, 2)
                                item["date"]         = new_date
                        save_portfolio(username, portfolio)
                        st.session_state[f"editing_{p['id']}"] = False
                        st.success("✅ 수정 완료!")
                        st.rerun()
                with sc2:
                    if st.button("❌ 취소", key=f"ecancel_{p['id']}"):
                        st.session_state[f"editing_{p['id']}"] = False
                        st.rerun()

# ════════════════════════════════════════════════════════════
#  [3] 퀀트 스캐너
# ════════════════════════════════════════════════════════════
def page_quant(username: str):
    st.markdown("## 🧮 퀀트 스캐너")
    st.info("💡 **스캔 최적 시간 안내** — 스캐너는 장이 마감된 오후 3시 30분 이후 ~ 저녁 시간에 돌리는 것이 가장 정확합니다. 장중에는 종가와 거래대금이 계속 변동하므로 정확한 타점을 산출할 수 없습니다.")

    market = st.selectbox("시장 선택", ["KOSPI", "KOSDAQ", "전체"])
    top_n  = st.slider("상위 종목 수", 5, 30, 10)

    if st.button("🔍 퀀트 스캔 시작"):
        with st.spinner("데이터 수집 중..."):
            try:
                import FinanceDataReader as fdr
                results = []
                markets = ["KOSPI","KOSDAQ"] if market == "전체" else [market]
                for mkt in markets:
                    listing = fdr.StockListing(mkt)
                    listing.columns = [c.strip() for c in listing.columns]
                    code_col = next((c for c in listing.columns if c in ["Code","Symbol"]), None)
                    name_col = next((c for c in listing.columns if c in ["Name","종목명"]), None)
                    amt_col  = next((c for c in listing.columns if c in ["Amount","Tvalue"]), None)
                    if not code_col: continue
                    listing[code_col] = listing[code_col].astype(str).str.zfill(6)
                    sample = listing.nlargest(100, amt_col) if amt_col else listing.head(100)
                    for _, row in sample.iterrows():
                        ticker = str(row[code_col]).zfill(6)
                        name   = str(row.get(name_col, ticker))
                        try:
                            end   = datetime.now().strftime("%Y%m%d")
                            start = (datetime.now()-timedelta(days=380)).strftime("%Y%m%d")
                            df = fdr.DataReader(ticker, start, end)
                            if df is None or len(df) < 60: continue
                            for c in df.columns:
                                cl = c.strip().lower()
                                if cl in ("close","adj close"): df = df.rename(columns={c:"close"})
                            df["close"] = pd.to_numeric(df["close"], errors="coerce")
                            df = df.dropna(subset=["close"])
                            momentum = (df["close"].iloc[-1]/df["close"].iloc[0]-1)*100
                            vol_20   = df["close"].pct_change().rolling(20).std().iloc[-1]*100
                            score    = momentum*0.6 - vol_20*0.2
                            results.append({
                                "종목코드": ticker, "종목명": name, "시장": mkt,
                                "12개월수익률(%)": round(momentum,2),
                                "변동성(%)":      round(vol_20,2),
                                "퀀트점수":       round(score,2),
                                "현재가":         int(df["close"].iloc[-1]),
                            })
                        except: continue
                if results:
                    df_res = (pd.DataFrame(results)
                              .sort_values("퀀트점수", ascending=False)
                              .head(top_n).reset_index(drop=True))
                    df_res.index += 1
                    st.session_state["quant_records"] = df_res.to_dict("records")
                    st.session_state["quant_results"] = df_res[["종목코드","종목명"]].to_dict("records")
                    st.success(f"✅ {len(df_res)}개 종목 발굴!")
                else:
                    st.warning("결과 없음")
            except Exception as e:
                st.error(f"오류: {e}")

    records = st.session_state.get("quant_records", [])
    if not records:
        return

    df_show = pd.DataFrame(records)
    st.markdown(f"### 🏆 퀀트 점수 상위 {len(df_show)}개")
    fig = px.bar(df_show, x="종목명", y="퀀트점수",
                 color="퀀트점수", color_continuous_scale=["#ff4b6e","#ffd766","#00d4aa"],
                 template="plotly_dark")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=220, margin=dict(t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)

    # data_editor 체크박스
    st.markdown("#### 📋 종목 선택 후 일괄 추가")
    df_edit = df_show.copy()
    df_edit.insert(0, "선택", False)
    edited = st.data_editor(
        df_edit,
        column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)},
        disabled=[c for c in df_edit.columns if c != "선택"],
        use_container_width=True, hide_index=True, key="quant_editor",
    )
    sel = edited[edited["선택"] == True]
    st.caption(f"{len(sel)}개 선택됨")
    if st.button(f"➕ 선택한 {len(sel)}개 관심종목에 추가", type="primary",
                 disabled=len(sel)==0, key="quant_bulk"):
        added, today = 0, datetime.now().strftime("%Y-%m-%d")
        for _, row in sel.iterrows():
            cur_p = float(get_price(row["종목코드"]) or row["현재가"])
            r = add_to_watchlist(username=username, ticker=row["종목코드"], name=row["종목명"],
                source="퀀트", entry=int(cur_p), target=int(cur_p*1.20),
                stoploss=int(cur_p*0.93), market=row.get("시장",""),
                scan_date=today, base_price=cur_p)
            if r in ("added","updated"): added += 1
        st.success(f"✅ {added}개 관심종목에 추가! → [🗄️ 관심종목] 탭 확인")


def page_swing(username: str):
    st.markdown("## 📈 스윙 매매 스캐너")
    st.info("💡 **스캔 최적 시간 안내** — 스캐너는 장이 마감된 오후 3시 30분 이후 ~ 저녁 시간에 돌리는 것이 가장 정확합니다. 장중에는 종가와 거래대금이 계속 변동하므로 정확한 눌림목 타점을 산출할 수 없습니다.")

    with st.expander("⚙️ 스캔 조건 설정", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            min_chg  = st.number_input("최소 상승률 (%)", value=2.0, step=0.5) / 100
            max_chg  = st.number_input("최대 상승률 (%)", value=30.0, step=1.0) / 100
        with col2:
            min_val  = st.number_input("최소 거래대금 (억)", value=100, step=10) * 1e8
            rsi_min  = st.number_input("RSI 하한", value=50, step=5)
        with col3:
            rsi_max  = st.number_input("RSI 상한", value=85, step=5)
            market_s = st.selectbox("시장", ["KOSPI","KOSDAQ","전체"])

    if st.button("🔍 스윙 스캔 시작", type="primary"):
        progress = st.progress(0, text="종목 수집 중...")
        try:
            import FinanceDataReader as fdr
            import ta
            markets = ["KOSPI","KOSDAQ"] if market_s == "전체" else [market_s]
            tickers_all = []
            for mkt in markets:
                lst = fdr.StockListing(mkt)
                lst.columns = [c.strip() for c in lst.columns]
                code_col = next((c for c in lst.columns if c in ["Code","Symbol"]), None)
                name_col = next((c for c in lst.columns if c in ["Name","종목명"]), None)
                amt_col  = next((c for c in lst.columns if c in ["Amount","Tvalue"]), None)
                chg_col  = next((c for c in lst.columns if c in ["ChagesRatio","ChangeRate"]), None)
                if not code_col: continue
                lst[code_col] = lst[code_col].astype(str).str.zfill(6)
                mask = pd.Series([True]*len(lst), index=lst.index)
                if amt_col:
                    lst[amt_col] = pd.to_numeric(lst[amt_col], errors="coerce").fillna(0)
                    mask &= lst[amt_col] >= min_val
                if chg_col:
                    lst[chg_col] = pd.to_numeric(lst[chg_col], errors="coerce").fillna(0)
                    mx = lst[chg_col].abs().max()
                    lo, hi = min_chg*(100 if mx>1 else 1), max_chg*(100 if mx>1 else 1)
                    mask &= (lst[chg_col]>=lo)&(lst[chg_col]<=hi)
                for _, r in lst[mask].iterrows():
                    tickers_all.append({"ticker":str(r[code_col]).zfill(6),
                                        "name":str(r.get(name_col,"")),"market":mkt})
            progress.progress(10, text=f"사전 필터: {len(tickers_all)}개")
            results = []
            end   = datetime.now().strftime("%Y%m%d")
            start = (datetime.now()-timedelta(days=250)).strftime("%Y%m%d")
            for i, t in enumerate(tickers_all):
                if i%5==0:
                    pct = int(10+(i/max(len(tickers_all),1))*85)
                    progress.progress(pct, text=f"스캔 {i+1}/{len(tickers_all)} | 발굴: {len(results)}개")
                try:
                    df = fdr.DataReader(t["ticker"], start, end)
                    if df is None or len(df)<120: continue
                    col_map={}
                    for c in df.columns:
                        cl=c.strip().lower()
                        if cl=="open": col_map[c]="open"
                        elif cl=="high": col_map[c]="high"
                        elif cl=="low": col_map[c]="low"
                        elif cl in("close","adj close"): col_map[c]="close"
                        elif cl=="volume": col_map[c]="volume"
                    df=df.rename(columns=col_map)
                    for col in ["open","high","low","close","volume"]:
                        if col not in df.columns: continue
                        df[col]=pd.to_numeric(df[col],errors="coerce")
                    df=df.dropna(subset=["open","high","low","close","volume"])
                    df["trade_value"]=df["close"]*df["volume"]
                    df["ma5"]=df["close"].rolling(5).mean()
                    df["ma20"]=df["close"].rolling(20).mean()
                    df["ma120"]=df["close"].rolling(120).mean()
                    std=df["close"].rolling(20).std()
                    df["bb_upper"]=df["ma20"]+2*std
                    df["rsi"]=ta.momentum.RSIIndicator(df["close"],window=14).rsi()
                    df["prev_close"]=df["close"].shift(1)
                    df["prev_volume"]=df["volume"].shift(1)
                    df["ma5_prev"]=df["ma5"].shift(1)
                    df["ma20_prev"]=df["ma20"].shift(1)
                    row=df.iloc[-1]
                    pc=row["prev_close"]
                    if pd.isna(pc) or pc==0: continue
                    chg=(row["close"]-pc)/pc
                    if not(min_chg<=chg<=max_chg): continue
                    if row["trade_value"]<min_val: continue
                    pv=row["prev_volume"]
                    if pd.isna(pv) or pv==0 or row["volume"]<pv*0.7: continue
                    body=row["close"]-row["open"]
                    if body<=0 and chg<min_chg: continue
                    if any(pd.isna([row["ma5"],row["ma20"],row["ma120"]])): continue
                    if not(row["close"]>row["ma5"]>row["ma20"]): continue
                    if row["close"]<=row["ma120"]: continue
                    if pd.isna(row["bb_upper"]) or row["close"]<=row["bb_upper"]: continue
                    if pd.isna(row["rsi"]) or not(rsi_min<=row["rsi"]<=rsi_max): continue
                    disp=row["close"]/row["ma20"]
                    if not(0.98<=disp<=1.20): continue
                    ma5f=row["ma5_prev"] if not pd.isna(row["ma5_prev"]) else row["ma5"]
                    ma20f=row["ma20_prev"] if not pd.isna(row["ma20_prev"]) else row["ma20"]
                    entry=ma5f*0.975; target=entry*1.20; stoploss=max(entry*0.93,ma20f)
                    rr=(target-entry)/(entry-stoploss) if entry>stoploss else 0
                    results.append({
                        "종목명":t["name"],"종목코드":t["ticker"],"시장":t["market"],
                        "현재가":int(row["close"]),"등락률(%)":round(chg*100,2),
                        "거래대금(억)":round(row["trade_value"]/1e8,1),
                        "RSI":round(row["rsi"],1),"이격도(%)":round(disp*100,2),
                        "손익비":round(rr,2),
                        "매수타점":int(entry),"목표가(+20%)":int(target),"손절가(-7%)":int(stoploss),
                    })
                except: continue
            progress.progress(100, text="스캔 완료!")
            if results:
                df_out=(pd.DataFrame(results).sort_values("손익비",ascending=False).reset_index(drop=True))
                df_out.index+=1
                st.session_state["swing_records"]=df_out.to_dict("records")
                st.session_state["swing_results"]=df_out[["종목코드","종목명"]].to_dict("records")
                st.session_state["swing_results_full"]=df_out.to_dict("records")
                _tmp=user_file(username,"swing_temp.json")
                with open(_tmp,"w",encoding="utf-8") as _f:
                    json.dump(df_out.to_dict("records"),_f,ensure_ascii=False,indent=2)
                st.success(f"✅ {len(df_out)}개 종목 발굴!")
            else:
                st.warning("조건에 맞는 종목이 없습니다.")
        except Exception as e:
            st.error(f"오류: {e}")

    records = st.session_state.get("swing_records", [])
    if not records:
        return

    df_out = pd.DataFrame(records)
    st.markdown(f"### 📊 발굴 종목 {len(df_out)}개")

    # data_editor 체크박스
    disp = ["종목명","종목코드","시장","현재가","등락률(%)","RSI","손익비","매수타점","목표가(+20%)","손절가(-7%)"]
    avail = [c for c in disp if c in df_out.columns]
    df_edit = df_out[avail].copy()
    df_edit.insert(0, "선택", False)
    edited = st.data_editor(
        df_edit,
        column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)},
        disabled=[c for c in df_edit.columns if c != "선택"],
        use_container_width=True, hide_index=True, key="swing_editor",
    )
    sel = edited[edited["선택"] == True]
    n_sel, n_all = len(sel), len(df_out)

    ba, bb = st.columns([3,1])
    with ba:
        st.caption(f"{n_sel}개 선택 / 전체 {n_all}개")
        if st.button(f"➕ 선택한 {n_sel}개 관심종목에 추가", type="primary",
                     disabled=n_sel==0, key="swing_sel_add"):
            added, today = 0, datetime.now().strftime("%Y-%m-%d")
            for _, row in sel.iterrows():
                matched = next((r for r in records if r["종목코드"]==row["종목코드"]), None)
                if not matched: continue
                cur_p = float(matched.get("현재가", matched["매수타점"]))
                r2 = add_to_watchlist(username=username, ticker=matched["종목코드"],
                    name=matched["종목명"], source="스윙",
                    entry=int(matched["매수타점"]), target=int(matched["목표가(+20%)"]),
                    stoploss=int(matched["손절가(-7%)"]),
                    rsi=float(matched.get("RSI",0)), rr_ratio=float(matched.get("손익비",0)),
                    market=matched.get("시장",""), scan_date=today, base_price=cur_p)
                if r2 in ("added","updated"): added += 1
            st.success(f"✅ {added}개 관심종목 추가!")
            if added > 0: st.balloons()
    with bb:
        if st.button("🔥 전체 추가", key="swing_all_add"):
            added, today = 0, datetime.now().strftime("%Y-%m-%d")
            for row_w in records:
                cur_p = float(row_w.get("현재가", row_w["매수타점"]))
                r2 = add_to_watchlist(username=username, ticker=row_w["종목코드"],
                    name=row_w["종목명"], source="스윙",
                    entry=int(row_w["매수타점"]), target=int(row_w["목표가(+20%)"]),
                    stoploss=int(row_w["손절가(-7%)"]),
                    rsi=float(row_w.get("RSI",0)), rr_ratio=float(row_w.get("손익비",0)),
                    market=row_w.get("시장",""), scan_date=today,
                    base_price=float(row_w.get("현재가", row_w["매수타점"])))
                if r2 in ("added","updated"): added += 1
            st.success(f"✅ 전체 {added}개 추가!")
            if added > 0: st.balloons()


def page_super_signal(username: str):
    st.markdown("## 🚀 슈퍼 시그널")
    st.markdown("""
    <div class="card" style="border-left:4px solid #ffd766; margin-bottom:1rem;">
        <div style="color:#ffd766; font-weight:700; font-size:1rem;">⚡ 슈퍼 시그널이란?</div>
        <div style="color:#8892a4; font-size:0.85rem; margin-top:0.3rem; line-height:1.7;">
        퀀트 스캐너 + 스윙 매매 스캐너 <b style="color:white">두 시스템이 동시에 추천한 종목</b>만 표시합니다.<br>
        두 가지 독립적인 전략이 모두 선택한 종목 → <b style="color:#ffd766">최우선 매수 후보</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    quant_list = st.session_state.get("quant_results", [])
    swing_list = st.session_state.get("swing_results", [])

    col1, col2 = st.columns(2)
    with col1:
        q_status = f"✅ {len(quant_list)}개 로드됨" if quant_list else "❌ 미실행"
        st.markdown(f"""
        <div class="card card-info" style="text-align:center;">
            <div class="label">🧮 퀀트 스캐너</div>
            <div style="font-weight:700; color:#4e9eff;">{q_status}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        s_status = f"✅ {len(swing_list)}개 로드됨" if swing_list else "❌ 미실행"
        st.markdown(f"""
        <div class="card card-info" style="text-align:center;">
            <div class="label">📈 스윙 스캐너</div>
            <div style="font-weight:700; color:#4e9eff;">{s_status}</div>
        </div>""", unsafe_allow_html=True)

    if not quant_list or not swing_list:
        st.warning("⚠️ 퀀트 스캐너와 스윙 매매 스캐너를 **모두** 먼저 실행해 주세요!")
        st.markdown("""
        <div style="color:#8892a4; font-size:0.88rem; margin-top:0.5rem;">
        1️⃣ 🧮 퀀트 스캐너 탭 → 스캔 실행<br>
        2️⃣ 📈 스윙 매매 탭 → 스캔 실행<br>
        3️⃣ 🚀 슈퍼 시그널 탭으로 돌아오기
        </div>
        """, unsafe_allow_html=True)
        return

    # 공통 종목 찾기
    quant_codes = {q["종목코드"]: q["종목명"] for q in quant_list}
    swing_codes = {s["종목코드"]: s["종목명"] for s in swing_list}
    common_codes = set(quant_codes.keys()) & set(swing_codes.keys())

    st.markdown("---")

    if not common_codes:
        st.markdown("""
        <div class="card" style="text-align:center; padding:2rem;">
            <div style="font-size:2rem;">🔍</div>
            <div style="color:#8892a4; margin-top:0.5rem;">
                현재 두 스캐너에 공통 종목이 없습니다.<br>
                <span style="font-size:0.85rem;">스캔 조건을 조정하거나 다음 거래일에 다시 확인해 보세요.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # 🎉 공통 종목 발견!
    st.balloons()

    st.markdown(f"""
    <div style="text-align:center; margin:1rem 0;">
        <div style="font-size:2.5rem;">🎯</div>
        <div style="font-size:1.4rem; font-weight:900; color:#ffd766; margin:0.3rem 0;">
            슈퍼 시그널 {len(common_codes)}개 발견!
        </div>
        <div style="color:#8892a4; font-size:0.88rem;">
            두 시스템이 동시에 선택한 최우선 매수 후보입니다
        </div>
    </div>
    """, unsafe_allow_html=True)

    for code in common_codes:
        name = quant_codes[code]
        cur  = get_price(code)

        # 스윙 결과에서 상세 정보 가져오기
        swing_detail = next((s for s in st.session_state.get("swing_results_full", [])
                             if s.get("종목코드") == code), None)

        entry    = swing_detail["매수타점"]    if swing_detail else 0
        target   = swing_detail["목표가(+20%)"] if swing_detail else 0
        stoploss = swing_detail["손절가(-7%)"]  if swing_detail else 0
        rsi      = swing_detail["RSI"]          if swing_detail else "-"
        rr       = swing_detail["손익비"]       if swing_detail else "-"

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #1a1f2e, #16213e);
            border: 2px solid #ffd766;
            border-radius: 16px;
            padding: 1.2rem;
            margin: 0.6rem 0;
            box-shadow: 0 0 24px rgba(255,215,102,0.2);
        ">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
                <div>
                    <span style="font-size:1.15rem; font-weight:900;">{name}</span>
                    <span style="color:#8892a4; font-size:0.8rem; margin-left:0.5rem;">{code}</span>
                    <span style="background:#ffd76622; color:#ffd766; border-radius:6px;
                        padding:2px 10px; font-size:0.78rem; margin-left:0.5rem; font-weight:700;">
                        ⚡ 슈퍼 시그널
                    </span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.1rem;
                    font-weight:700; color:#4e9eff;">
                    {cur:,.0f}원
                </div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.5rem; font-size:0.85rem;">
                <div><span style="color:#8892a4">매수타점</span><br>
                    <b style="color:#ffd766">{entry:,.0f}원</b></div>
                <div><span style="color:#00d4aa">목표 +20%</span><br>
                    <b style="color:#00d4aa">{target:,.0f}원</b></div>
                <div><span style="color:#ff4b6e">손절 -7%</span><br>
                    <b style="color:#ff4b6e">{stoploss:,.0f}원</b></div>
                <div><span style="color:#8892a4">RSI</span><br><b>{rsi}</b></div>
                <div><span style="color:#8892a4">손익비</span><br><b>{rr}배</b></div>
                <div><span style="color:#8892a4">현재가</span><br><b>{cur:,.0f}원</b></div>
            </div>
            <div style="margin-top:0.8rem; padding:0.6rem; background:#ffd76611;
                border-radius:8px; font-size:0.82rem; color:#ffd766;">
                💡 퀀트(모멘텀) + 스윙(기술적지표) 동시 추천 — 최우선 매수 검토
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 관심종목 추가 버튼
        if st.button(f"🔖 {name} 관심종목 등록", key=f"super_{code}"):
            watchlist = load_watchlist(username)
            if any(w["ticker"] == code for w in watchlist):
                st.warning("이미 관심종목에 있습니다!")
            else:
                watchlist.append({
                    "id":        int(time.time()),
                    "name":      name,
                    "ticker":    code,
                    "market":    "",
                    "entry":     entry if entry else cur,
                    "target":    target if target else int(cur * 1.20),
                    "stoploss":  stoploss if stoploss else int(cur * 0.93),
                    "scan_date": datetime.now().strftime("%Y-%m-%d"),
                    "rsi":       rsi,
                })
                save_watchlist(username, watchlist)
                st.success(f"✅ {name} 관심종목 등록 완료!")

# ════════════════════════════════════════════════════════════
#  [5] 모닝 체크
# ════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════
#  [관심종목] 탭
# ════════════════════════════════════════════════════════════
def page_vault(username: str):
    st.markdown("## 🗄️ 관심종목")
    st.markdown(
        '<div class="card card-info" style="margin-bottom:1rem;">'
        '<div style="color:#4e9eff;font-weight:700;">💡 관심종목 사용법</div>'
        '<div style="color:#8892a4;font-size:0.83rem;margin-top:0.3rem;line-height:1.8;">'
        '• 퀀트/스윙 스캐너에서 추가한 종목이 영구 저장됩니다<br>'
        '• <b style="color:white">🌅 모닝체크</b> 열을 체크한 종목만 모닝체크에서 감시됩니다<br>'
        '• <b style="color:white">☑️ 선택</b> 후 [선택 삭제] 버튼으로 일괄 삭제 가능합니다'
        '</div></div>', unsafe_allow_html=True)

    wl = load_watchlist(username)
    if not wl:
        st.info("관심종목이 없습니다. 퀀트 또는 스윙 스캐너에서 종목을 추가하세요.")
        return

    active_cnt = sum(1 for w in wl if w.get("is_active", w.get("morning_check", False)))
    st.markdown(
        f'<div style="color:#8892a4;font-size:0.85rem;margin-bottom:0.6rem;">'
        f'총 <b style="color:white">{len(wl)}개</b> | 모닝체크 감시: <b style="color:#4e9eff">{active_cnt}개</b>'
        f'</div>', unsafe_allow_html=True)

    # 현재가 조회 + 수익률 계산
    rows, id_list = [], []
    for w in wl:
        cur      = float(get_price(w["ticker"]) or w.get("base_price", w.get("entry",0)))
        base     = float(w.get("base_price", w.get("entry", cur)))
        ret_pct  = round((cur-base)/base*100, 2) if base else 0.0
        is_act   = bool(w.get("is_active", w.get("morning_check", False)))
        id_list.append(w["id"])
        rows.append({
            "🌅 모닝체크": is_act,
            "☑️ 선택":    False,
            "종목명":      w["name"],
            "종목코드":    w["ticker"],
            "출처":        w.get("source","기타"),
            "등록일":      w.get("reg_date", w.get("add_date","")),
            "기준가":      int(base),
            "현재가":      int(cur),
            "수익률(%)":   ret_pct,
            "타점":        int(w.get("entry",0)),
            "목표가":      int(w.get("target",0)),
            "손절가":      int(w.get("stoploss",0)),
        })

    df_vault = pd.DataFrame(rows)
    edited = st.data_editor(
        df_vault,
        column_config={
            "🌅 모닝체크": st.column_config.CheckboxColumn("🌅 모닝체크", help="모닝체크 감시 포함"),
            "☑️ 선택":    st.column_config.CheckboxColumn("☑️ 선택",    help="삭제할 종목 선택"),
            "수익률(%)":   st.column_config.NumberColumn("수익률(%)", format="%.2f%%"),
            "기준가":      st.column_config.NumberColumn("기준가", format="%d원"),
            "현재가":      st.column_config.NumberColumn("현재가", format="%d원"),
        },
        disabled=["종목명","종목코드","출처","등록일","기준가","현재가","타점","목표가","손절가"],
        use_container_width=True,
        hide_index=True,
        key="vault_editor",
        height=min(500, 60+len(rows)*38),
    )

    # 모닝체크 상태 변경 즉시 저장
    changed = False
    for i, w in enumerate(wl):
        if i >= len(edited): break
        new_act = bool(edited.iloc[i]["🌅 모닝체크"])
        old_act = bool(w.get("is_active", w.get("morning_check", False)))
        if new_act != old_act:
            w["is_active"]      = new_act
            w["morning_check"]  = new_act
            changed = True
    if changed:
        save_watchlist(username, wl)

    # 선택 삭제
    sel_mask = edited["☑️ 선택"] == True
    n_sel    = int(sel_mask.sum())
    col_info, col_del = st.columns([3,1])
    with col_info:
        st.caption(f"{n_sel}개 선택됨")
        pos = sum(1 for r in rows if r["수익률(%)"]>0)
        neg = sum(1 for r in rows if r["수익률(%)"]<0)
        st.caption(f"수익 {pos}개 | 손실 {neg}개")
    with col_del:
        if st.button(f"🗑️ 선택 {n_sel}개 삭제", disabled=n_sel==0,
                     type="primary", key="vault_del"):
            ids_del = {id_list[i] for i, v in enumerate(sel_mask) if v}
            save_watchlist(username, [w for w in wl if w["id"] not in ids_del])
            st.success(f"✅ {n_sel}개 삭제 완료!")
            st.rerun()


def page_morning(username: str):
    st.markdown("## 🌅 모닝 체크")

    all_wl    = load_watchlist(username)
    watchlist = [w for w in all_wl
                 if w.get("is_active", w.get("morning_check", False))]

    if not watchlist:
        st.warning("감시 중인 종목이 없습니다.")
        st.info("👉 [🗄️ 관심종목] 탭에서 [🌅 모닝체크] 열을 체크해 주세요.")
        return

    col_r, col_tg, col_i = st.columns([1, 1, 3])
    with col_r:
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear(); st.rerun()
    with col_tg:
        send_tg = st.button("📨 텔레그램 전송", use_container_width=True)
    with col_i:
        st.markdown(
            f'<div style="color:#8892a4;font-size:0.85rem;padding:0.5rem 0;">'
            f'감시 <b style="color:white">{len(watchlist)}개</b> | {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            f'</div>', unsafe_allow_html=True)

    # 데이터 수집
    rows = []
    with st.spinner("현재가 조회 중..."):
        for w in watchlist:
            entry    = float(w.get("entry", 0))
            target   = float(w.get("target", entry * 1.20))
            stoploss = float(w.get("stoploss", entry * 0.93))
            source   = w.get("source", "기타")
            cur      = float(get_price(w["ticker"]) or entry)
            df_h     = get_ohlcv_cached(w["ticker"], days=5)
            low_t    = float(df_h["low"].iloc[-1])   if df_h is not None and len(df_h) > 0 else cur
            open_t   = float(df_h["open"].iloc[-1])  if df_h is not None and len(df_h) > 0 else cur
            prev_c   = float(df_h["close"].iloc[-2]) if df_h is not None and len(df_h) > 1 else cur
            diff_pct = (cur - entry) / entry * 100 if entry else 0
            chg_pct  = (cur - prev_c) / prev_c * 100 if prev_c else 0
            gap_pct  = (open_t - prev_c) / prev_c * 100 if prev_c else 0

            if low_t <= entry:    status, pri, sc = "✅ 타점 도달", 0, "#00d4aa"
            elif diff_pct <= 3:   status, pri, sc = "🔔 근접",     1, "#ffd766"
            elif gap_pct > 5:     status, pri, sc = "⚠️ 갭상승",   3, "#ff4b6e"
            else:                 status, pri, sc = "⏳ 대기",     2, "#8892a4"

            rows.append({
                "pri": pri, "status": status, "sc": sc,
                "name": w["name"], "ticker": w["ticker"], "source": source,
                "entry": entry, "target": target, "stoploss": stoploss,
                "cur": cur, "diff_pct": diff_pct, "chg_pct": chg_pct,
            })
    rows.sort(key=lambda x: x["pri"])

    # 상태 요약 배지
    cnt = {0:0, 1:0, 2:0, 3:0}
    for r in rows: cnt[r["pri"]] += 1
    b1, b2, b3, b4 = st.columns(4)
    for col, label, n, color in [
        (b1, "✅ 타점도달", cnt[0], "#00d4aa"),
        (b2, "🔔 근접",    cnt[1], "#ffd766"),
        (b3, "⏳ 대기",    cnt[2], "#8892a4"),
        (b4, "⚠️ 갭상승",  cnt[3], "#ff4b6e"),
    ]:
        col.markdown(
            f'<div style="background:{color}18;border:1px solid {color};'
            f'border-radius:10px;padding:0.5rem;text-align:center;">'
            f'<div style="color:{color};font-size:0.78rem;">{label}</div>'
            f'<div style="color:{color};font-family:JetBrains Mono,monospace;'
            f'font-size:1.5rem;font-weight:900;">{n}</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin:0.8rem 0'></div>", unsafe_allow_html=True)

    # 텔레그램 전송
    if send_tg:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"<b>🌅 모닝 체크 ({now_str})</b>\n감시 {len(rows)}개 종목\n\n"
        for r in rows:
            sgn = "+" if r["chg_pct"] >= 0 else ""
            src_icon = "🎯" if r["source"] == "스윙" else "📊"
            msg += (
                f"{src_icon} [{r['source']}] <b>{r['name']}</b> | {r['status']}\n"
                f"타점: {r['entry']:,.0f} / 목표: {r['target']:,.0f} / "
                f"손절: {r['stoploss']:,.0f} / 현재: {r['cur']:,.0f} "
                f"({sgn}{r['chg_pct']:.1f}%)\n\n"
            )
        send_telegram(msg)
        st.success("✅ 텔레그램 전송 완료!")

    # 종목 카드 (목표가/손절가 포함)
    src_colors = {"스윙": "#00d4aa", "퀀트": "#ffd766"}
    for r in rows:
        bc   = r["sc"]
        cc   = "#4e9eff" if r["chg_pct"] >= 0 else "#ff4b6e"
        sgn  = "+" if r["chg_pct"] >= 0 else ""
        dc   = "#00d4aa" if r["diff_pct"] <= 0 else ("#ffd766" if r["diff_pct"] <= 3 else "#8892a4")
        sc   = src_colors.get(r["source"], "#8892a4")
        blink = "animation:pulse 1.2s ease-in-out infinite;" if r["pri"] == 0 else ""

        st.markdown(
            f'<div style="background:#1a1f2e;border:2px solid {bc};border-radius:14px;'
            f'padding:1rem 1.2rem;margin:0.4rem 0;{blink}">'

            # 상단: 종목명 + 상태
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">'
            f'<div>'
            f'<span style="font-size:1.05rem;font-weight:700;">{r["name"]}</span>'
            f'<span style="color:#8892a4;font-size:0.75rem;margin-left:0.4rem;">{r["ticker"]}</span>'
            f'<span style="background:{sc}22;color:{sc};border-radius:5px;'
            f'padding:1px 7px;font-size:0.7rem;margin-left:0.4rem;">{r["source"]}</span>'
            f'</div>'
            f'<span style="background:{bc}22;color:{bc};border-radius:8px;'
            f'padding:4px 14px;font-size:0.95rem;font-weight:700;">{r["status"]}</span>'
            f'</div>'

            # 핵심 6가지 정보 (목표가/손절가 포함)
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr 1fr 1fr;gap:0.5rem;">'

            # 1. 매수타점
            f'<div style="background:#12172a;border-radius:10px;padding:0.55rem;text-align:center;">'
            f'<div style="color:#8892a4;font-size:0.68rem;margin-bottom:0.15rem;">💰 매수타점</div>'
            f'<div style="color:#ffd766;font-family:JetBrains Mono,monospace;font-size:0.9rem;font-weight:700;">{r["entry"]:,.0f}</div>'
            f'</div>'

            # 2. 현재가
            f'<div style="background:#12172a;border-radius:10px;padding:0.55rem;text-align:center;">'
            f'<div style="color:#8892a4;font-size:0.68rem;margin-bottom:0.15rem;">📊 현재가</div>'
            f'<div style="color:{cc};font-family:JetBrains Mono,monospace;font-size:0.9rem;font-weight:700;">{r["cur"]:,.0f}</div>'
            f'<div style="color:{cc};font-size:0.65rem;">{sgn}{r["chg_pct"]:.2f}%</div>'
            f'</div>'

            # 3. 목표가
            f'<div style="background:#12172a;border-radius:10px;padding:0.55rem;text-align:center;">'
            f'<div style="color:#8892a4;font-size:0.68rem;margin-bottom:0.15rem;">🎯 목표가</div>'
            f'<div style="color:#00d4aa;font-family:JetBrains Mono,monospace;font-size:0.9rem;font-weight:700;">{r["target"]:,.0f}</div>'
            f'<div style="color:#00d4aa;font-size:0.65rem;">+{(r["target"]-r["entry"])/r["entry"]*100:.1f}%</div>'
            f'</div>'

            # 4. 손절가
            f'<div style="background:#12172a;border-radius:10px;padding:0.55rem;text-align:center;">'
            f'<div style="color:#8892a4;font-size:0.68rem;margin-bottom:0.15rem;">🛑 손절가</div>'
            f'<div style="color:#ff4b6e;font-family:JetBrains Mono,monospace;font-size:0.9rem;font-weight:700;">{r["stoploss"]:,.0f}</div>'
            f'<div style="color:#ff4b6e;font-size:0.65rem;">{(r["stoploss"]-r["entry"])/r["entry"]*100:.1f}%</div>'
            f'</div>'

            # 5. 타점까지
            f'<div style="background:#12172a;border-radius:10px;padding:0.55rem;text-align:center;">'
            f'<div style="color:#8892a4;font-size:0.68rem;margin-bottom:0.15rem;">📍 타점까지</div>'
            f'<div style="color:{dc};font-family:JetBrains Mono,monospace;font-size:0.9rem;font-weight:700;">{r["diff_pct"]:+.2f}%</div>'
            f'</div>'

            # 6. 상태
            f'<div style="background:{bc}18;border-radius:10px;padding:0.55rem;text-align:center;">'
            f'<div style="color:#8892a4;font-size:0.68rem;margin-bottom:0.15rem;">🚦 상태</div>'
            f'<div style="color:{bc};font-size:1rem;font-weight:700;">{r["status"]}</div>'
            f'</div>'

            f'</div></div>',
            unsafe_allow_html=True)

    st.markdown("---")
    st.caption("💡 종목 관리는 [🗄️ 관심종목] 탭의 [🌅 모닝체크] 열에서 하세요.")


# ════════════════════════════════════════════════════════════
#  메인
# ════════════════════════════════════════════════════════════
def main():
    # 로그인 체크
    if "user" not in st.session_state:
        show_login()
        return

    username = st.session_state["user"]

    # 사이드바
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:1rem 0 0.5rem;">
            <div style="font-size:2rem;">📈</div>
            <div style="font-weight:700; color:#4e9eff;">스윙 대시보드</div>
            <div style="color:#8892a4; font-size:0.8rem;">👤 {username}</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        menu = st.radio("메뉴", [
            "📊 대시보드",
            "💼 내 포트폴리오",
            "🧮 퀀트 스캐너",
            "📈 스윙 매매",
            "🚀 슈퍼 시그널",
            "🗄️ 관심종목",
            "🌅 모닝 체크",
        ], label_visibility="collapsed")

        st.divider()
        if st.button("🔔 알림 초기화"):
            json.dump([], open(user_file(username,"notifications.json"),"w"))
            st.rerun()
        if st.button("🚪 로그아웃"):
            del st.session_state["user"]
            st.rerun()

        st.markdown(f"""
        <div style="color:#8892a4; font-size:0.75rem; margin-top:1rem;">
            {datetime.now().strftime("%Y-%m-%d %H:%M")}
        </div>
        """, unsafe_allow_html=True)

    # 알림바 — 모닝체크/관심종목 탭에서만 표시
    if menu in ["🌅 모닝 체크"]:
        show_notification_bar(username)

    # 페이지 라우팅
    if menu == "📊 대시보드":
        page_dashboard(username)
    elif menu == "💼 내 포트폴리오":
        page_portfolio(username)
    elif menu == "🧮 퀀트 스캐너":
        page_quant(username)
    elif menu == "📈 스윙 매매":
        page_swing(username)
    elif menu == "🚀 슈퍼 시그널":
        page_super_signal(username)
    elif menu == "🗄️ 관심종목":
        page_vault(username)
    elif menu == "🌅 모닝 체크":
        page_morning(username)


if __name__ == "__main__":
    main()
