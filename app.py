"""
스윙 매매 전용 수급 스캐너
외국인 + 기관 쌍끌이 Top 20 종목 발굴
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="수급 스캐너",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
    background: #0f1117;
    color: #e2e8f0;
}
.main .block-container { padding: 1rem 1.5rem 3rem; max-width: 100%; }

.card {
    background: #1e2535;
    border: 1px solid #2d3748;
    border-radius: 14px;
    padding: 1rem 1.1rem;
    margin: 0.3rem 0;
    transition: transform 0.15s;
}
.card:hover { transform: translateY(-2px); }
.card-double { border-top: 3px solid #38bdf8; }
.card-foreign { border-top: 3px solid #34d399; }
.card-inst   { border-top: 3px solid #a78bfa; }

.ticker-name { font-size: 1rem; font-weight: 700; margin-bottom: 0.1rem; }
.ticker-code { color: #94a3b8; font-size: 0.72rem; }
.badge {
    display: inline-block;
    border-radius: 5px; padding: 1px 8px;
    font-size: 0.7rem; font-weight: 600; margin-left: 0.3rem;
}
.badge-double { background:#38bdf822; color:#38bdf8; }
.badge-green  { background:#34d39922; color:#34d399; }
.badge-purple { background:#a78bfa22; color:#a78bfa; }

.num-pos { color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-weight: 700; }
.num-neg { color: #f87171; font-family: 'JetBrains Mono', monospace; font-weight: 700; }
.label   { color: #94a3b8; font-size: 0.72rem; margin-bottom: 0.1rem; }

.summary-box {
    background: #1e2535; border: 1px solid #2d3748;
    border-radius: 12px; padding: 0.7rem 1.2rem;
    text-align: center;
}
@media (max-width: 768px) {
    .main .block-container { padding: 0.4rem 0.4rem 2rem; }
    .card { padding: 0.7rem 0.8rem; }
}
</style>
""", unsafe_allow_html=True)


# ── 데이터 수집 함수 ─────────────────────────────────────────
@st.cache_data(ttl=1800)
def get_supply_data(market: str, days: int = 5) -> pd.DataFrame:
    """pykrx로 외국인·기관 순매수 합산 데이터 수집"""
    try:
        from pykrx import stock as krx

        end_dt   = datetime.now()
        start_dt = end_dt - timedelta(days=days * 2 + 5)  # 영업일 여유
        end_str  = end_dt.strftime("%Y%m%d")
        start_str = start_dt.strftime("%Y%m%d")

        # 전체 종목 리스트
        tickers = krx.get_market_ticker_list(end_str, market=market)
        if not tickers:
            return pd.DataFrame()

        all_rows = []
        prog = st.progress(0, text=f"{market} 수급 데이터 수집 중...")

        for i, ticker in enumerate(tickers):
            try:
                # 투자자별 순매수 (기간 합산)
                df = krx.get_market_net_purchases_of_equities(
                    start_str, end_str, ticker
                )
                if df is None or df.empty:
                    continue

                # 컬럼명 정규화
                df.columns = [c.strip() for c in df.columns]

                # 외국인·기관 컬럼 찾기
                foreign_col = next((c for c in df.columns
                                    if "외국인" in c or "외인" in c), None)
                inst_col    = next((c for c in df.columns
                                    if "기관" in c), None)

                if not foreign_col or not inst_col:
                    continue

                foreign_sum = pd.to_numeric(df[foreign_col], errors="coerce").sum()
                inst_sum    = pd.to_numeric(df[inst_col],    errors="coerce").sum()

                name = krx.get_market_ticker_name(ticker)
                all_rows.append({
                    "종목코드": ticker,
                    "종목명":   name,
                    "시장":     market,
                    "외국인순매수": int(foreign_sum),
                    "기관순매수":   int(inst_sum),
                })
            except Exception:
                continue
            finally:
                pct = int((i + 1) / len(tickers) * 100)
                if i % 10 == 0:
                    prog.progress(pct, text=f"{market} 수집 중... {i+1}/{len(tickers)}")

        prog.progress(100, text=f"{market} 완료!")
        return pd.DataFrame(all_rows)

    except Exception as e:
        st.error(f"데이터 수집 실패: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def get_current_price(ticker: str) -> int:
    """현재가 조회"""
    try:
        from pykrx import stock as krx
        today = datetime.now().strftime("%Y%m%d")
        df = krx.get_market_ohlcv(today, today, ticker)
        if df is not None and len(df) > 0:
            return int(df["종가"].iloc[-1])
    except Exception:
        pass
    return 0


# ── 메인 UI ──────────────────────────────────────────────────
st.markdown("## 📡 수급 스캐너")
st.markdown("외국인 + 기관 **쌍끌이** 종목 발굴 — 최근 5거래일 순매수 합산 기준")

# 설정 사이드바
with st.sidebar:
    st.markdown("### ⚙️ 스캔 설정")
    market_sel = st.selectbox("시장", ["KOSPI", "KOSDAQ", "전체"])
    top_n      = st.slider("Top N 종목", 10, 50, 20)
    days_sel   = st.slider("집계 기간 (거래일)", 3, 20, 5)
    show_price = st.checkbox("현재가 표시 (느려짐)", value=False)

# 스캔 버튼
if st.button("🔍 수급 스캔 시작", type="primary", use_container_width=False):
    st.session_state["scan_done"] = False

    markets = ["KOSPI", "KOSDAQ"] if market_sel == "전체" else [market_sel]
    all_df  = []

    for mkt in markets:
        df = get_supply_data(mkt, days_sel)
        if not df.empty:
            all_df.append(df)

    if all_df:
        combined = pd.concat(all_df, ignore_index=True)
        # 쌍끌이 필터: 외국인 > 0 AND 기관 > 0
        double = combined[
            (combined["외국인순매수"] > 0) &
            (combined["기관순매수"]   > 0)
        ].copy()

        # 기관 순매수 내림차순 Top N
        double = (double
                  .sort_values("기관순매수", ascending=False)
                  .head(top_n)
                  .reset_index(drop=True))

        st.session_state["result_df"] = double.to_dict("records")
        st.session_state["scan_done"] = True
        st.session_state["scan_market"] = market_sel
        st.session_state["scan_days"]   = days_sel
    else:
        st.warning("데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")


# ── 결과 표시 ────────────────────────────────────────────────
records = st.session_state.get("result_df", [])
if not records:
    st.info("👆 스캔 버튼을 눌러 쌍끌이 종목을 찾아보세요!")
    st.stop()

df_res = pd.DataFrame(records)

# 요약 통계
st.markdown("---")
s1, s2, s3, s4 = st.columns(4)
total_foreign = int(df_res["외국인순매수"].sum())
total_inst    = int(df_res["기관순매수"].sum())
scan_market   = st.session_state.get("scan_market", "")
scan_days     = st.session_state.get("scan_days", 5)

for col, label, val, color in [
    (s1, "🔍 쌍끌이 종목",  f"{len(records)}개",          "#38bdf8"),
    (s2, "🌍 외국인 합산",  f"{total_foreign/1e8:.1f}억", "#34d399"),
    (s3, "🏦 기관 합산",    f"{total_inst/1e8:.1f}억",    "#a78bfa"),
    (s4, "📅 집계 기간",    f"{scan_days}거래일",          "#fbbf24"),
]:
    col.markdown(
        f'<div class="summary-box">'
        f'<div style="color:#94a3b8;font-size:0.75rem;">{label}</div>'
        f'<div style="color:{color};font-family:JetBrains Mono,monospace;'
        f'font-size:1.3rem;font-weight:900;">{val}</div>'
        f'</div>', unsafe_allow_html=True)

st.markdown(f"<div style='color:#94a3b8;font-size:0.8rem;margin:0.5rem 0;'>"
            f"기관 순매수 내림차순 Top {len(records)}개 | {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준"
            f"</div>", unsafe_allow_html=True)

# 4열 카드
cols_per_row = 4
for row_i in range(0, len(records), cols_per_row):
    row_recs = records[row_i: row_i + cols_per_row]
    cols     = st.columns(cols_per_row)

    for col, r in zip(cols, row_recs):
        rank       = row_i + records.index(r) + 1
        foreign    = r["외국인순매수"]
        inst       = r["기관순매수"]
        f_str      = f"+{foreign/1e4:,.0f}만" if foreign >= 0 else f"{foreign/1e4:,.0f}만"
        i_str      = f"+{inst/1e4:,.0f}만"    if inst    >= 0 else f"{inst/1e4:,.0f}만"
        f_cls      = "num-pos" if foreign >= 0 else "num-neg"
        i_cls      = "num-pos" if inst    >= 0 else "num-neg"

        # 현재가 (옵션)
        price_html = ""
        if show_price:
            cur = get_current_price(r["종목코드"])
            if cur:
                price_html = (f'<div class="label" style="margin-top:0.4rem;">현재가</div>'
                              f'<div class="num-pos">{cur:,}원</div>')

        col.markdown(
            f'<div class="card card-double">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            f'<div>'
            f'<div class="ticker-name">#{rank} {r["종목명"]}</div>'
            f'<span class="ticker-code">{r["종목코드"]}</span>'
            f'<span class="badge badge-double">쌍끌이</span>'
            f'</div>'
            f'<span style="color:#94a3b8;font-size:0.75rem;">{r["시장"]}</span>'
            f'</div>'
            f'<div style="margin-top:0.6rem;">'
            f'<div class="label">🌍 외국인 순매수</div>'
            f'<div class="{f_cls}">{f_str}</div>'
            f'</div>'
            f'<div style="margin-top:0.4rem;">'
            f'<div class="label">🏦 기관 순매수</div>'
            f'<div class="{i_cls}">{i_str}</div>'
            f'</div>'
            f'{price_html}'
            f'</div>',
            unsafe_allow_html=True)

# 전체 테이블
st.markdown("---")
st.markdown("### 📋 전체 결과 테이블")
df_display = df_res.copy()
df_display["외국인순매수(만)"] = (df_display["외국인순매수"] / 1e4).round(0).astype(int)
df_display["기관순매수(만)"]   = (df_display["기관순매수"]   / 1e4).round(0).astype(int)
st.dataframe(
    df_display[["종목명","종목코드","시장","외국인순매수(만)","기관순매수(만)"]],
    use_container_width=True, hide_index=True,
)
