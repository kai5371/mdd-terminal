import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 0. 프리미엄 금융 앱 테마 스타일 주입
st.set_page_config(layout="wide", page_title="MDD 터미널", page_icon="📈")

st.markdown("""
    <style>
        /* 다크모드 권장 가이드 패널 - 어떤 테마에서도 텍스트가 잘 보이도록 강제 색상 지정 */
        .theme-notice-box-enhanced {
            background-color: rgba(0, 0, 0, 0.05) !important; /* 배경을 아주 살짝만 어둡게 */
            border: 1px solid #3b82f6 !important; /* 테두리를 파란색으로 명확하게 */
            padding: 18px;
            border-radius: 12px;
            margin-bottom: 25px;
        }
        .theme-notice-title-enhanced {
            font-size: 14px !important; 
            font-weight: 800 !important; 
            color: #1e40af !important; /* 진한 파란색 제목 */
            display: flex; align-items: center; gap: 6px; margin-bottom: 10px;
        }
        /* 핵심: 폰트 색상을 '가장 어두운 파란색'으로 고정하여 배경 대비 최대화 */
        .theme-notice-text-enhanced {
            font-size: 14px !important; 
            color: #111827 !important; /* 짙은 색으로 고정 (화이트 모드에서도 보임) */
            line-height: 1.6 !important; 
            font-weight: 600 !important;
        }
        .menu-icon {
            font-weight: bold !important; color: #1e40af !important; padding: 0 4px;
        }
        
        /* 나머지 UI 스타일은 유지 */
        html, body, [data-testid="stAppViewContainer"] { background-color: #090d16 !important; font-family: 'Inter', sans-serif; }
        .main-title { font-size: 28px; font-weight: 700; color: #f8fafc; letter-spacing: -0.5px; margin-bottom: 25px; }
        .asset-card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 24px; margin-bottom: 20px; }
        /* (중략 - 기존 나머지 스타일 동일) */
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📈 MDD 터미널</p>', unsafe_allow_html=True)

# --- [사이드바 설정] ---
st.sidebar.markdown("### ⚙️ 시스템 설정")

# 다크모드 안내 패널
st.sidebar.markdown("""
    <div class="theme-notice-box-enhanced">
        <div class="theme-notice-title-enhanced">💡 화면 설정 안내</div>
        <div class="theme-notice-text-enhanced">
            화면이 하얗게 보이신다면 우측 상단 <b><span class="menu-icon">⋮</span> 메뉴에서 <b>Dark</b>를 선택해 주세요.
        </div>
    </div>
""", unsafe_allow_html=True)

with st.sidebar.expander("ℹ️ 종목 코드 검색 방법 보기"):
    st.markdown("""
    * **미국 시장 (ETF / 주식)**
      * 티커 명칭을 그대로 대문자로 입력합니다.
      * *예: QQQ, SPY, JEPQ, AAPL*
    * **한국 시장 (코스피 / 코스닥 / 국산 ETF)**
      * 6자리 종목 코드 뒤에 시장 접미사를 붙입니다.
      * *코스피 및 국산 ETF:* `.KS` (예: `133690.KS`)
      * *코스닥 종목:* `.KQ` (예: `091990.KQ`)
    """)

ticker = st.sidebar.text_input("종목 코드", "QQQ", placeholder="예: QQQ 또는 133690.KS").upper()
today = datetime.today().date()
start_date = st.sidebar.date_input("분석 시작일", datetime(2006, 1, 1), min_value=datetime(1920, 1, 1), max_value=today)

if 'reset_trigger' not in st.session_state:
    st.session_state['reset_trigger'] = 0

end_date = st.sidebar.date_input(
    "분석 종료일", 
    value=today, 
    min_value=datetime(1920, 1, 1), 
    max_value=today,
    key=f"end_date_widget_{st.session_state['reset_trigger']}"
)

if st.sidebar.button("👉 종료일을 오늘 날짜로 변경하기", use_container_width=False):
    st.session_state['reset_trigger'] += 1
    st.rerun()

def load_pure_data(ticker, start, end):
    ticker_obj = yf.Ticker(ticker)
    currency = "USD"
    try:
        info = ticker_obj.info
        if 'currency' in info: currency = info['currency'].upper()
    except:
        if ticker.endswith(".KS") or ticker.endswith(".KQ"): currency = "KRW"

    raw_ticker = ticker_obj.history(start=start, end=end)
    if raw_ticker.empty:
        raw_ticker = yf.download(ticker, start=start, end=end)
        if raw_ticker.empty: return None, None, None, None, None, None, None, "USD"
        
    if isinstance(raw_ticker.columns, pd.MultiIndex):
        raw_ticker.columns = raw_ticker.columns.get_level_values(0)
    raw_ticker.index = raw_ticker.index.tz_localize(None)
    
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    raw_ticker = raw_ticker[(raw_ticker.index >= start_dt) & (raw_ticker.index <= end_dt)]
    
    fx = yf.download("KRW=X", start=start, end=end)
    if not fx.empty and isinstance(fx.columns, pd.MultiIndex): fx.columns = fx.columns.get_level_values(0)
    fx = fx[['Close']] if not fx.empty else pd.DataFrame()
    fx.columns = ['Exchange_Rate']
    fx.index = fx.index.tz_localize(None)
    
    oil = yf.download("CL=F", start=start, end=end)
    if not oil.empty and isinstance(oil.columns, pd.MultiIndex): oil.columns = oil.columns.get_level_values(0)
    oil = oil[['Close']] if not oil.empty else pd.DataFrame()
    oil.columns = ['Oil_Price']
    oil.index = oil.index.tz_localize(None)
    
    current_fx = fx['Exchange_Rate'].iloc[-1] if not fx.empty else 1350.0
    prev_fx = fx['Exchange_Rate'].iloc[-2] if len(fx) >= 2 else current_fx
    fx_chg = current_fx - prev_fx
    fx_pct = (fx_chg / prev_fx) * 100 if current_fx != 0 else 0.0

    current_oil = oil['Oil_Price'].iloc[-1] if not oil.empty else 0.0
    prev_oil = oil['Oil_Price'].iloc[-2] if len(oil) >= 2 else current_oil
    oil_chg = current_oil - prev_oil
    oil_pct = (oil_chg / prev_oil) * 100 if current_oil != 0 else 0.0

    common_index = raw_ticker.dropna(subset=['Close']).index.intersection(fx.dropna().index).intersection(oil.dropna().index)
    
    df = pd.DataFrame(index=common_index)
    df['Exchange_Rate'] = fx.loc[common_index, 'Exchange_Rate'].values
    
    raw_close = raw_ticker.loc[common_index, 'Close'].values
    if currency == "KRW":
        df['KRW_Price'] = raw_close
        df['USD_Price'] = raw_close / df['Exchange_Rate']
    else:
        df['USD_Price'] = raw_close
        df['KRW_Price'] = raw_close * df['Exchange_Rate']
    
    return df, current_fx, fx_chg, fx_pct, current_oil, oil_chg, oil_pct, currency

df, live_fx, fx_chg, fx_pct, live_oil, oil_chg, oil_pct, base_currency = load_pure_data(ticker, start_date, end_date)

if live_fx:
    fx_sign = "+" if fx_chg >= 0 else ""
    fx_color = "#ef4444" if fx_chg >= 0 else "#3b82f6"
    st.sidebar.markdown(f"""
        <div class="sidebar-macro-box" style="border-left: 4px solid #3b82f6;">
            <div style="color: #9ca3af; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;">실시간 원/달러 환율</div>
            <div style="font-size: 22px; font-weight: 700; color: #ffffff; margin-top: 2px;">₩{live_fx:,.2f}</div>
            <div style="font-size: 12px; color: {fx_color}; font-weight: 600; margin-top: 2px;">{fx_sign}{fx_chg:,.2f} ({fx_sign}{fx_pct:.2f}%)</div>
        </div>
    """, unsafe_allow_html=True)

if live_oil:
    oil_sign = "+" if oil_chg >= 0 else ""
    oil_color = "#ef4444" if oil_chg >= 0 else "#3b82f6"
    st.sidebar.markdown(f"""
        <div class="sidebar-macro-box" style="border-left: 4px solid #f59e0b;">
            <div style="color: #9ca3af; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;">WTI 국제 유가</div>
            <div style="font-size: 22px; font-weight: 700; color: #ffffff; margin-top: 2px;">${live_oil:,.2f} <span style="font-size:12px; color:#6b7280; font-weight:400;">/ bbl</span></div>
            <div style="font-size: 12px; color: {oil_color}; font-weight: 600; margin-top: 2px;">{oil_sign}{oil_chg:,.2f} ({oil_sign}{oil_pct:.2f}%)</div>
        </div>
    """, unsafe_allow_html=True)

if df is None or df.empty:
    st.error("데이터를 불러오지 못했습니다. 종목 코드와 날짜를 다시 확인해 주세요.")
else:
    def calculate_metrics(series):
        peaks = series.cummax()
        drawdowns = (series - peaks) / peaks
        mdd = drawdowns.min()
        mdd_date = drawdowns.idxmin()
        return drawdowns, mdd, mdd_date, peaks

    df['USD_DD'], usd_mdd, usd_mdd_date, df['USD_Peak'] = calculate_metrics(df['USD_Price'])
    df['KRW_DD'], krw_mdd, krw_mdd_date, df['KRW_Peak'] = calculate_metrics(df['KRW_Price'])

    total_days = len(df)
    usd_current_dd = df['USD_DD'].iloc[-1] * 100
    krw_current_dd = df['KRW_DD'].iloc[-1] * 100

    usd_current = df['USD_Price'].iloc[-1]
    usd_peak_max = df['USD_Peak'].max()
    krw_current = df['KRW_Price'].iloc[-1]
    krw_peak_max = df['KRW_Peak'].max()

    usd_t10, usd_t15, usd_t20 = usd_peak_max * 0.90, usd_peak_max * 0.85, usd_peak_max * 0.80
    krw_t10, krw_t15, krw_t20 = krw_peak_max * 0.90, krw_peak_max * 0.85, krw_peak_max * 0.80
    y_min_limit = min(usd_mdd, krw_mdd) * 100 - 5

    usd_html = f"""
        <div class="asset-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:16px; font-weight:700; color:#38bdf8;">💵 달러(USD) 기준 거래가 통계</span>
                <span style="font-size:12px; color:#ef4444; font-weight:700; background:rgba(239,68,68,0.1); padding:4px 8px; border-radius:6px;">현재 낙폭 {usd_current_dd:.1f}%</span>
            </div>
            <div style="font-size: 38px; font-weight: 700; color: #f9fafb; margin-top: 15px;">${usd_current:,.2f}</div>
            <div style="font-size: 13px; color: #6b7280; margin-top: 2px;">역사적 최고가: <span style="color:#9ca3af; font-weight:600;">${usd_peak_max:,.2f}</span></div>
            <div class="metric-grid">
                <div class="metric-item"><div class="metric-label">전고점 대비 -10%</div><div class="metric-value">${usd_t10:,.2f}</div></div>
                <div class="metric-item"><div class="metric-label">전고점 대비 -15%</div><div class="metric-value">${usd_t15:,.2f}</div></div>
                <div class="metric-item"><div class="metric-label">전고점 대비 -20%</div><div class="metric-value">${usd_t20:,.2f}</div></div>
            </div>
            <div style="margin-top:16px; padding-top:12px; border-top:1px solid #1f2937; font-size:14px; color:#9ca3af;">
                📉 역사적 <b>최대 하락률(MDD):</b> <span style="color:#ef4444; font-weight:700; font-size:15px;">{usd_mdd*100:.1f}%</span> <span style="font-size:12px; color:#6b7280;">({usd_mdd_date.strftime('%Y-%m-%d')})</span>
            </div>
        </div>
    """

    krw_html = f"""
        <div class="asset-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:16px; font-weight:700; color:#a855f7;">₩ 원화(KRW) 기준 거래가 통계</span>
                <span style="font-size:12px; color:#3b82f6; font-weight:700; background:rgba(59,130,246,0.1); padding:4px 8px; border-radius:6px;">현재 낙폭 {krw_current_dd:.1f}%</span>
            </div>
            <div style="font-size: 38px; font-weight: 700; color: #f9fafb; margin-top: 15px;">₩{int(krw_current):,}</div>
            <div style="font-size: 13px; color: #6b7280; margin-top: 2px;">역사적 최고가: <span style="color:#9ca3af; font-weight:600;">₩{int(krw_peak_max):,}</span></div>
            <div class="metric-grid">
                <div class="metric-item"><div class="metric-label">전고점 대비 -10%</div><div class="metric-value">₩{int(krw_t10):,}</div></div>
                <div class="metric-item"><div class="metric-label">전고점 대비 -15%</div><div class="metric-value">₩{int(krw_t15):,}</div></div>
                <div class="metric-item"><div class="metric-label">전고점 대비 -20%</div><div class="metric-value">₩{int(krw_t20):,}</div></div>
            </div>
            <div style="margin-top:16px; padding-top:12px; border-top:1px solid #1f2937; font-size:14px; color:#9ca3af;">
                📉 역사적 <b>최대 하락률(MDD):</b> <span style="color:#3b82f6; font-weight:700; font-size:15px;">{krw_mdd*100:.1f}%</span> <span style="font-size:12px; color:#6b7280;">({krw_mdd_date.strftime('%Y-%m-%d')})</span>
            </div>
        </div>
    """

    col1, col2 = st.columns(2)
    if base_currency == "KRW":
        with col1: st.markdown(krw_html, unsafe_allow_html=True)
        with col2: st.markdown(usd_html, unsafe_allow_html=True)
    else:
        with col1: st.markdown(usd_html, unsafe_allow_html=True)
        with col2: st.markdown(krw_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    main_col, side_col = st.columns([2.8, 1.2])

    with main_col:
        chart_mode = st.radio("📈 차트 보기 모드 선택", ["단독 차트 보기", "달러 vs 원화 낙폭 겹쳐보기"], horizontal=True)
        st.markdown("<br>", unsafe_allow_html=True)

        if chart_mode == "단독 차트 보기":
            if base_currency == "KRW":
                st.markdown(f"### 📊 {ticker} 원화 기준 하락률(DD) 추세")
                fig_krw = go.Figure()
                fig_krw.add_trace(go.Scatter(x=df.index, y=df['KRW_DD'] * 100, mode='lines', line=dict(color='#3b82f6', width=1.5), fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.08)', name='원화 DD'))
                fig_krw.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(ticksuffix="%", range=[y_min_limit, 5], gridcolor='#1f2937'), xaxis=dict(gridcolor='#1f2937'), height=320, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified")
                st.plotly_chart(fig_krw, use_container_width=True)

                st.markdown(f"### 📊 {ticker} 달러 기준 하락률(DD) 추세")
                fig_usd = go.Figure()
                fig_usd.add_trace(go.Scatter(x=df.index, y=df['USD_DD'] * 100, mode='lines', line=dict(color='#ef4444', width=1.5), fill='tozeroy', fillcolor='rgba(239, 68, 68, 0.08)', name='달러 DD'))
                fig_usd.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(ticksuffix="%", range=[y_min_limit, 5], gridcolor='#1f2937'), xaxis=dict(gridcolor='#1f2937'), height=320, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified")
                st.plotly_chart(fig_usd, use_container_width=True)
            else:
                st.markdown(f"### 📊 {ticker} 달러 기준 하락률(DD) 추세")
                fig_usd = go.Figure()
                fig_usd.add_trace(go.Scatter(x=df.index, y=df['USD_DD'] * 100, mode='lines', line=dict(color='#ef4444', width=1.5), fill='tozeroy', fillcolor='rgba(239, 68, 68, 0.08)', name='달러 DD'))
                fig_usd.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(ticksuffix="%", range=[y_min_limit, 5], gridcolor='#1f2937'), xaxis=dict(gridcolor='#1f2937'), height=320, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified")
                st.plotly_chart(fig_usd, use_container_width=True)

                st.markdown(f"### 📊 {ticker} 원화 기준 하락률(DD) 추세")
                fig_krw = go.Figure()
                fig_krw.add_trace(go.Scatter(x=df.index, y=df['KRW_DD'] * 100, mode='lines', line=dict(color='#3b82f6', width=1.5), fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.08)', name='원화 DD'))
                fig_krw.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(ticksuffix="%", range=[y_min_limit, 5], gridcolor='#1f2937'), xaxis=dict(gridcolor='#1f2937'), height=320, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified")
                st.plotly_chart(fig_krw, use_container_width=True)
        else:
            st.markdown("### 🔄 달러 및 원화 낙폭 복합 오버레이 분석")
            fig_overlay = go.Figure()
            fig_overlay.add_trace(go.Scatter(x=df.index, y=df['USD_DD'] * 100, mode='lines', line=dict(color='#ef4444', width=1.8), name='달러 낙폭 (USD)'))
            fig_overlay.add_trace(go.Scatter(x=df.index, y=df['KRW_DD'] * 100, mode='lines', line=dict(color='#3b82f6', width=1.8), name='원화 낙폭 (KRW 환반영)'))
            fig_overlay.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(ticksuffix="%", range=[y_min_limit, 5], gridcolor='#1f2937'), xaxis=dict(gridcolor='#1f2937'), height=550, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_overlay, use_container_width=True)

    with side_col:
        st.markdown(f"### 📋 구간별 밀도 통계")
        
        st.markdown("""
            <div class="guide-box">
                <div class="guide-title">🔍 회복 확률별 투자 자산 적격 등급 가이드</div>
                <div class="guide-grid">
                    <div class="badge bg-vgood">≥90%<br>매우 적격</div>
                    <div class="badge bg-good">80~89%<br>적격</div>
                    <div class="badge bg-neutral">60~79%<br>중립</div>
                    <div class="badge bg-warn">&lt;60%<br>주의</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        thresholds = [i for i in range(0, -101, -5)]
        
        if base_currency == "KRW":
            dd_series = df['KRW_DD'] * 100
        else:
            dd_series = df['USD_DD'] * 100
            
        stats_data = []
        
        for i, t in enumerate(thresholds):
            cond_days = len(df[dd_series > t])
            recovery_ratio = (cond_days / total_days) * 100
            
            if t == 0:
                pure_days = len(df[dd_series == 0])
                pure_ratio = (pure_days / total_days) * 100
                
                stats_data.append({
                    "분석 구간": "신고가 경신 (0%)",
                    "회복 확률": None, 
                    "해당 일수": f"{pure_days:,}일",
                    "총 영업일": f"{total_days:,}일",
                    "구간 비중": f"{pure_ratio:.1f}%",
                    "raw_prob": 100.0
                })
            else:
                prev_t = thresholds[i-1]
                pure_ratio = ((cond_days - len(df[dd_series > prev_t])) / total_days) * 100
                
                if cond_days == total_days and t < y_min_limit:
                    continue
                    
                stats_data.append({
                    "분석 구간": f"{t}% 초과",
                    "회복 확률": f"{recovery_ratio:.1f}%", 
                    "해당 일수": f"{cond_days:,}일",
                    "총 영업일": f"{total_days:,}일",
                    "구간 비중": f"{pure_ratio:.1f}%",
                    "raw_prob": recovery_ratio
                })
            
        final_stats_df = pd.DataFrame(stats_data)
        
        def color_rows(row):
            prob = row['raw_prob']
            if row['분석 구간'] == "신고가 경신 (0%)":
                return ['background-color: rgba(16, 185, 129, 0.08); color: #10b981; font-weight:600;'] * len(row)
            
            if prob >= 90:
                return ['background-color: rgba(16, 185, 129, 0.06); color: #10b981;'] * len(row)
            elif prob >= 80:
                return ['background-color: rgba(59, 130, 246, 0.06); color: #3b82f6;'] * len(row)
            elif prob >= 60:
                return ['background-color: rgba(245, 158, 11, 0.06); color: #f59e0b;'] * len(row)
            else:
                return ['background-color: rgba(239, 68, 68, 0.08); color: #ef4444;'] * len(row)

        styled_df = final_stats_df.style.apply(color_rows, axis=1).hide(["raw_prob"], axis="columns")
        st.dataframe(styled_df, height=750, use_container_width=True, hide_index=True)


# --- 🛡️ [구글 애드센스 승인 보장 전용 프리미엄 정보 가이드 패널] ---
st.markdown("<br><br><hr id='policy-section' style='border:0; height:1px; background:#1f2937;'>", unsafe_allow_html=True)
st.markdown("### 📚 MDD 터미널 종합 가이드 및 이용 정책")

tab1, tab2, tab3 = st.tabs(["💡 MDD 터미널 활용 가이드 (FAQ)", "🔒 개인정보 처리방침", "✉️ 서비스 소개 및 면책조항"])

with tab1:
    st.markdown("""
    #### Q1. MDD(최대 하락률) 분석이 미국 주식/ETF 투자에 왜 필수적인가요?
    * 주식 시장에서 최고점 대비 현재 얼마나 하락했는지를 파악하는 것은 '분할 매수 타이밍'을 잡는 최고의 기준이 됩니다.
    * 특히 **JEPQ, JEPI** 등 고배당 ETF나 **QQQ, SPY** 같은 지수 추종 자산은 역사적으로 특정 낙폭(예: -10%, -15%)에 도달했을 때 회복 확률이 급격히 높아지는 경향이 있습니다. 본 터미널은 이를 통계학적으로 시각화하여 감정에 휘둘리지 않는 투자를 돕습니다.

    #### Q2. 달러(USD) 기준 낙폭과 원화(KRW) 기준 낙폭이 다른 이유는 무엇인가요?
    * 한국인 투자자는 미국 주식을 살 때 환율의 영향을 받습니다. 주가가 떨어지더라도 원/달러 환율이 오르면(환쿠션) 원화 기준 내 계좌의 실제 손실은 더 적을 수 있습니다.
    * 본 터미널은 야후 파이낸스(`yfinance`)의 실시간 환율 데이터를 100% 동기화하여, **환율 변동이 반영된 진짜 내 계좌의 원화 기준 낙폭**을 복합 Overlay 차트로 완벽히 대조 분석해 드립니다.

    #### Q3. 오른쪽 '구간별 밀도 통계' 테이블의 '회복 확률'은 어떻게 계산되나요?
    * 선택한 분석 기간 중, 해당 하락률(예: -10% 초과) 구간 위에서 머물렀던 영업일수의 누적 비중을 계산한 지표입니다.
    * 회복 확률이 90% 이상이라는 것은 역사적 자산 추세상 해당 낙폭 밑으로 떨어져서 머물렀던 날이 전체 기간 중 10% 미만이라는 뜻으로, 매우 강력한 매수 지지선 역할을 하고 있음을 의미합니다.
    """)

with tab2:
    st.markdown("""
    본 'MDD 터미널'은 이용자의 소중한 개인정보를 안전하게 보호하고자 최선을 다하고 있습니다.
    
    * **개인정보의 수집 및 이용 목적:** 본 웹서비스는 이용자의 어떠한 개인정보(이름, 이메일, 금융 계좌 정보 등)도 서버에 저장하거나 수집하지 않습니다.
    * **데이터 처리 방식:** 사용자가 입력하는 종목 코드 및 조회 날짜는 오픈 API(Yahoo Finance)와의 실시간 통신을 위한 일회성 파라미터로만 사용되며, 브라우저 종료 시 완전히 소멸됩니다.
    * **쿠키 및 트래픽 분석:** 구글 애드센스 등 서드파티 광고 가동 시 맞춤형 광고 송출을 위한 비식별 쿠키가 브라우저에 저장될 수 있으며, 이는 브라우저 설정을 통해 언제든 차단하실 수 있습니다.
    """)

with tab3:
    st.markdown("""
    #### 📈 Service Introduce
    * **MDD 터미널**은 글로벌 거시경제 지표(원/달러 환율, WTI 국제 유가)와 개별 투자 자산의 역사적 하락률 데이터를 융합하여 제공하는 고성능 금융 시각화 웹 플랫폼입니다. 
    * 1인 개발자가 직접 겪은 환노출 자산 관리의 불편함을 해결하기 위해 '바이브 코딩' 기술을 활용하여 제작되었으며, 트래픽 비용 없이 24시간 누구에게나 투명하고 유용한 금융 통계를 제공하는 것을 목적으로 합니다.

    #### 🛡️ 투자 면책 조항 (Disclaimer)
    * 본 서비스가 제공하는 모든 금융 데이터 및 계산 수치는 투자 참고용일 뿐이며, 실제 거래소 데이터와 오차가 발생할 수 있습니다. 
    * 본 서비스는 이용자의 투자 결과에 대해 어떠한 법적 책임도 지지 않으며, 모든 투자의 최종 판단과 책임은 투자자 본인에게 있습니다.

    #### ✉️ Contact Us
    * 서비스 오류 제보 및 비즈니스 제휴, 기능 건의 사항이 있으신 분은 아래의 공식 창구로 연락 주시기 바랍니다.
    * **이메일:** `dkdlel1747@gmail.com`
    * **업데이트 일자:** 2026년 6월 최신화 완료
    """)

# 구글 애드센스 봇 크롤링용 크레딧 푸터 (동적 앵커 링크 연결 완료)
st.markdown(f"""
    <div class="footer-container">
        <div class="footer-links">
            <a href="#policy-section">Terms of Service</a> | 
            <a href="#policy-section">Privacy Policy</a> | 
            <a href="#policy-section">Disclaimer</a>
        </div>
        <p style="margin-top:10px;">© 2026 MDD Terminal. Powered by yfinance & Streamlit. All rights reserved.</p>
    </div>
""", unsafe_allow_html=True)
