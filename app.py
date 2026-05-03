import json
import os
import stripe
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analyzer import analyze_dataframe, detect_columns
from insights import generate_insights
from report import render_report, render_excel_report
from storage import load_usage, save_usage, is_user_paid

st.set_page_config(
    page_title="BizView — AI-анализ продаж",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

USAGE_FILE = "usage_log.json"
FREE_LIMIT = 3

PAYWALL_MESSAGE = """
🚀 Salytic Pro

Получите:
- Неограниченные анализы
- Расширенные AI инсайты
- Приоритетную поддержку

Свяжитесь с автором для доступа.
"""

def get_user_id():
    session_id = st.session_state.get("session_id")

    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        st.session_state["session_id"] = session_id

    return session_id


def get_user_usage(user_id):
    data = load_usage()
    return data.get(user_id, {"count": 0})


def increment_usage(user_id):
    data = load_usage()

    if user_id not in data:
        data[user_id] = {
            "count": 0,
            "total_runs": 0,
            "last_used": None,
            "is_paid": False
        }

    data[user_id]["count"] += 1
    data[user_id]["total_runs"] = data[user_id].get("total_runs", 0) + 1
    data[user_id]["last_used"] = datetime.now().isoformat()

    save_usage(data)


def is_user_paid(user_id):
    data = load_usage()
    return data.get(user_id, {}).get("is_paid", False)


def get_usage_stats():
    data = load_usage()

    return {
        "users": len(data),
        "total_runs": sum(u.get("total_runs", 0) for u in data.values()),
        "active_today": len([
            u for u in data.values()
            if u.get("last_used") and
            (datetime.fromisoformat(u["last_used"]).date() == datetime.now().date())
        ])
    }


def set_user_paid(user_id: str):
    data = load_usage()

    if user_id not in data:
        data[user_id] = {}

    data[user_id]["is_paid"] = True
    save_usage(data)


# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Unbounded:wght@400;600;800&family=Inter:wght@300;400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #0a0a0f;
    color: #e8e8f0;
    font-family: 'Inter', sans-serif;
}

[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse 80% 60% at 50% -10%, #1a1040 0%, #0a0a0f 60%);
    min-height: 100vh;
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #0d0d15; border-right: 1px solid #1e1e30; }

.hero {
    text-align: center;
    padding: 60px 20px 40px;
}
.hero-badge {
    display: inline-block;
    background: linear-gradient(135deg, #7c3aed20, #06b6d420);
    border: 1px solid #7c3aed50;
    border-radius: 100px;
    padding: 6px 18px;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #a78bfa;
    margin-bottom: 24px;
}
.hero h1 {
    font-family: 'Unbounded', sans-serif;
    font-size: clamp(2rem, 5vw, 3.5rem);
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(135deg, #ffffff 0%, #a78bfa 50%, #06b6d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 16px;
}
.hero p {
    font-size: 1.1rem;
    color: #8888aa;
    max-width: 520px;
    margin: 0 auto 40px;
    line-height: 1.7;
    font-weight: 300;
}

.upload-zone {
    background: linear-gradient(135deg, #12121e, #1a1a2e);
    border: 2px dashed #2e2e4e;
    border-radius: 20px;
    padding: 40px;
    text-align: center;
    transition: border-color 0.3s;
    max-width: 640px;
    margin: 0 auto;
}
.upload-zone:hover { border-color: #7c3aed60; }

.stat-card {
    background: linear-gradient(135deg, #12121e, #16162a);
    border: 1px solid #1e1e35;
    border-radius: 16px;
    padding: 24px;
    position: relative;
    overflow: hidden;
}
.stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #7c3aed, #06b6d4);
}
.stat-label {
    font-size: 11px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #6666aa;
    margin-bottom: 8px;
    font-weight: 500;
}
.stat-value {
    font-family: 'Unbounded', sans-serif;
    font-size: 1.8rem;
    font-weight: 600;
    color: #ffffff;
    line-height: 1;
    margin-bottom: 4px;
}
.stat-sub {
    font-size: 0.8rem;
    color: #5555aa;
}

.section-title {
    font-family: 'Unbounded', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: #e8e8f0;
    margin: 32px 0 16px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #2e2e4e, transparent);
}

.insight-card {
    background: #0f0f1e;
    border: 1px solid #1e1e35;
    border-left: 3px solid #7c3aed;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    line-height: 1.7;
    color: #c8c8e0;
    font-size: 0.95rem;
}

.tag-good {
    display: inline-block;
    background: #0d2e1a;
    color: #4ade80;
    border: 1px solid #166534;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 500;
}
.tag-bad {
    display: inline-block;
    background: #2e0d0d;
    color: #f87171;
    border: 1px solid #991b1b;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 500;
}

.stFileUploader > div { background: transparent !important; }
[data-testid="stFileUploaderDropzone"] {
    background: #0f0f1e !important;
    border: 2px dashed #2e2e4e !important;
    border-radius: 16px !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #7c3aed !important;
}

div[data-testid="stSelectbox"] > div > div {
    background: #12121e !important;
    border: 1px solid #2e2e4e !important;
    border-radius: 10px !important;
    color: #e8e8f0 !important;
}

.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 32px !important;
    font-family: 'Unbounded', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    transition: all 0.3s !important;
    width: 100%;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #6d28d9, #4c1d95) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px #7c3aed40 !important;
}

.stSpinner > div { border-top-color: #7c3aed !important; }

.plotly-chart { border-radius: 16px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── HERO ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-badge">🤖 AI-аналитика для бизнеса</div>
    <h1>Анализ продаж<br>для вашего бизнеса</h1>
    <p>Загрузить CSV с данными — получи готовый анализ и рекомендации</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; padding: 20px; color: #6666aa; font-size: 0.85rem;">
    🚀 Powered by BizView
</div>
""", unsafe_allow_html=True)

user_id = get_user_id()
usage = get_user_usage(user_id)
remaining = max(FREE_LIMIT - usage["count"], 0)

# PAYWALL
if usage["count"] >= FREE_LIMIT and not is_user_paid(user_id):
    st.warning("❌ Лимит исчерпан. Оформи подписку для продолжения.")

    if st.button("💳 Оплатить доступ"):
        from payments import create_checkout_session

        url = create_checkout_session(user_id)
        st.markdown(f"[Перейти к оплате]({url})", unsafe_allow_html=True)

    st.stop()

# ── SIDEBAR UI ─────────────────────────────
st.sidebar.markdown(f"""
### 📊 Usage
**{usage['count']} / {FREE_LIMIT}**

Осталось запусков: **{remaining}**
""")

if st.sidebar.checkbox("Admin stats"):
    stats = get_usage_stats()

    st.sidebar.markdown(f"""
### 📊 System stats
Users: **{stats['users']}**  
Total runs: **{stats['total_runs']}**  
Active today: **{stats['active_today']}
""")

# 🔓 DEV: simulate payment (ВОТ СЮДА)
if st.sidebar.button("🔓 Simulate payment (dev)"):
    data = load_usage()
    data[user_id]["is_paid"] = True
    save_usage(data)
    st.sidebar.success("User marked as paid")

# ── BLOCK ACCESS  ─────────
is_paid = usage.get("is_paid", False)

if not is_paid and usage["count"] >= FREE_LIMIT:
    st.error("❌ Бесплатный лимит исчерпан. Перейдите на Pro-версию для неограниченного доступа.")

    st.markdown(PAYWALL_MESSAGE)
    st.stop()

# ── UPLOAD ────────────────────────────────────────────────────────────────────
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    uploaded_file = st.file_uploader(
        "Загрузи CSV-файл с продажами",
        type=["csv"],
        help="Поддерживаются файлы с колонками: дата, товар, количество, сумма (названия могут быть любыми)"
    )

if uploaded_file is None:
    st.markdown("""
    <div style="text-align:center; padding: 40px 0; color: #3a3a5c; font-size: 0.85rem;">
        Пример формата CSV: дата, название товара, количество, сумма продажи
    </div>
    """, unsafe_allow_html=True)

    # Кнопка для демо
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button("▶  Попробовать на демо-данных"):
            st.session_state["use_demo"] = True
            st.rerun()

# ── DEMO DATA ─────────────────────────────────────────────────────────────────
def get_demo_df():
    import numpy as np
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", "2024-06-30", freq="D")
    products = ["Кофе", "Чай", "Капучино", "Эспрессо", "Латте", "Круассан", "Сэндвич", "Торт", "Маффин", "Сок"]
    rows = []
    for date in dates:
        n = np.random.randint(15, 40)
        for _ in range(n):
            product = np.random.choice(products, p=[0.2,0.08,0.18,0.12,0.15,0.09,0.06,0.03,0.05,0.04])
            price_map = {"Кофе":150,"Чай":100,"Капучино":220,"Эспрессо":180,"Латте":240,
                         "Круассан":120,"Сэндвич":200,"Торт":350,"Маффин":130,"Сок":160}
            qty = np.random.randint(1, 4)
            rows.append({
                "дата": date.strftime("%Y-%m-%d"),
                "товар": product,
                "количество": qty,
                "сумма": price_map[product] * qty
            })
    return pd.DataFrame(rows)

def _read_csv_smart(file) -> pd.DataFrame | None:
    """Пробует разные кодировки и разделители, возвращает корректный DataFrame."""
    encodings = ["utf-8", "cp1251", "latin-1"]
    separators = [",", ";", "	", "|"]

    for enc in encodings:
        for sep in separators:
            try:
                file.seek(0)
                df = pd.read_csv(file, encoding=enc, sep=sep)
                # Считаем файл прочитанным правильно если получили >1 колонки
                if df.shape[1] > 1:
                    return df
            except:
                continue

    # Последняя попытка — python engine с автоопределением
    try:
        file.seek(0)
        df = pd.read_csv(file, encoding="utf-8", sep=None, engine="python")
        if df.shape[1] > 1:
            return df
    except:
        pass

    st.error("Не удалось прочитать файл. Проверь формат: CSV с разделителями , ; или Tab.")
    return None

# ── MAIN LOGIC ────────────────────────────────────────────────────────────────
df_raw = None

if uploaded_file is not None:
    df_raw = _read_csv_smart(uploaded_file)

elif st.session_state.get("use_demo"):
    df_raw = get_demo_df()
    st.info("📁 Используются демо-данные кофейни за 6 месяцев")

if df_raw is not None:
    st.markdown("---")

    # ── COLUMN MAPPING ────────────────────────────────────────────────────────
    cols = detect_columns(df_raw)

    with st.expander("⚙️ Настройка колонок (нажми если автоопределение неверно)", expanded=not all(cols.values())):
        c1, c2, c3, c4 = st.columns(4)
        all_cols = ["(не указано)"] + list(df_raw.columns)

        def col_idx(val):
            return all_cols.index(val) if val in all_cols else 0

        with c1:
            cols["date"] = st.selectbox("📅 Дата", all_cols, index=col_idx(cols.get("date", "")))
        with c2:
            cols["product"] = st.selectbox("📦 Товар/категория", all_cols, index=col_idx(cols.get("product", "")))
        with c3:
            cols["quantity"] = st.selectbox("🔢 Количество", all_cols, index=col_idx(cols.get("quantity", "")))
        with c4:
            cols["revenue"] = st.selectbox("💰 Сумма", all_cols, index=col_idx(cols.get("revenue", "")))

    # Фильтруем None
    cols = {k: v for k, v in cols.items() if v and v != "(не указано)"}

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn2:
        run_analysis = st.button("🔍  Запустить AI-анализ")

    if run_analysis or st.session_state.get("analysis_done"):
        if run_analysis:
            increment_usage(user_id)
            usage = get_user_usage(user_id)

            st.success(
                f"Анализ завершён. Использований: {usage['count']}/{FREE_LIMIT}"
            )

            st.session_state["analysis_done"] = True

        with st.spinner("Анализирую данные..."):
            stats = analyze_dataframe(df_raw, cols)

        # ── KPI CARDS ─────────────────────────────────────────────────────────
        st.markdown('<div class="section-title">Ключевые метрики</div>', unsafe_allow_html=True)

        k1, k2, k3, k4 = st.columns(4)
        cards = [
            (k1, "Выручка", stats["total_revenue"], "за весь период"),
            (k2, "Продаж", stats["total_orders"], "транзакций"),
            (k3, "Товаров", stats["unique_products"], "уникальных позиций"),
            (k4, "Средний чек", stats["avg_order"], "руб / транзакция"),
        ]
        for col, label, value, sub in cards:
            with col:
                if isinstance(value, float):
                    disp = f"{value:,.0f} ₽" if "₽" not in sub else f"{value:,.0f}"
                else:
                    disp = f"{value:,}"
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-label">{label}</div>
                    <div class="stat-value">{disp}</div>
                    <div class="stat-sub">{sub}</div>
                </div>""", unsafe_allow_html=True)

        # ── CHARTS ────────────────────────────────────────────────────────────
        if stats.get("revenue_over_time") is not None:
            st.markdown('<div class="section-title">Динамика выручки</div>', unsafe_allow_html=True)
            fig = px.area(
                stats["revenue_over_time"], x="date", y="revenue",
                color_discrete_sequence=["#7c3aed"]
            )
            fig.update_layout(
                paper_bgcolor="#0f0f1e", plot_bgcolor="#0f0f1e",
                font=dict(color="#8888aa", family="Inter"),
                xaxis=dict(gridcolor="#1e1e35", title=""),
                yaxis=dict(gridcolor="#1e1e35", title="Выручка, ₽"),
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False
            )
            fig.update_traces(fillcolor="rgba(124,58,237,0.12)", line_width=2)
            st.plotly_chart(fig, use_container_width=True)

        if stats.get("top_products") is not None:
            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown('<div class="section-title">Топ товаров</div>', unsafe_allow_html=True)
                top = stats["top_products"].head(8)
                fig2 = px.bar(
                    top, x="revenue", y="product", orientation="h",
                    color_discrete_sequence=["#7c3aed"]
                )
                fig2.update_layout(
                    paper_bgcolor="#0f0f1e", plot_bgcolor="#0f0f1e",
                    font=dict(color="#8888aa", family="Inter"),
                    xaxis=dict(gridcolor="#1e1e35", title="Выручка, ₽"),
                    yaxis=dict(gridcolor="#1e1e35", title="", autorange="reversed"),
                    margin=dict(l=0, r=0, t=10, b=0),
                    showlegend=False
                )
                st.plotly_chart(fig2, use_container_width=True)

            with col_right:
                st.markdown('<div class="section-title">Аутсайдеры</div>', unsafe_allow_html=True)
                bottom = stats["top_products"].tail(8).sort_values("revenue")
                fig3 = px.bar(
                    bottom, x="revenue", y="product", orientation="h",
                    color_discrete_sequence=["#ef4444"]
                )
                fig3.update_layout(
                    paper_bgcolor="#0f0f1e", plot_bgcolor="#0f0f1e",
                    font=dict(color="#8888aa", family="Inter"),
                    xaxis=dict(gridcolor="#1e1e35", title="Выручка, ₽"),
                    yaxis=dict(gridcolor="#1e1e35", title="", autorange="reversed"),
                    margin=dict(l=0, r=0, t=10, b=0),
                    showlegend=False
                )
                st.plotly_chart(fig3, use_container_width=True)

        if stats.get("weekday_revenue") is not None:
            st.markdown('<div class="section-title">Продажи по дням недели</div>', unsafe_allow_html=True)
            fig4 = px.bar(
                stats["weekday_revenue"], x="weekday", y="revenue",
                color_discrete_sequence=["#06b6d4"]
            )
            fig4.update_layout(
                paper_bgcolor="#0f0f1e", plot_bgcolor="#0f0f1e",
                font=dict(color="#8888aa", family="Inter"),
                xaxis=dict(gridcolor="#1e1e35", title=""),
                yaxis=dict(gridcolor="#1e1e35", title="Выручка, ₽"),
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False
            )
            st.plotly_chart(fig4, use_container_width=True)

        # ── AI INSIGHTS ───────────────────────────────────────────────────────
        st.markdown('<div class="section-title">🤖 AI-рекомендации</div>', unsafe_allow_html=True)

        if "insights" not in st.session_state or run_analysis:
            with st.spinner("Генерирую рекомендации..."):
                insights = generate_insights(stats)
                st.session_state["insights"] = insights
        else:
            insights = st.session_state["insights"]

        if insights:
            order = {"positive": 0, "neutral": 1, "warning": 2}
            sorted_insights = sorted(insights, key=lambda x: order.get(x.get("type"), 1))
            for ins in sorted_insights:
                icon = "🔴" if ins.get("type") == "warning" else "🟢" if ins.get("type") == "positive" else "💡"
                st.markdown(f"""
                <div class="insight-card">
                    {icon} <strong>{ins.get("title","")}</strong><br>
                    {ins.get("text","")}
                </div>""", unsafe_allow_html=True)

        # ── EXPORT ────────────────────────────────────────────────────────────
        st.markdown('<div class="section-title">📥 Экспорт отчёта</div>', unsafe_allow_html=True)
        col_e1, col_e2, col_e3, col_e4 = st.columns([1,1,1,1])
        with col_e2:
            html_report = render_report(stats, insights)
            st.download_button(
                label="⬇  Скачать HTML-отчёт",
                data=html_report,
                file_name="salytic_report.html",
                mime="text/html"
            )
        with col_e3:
            excel_report = render_excel_report(stats, insights)
            st.download_button(
                label="⬇  Скачать Excel-отчёт",
                data=excel_report,
                file_name="salytic_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
