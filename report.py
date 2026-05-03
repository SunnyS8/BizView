from datetime import datetime
import pandas as pd
import io


def render_excel_report(stats: dict, insights: list) -> bytes:
    """Генерирует Excel-отчёт с несколькими листами."""
    try:
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист 1: KPI
            kpi_data = {
                'Метрика': ['Общая выручка (₽)', 'Всего транзакций', 'Уникальных товаров', 'Средний чек (₽)',
                           'Тренд (%)', 'Лучший день', 'Худший день', 'Аномальных дней'],
                'Значение': [
                    stats.get('total_revenue', 0),
                    stats.get('total_orders', 0),
                    stats.get('unique_products', 0),
                    stats.get('avg_order', 0),
                    round(stats.get('trend_pct', 0), 2),
                    stats.get('best_weekday', '-'),
                    stats.get('worst_weekday', '-'),
                    stats.get('anomaly_days', 0)
                ]
            }
            pd.DataFrame(kpi_data).to_excel(writer, sheet_name='KPI', index=False)

            # Лист 2: Динамика выручки
            if stats.get('revenue_over_time') is not None:
                rev_df = stats['revenue_over_time'].copy()
                rev_df.columns = ['Дата', 'Выручка']
                rev_df.to_excel(writer, sheet_name='Динамика', index=False)

            # Лист 3: Товары
            if stats.get('top_products') is not None:
                prod_df = stats['top_products'].copy()
                prod_df.columns = ['Товар', 'Выручка', 'Количество', 'Транзакции']
                prod_df.to_excel(writer, sheet_name='Товары', index=False)

            # Лист 4: По дням недели
            if stats.get('weekday_revenue') is not None:
                wd_df = stats['weekday_revenue'].copy()
                wd_df.columns = ['День недели', 'Выручка']
                wd_df.to_excel(writer, sheet_name='По дням недели', index=False)

            # Лист 5: ABC-анализ
            abc_data = []
            if stats.get('abc_a'):
                for item in stats['abc_a']:
                    abc_data.append({'Товар': item, 'Группа': 'A'})
            if stats.get('abc_c'):
                for item in stats['abc_c']:
                    abc_data.append({'Товар': item, 'Группа': 'C'})
            if abc_data:
                pd.DataFrame(abc_data).to_excel(writer, sheet_name='ABC-анализ', index=False)

            # Лист 6: AI-рекомендации
            if insights:
                insight_df = pd.DataFrame(insights)
                if 'type' in insight_df.columns:
                    insight_df['type'] = insight_df['type'].replace({'positive': 'Позитивно', 'warning': 'Предупреждение', 'neutral': 'Нейтрально'})
                insight_df.to_excel(writer, sheet_name='AI-рекомендации', index=False)

        return output.getvalue()
    except Exception as e:
        print(f"Excel export error: {e}")
        return b""


def render_report(stats: dict, insights: list) -> str:
    """Генерирует красивый HTML-отчёт для скачивания."""

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # KPI карточки
    kpi_cards = f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Выручка</div>
            <div class="kpi-value">{stats.get('total_revenue', 0):,.0f} ₽</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Транзакций</div>
            <div class="kpi-value">{stats.get('total_orders', 0):,}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Товаров</div>
            <div class="kpi-value">{stats.get('unique_products', 0)}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Средний чек</div>
            <div class="kpi-value">{stats.get('avg_order', 0):,.0f} ₽</div>
        </div>
    </div>
    """

    # Топ товары
    top_products_html = ""
    if stats.get("top_products") is not None:
        top_df = stats["top_products"].head(10)
        max_rev = top_df["revenue"].max() if len(top_df) > 0 else 1
        rows = ""
        for i, (_, row) in enumerate(top_df.iterrows()):
            pct = row["revenue"] / max_rev * 100
            color = "#7c3aed" if i < 3 else "#374151"
            rows += f"""
            <tr>
                <td style="color:#9ca3af;width:30px">{i+1}</td>
                <td><strong>{row['product']}</strong></td>
                <td style="text-align:right">{row['revenue']:,.0f} ₽</td>
                <td style="width:120px">
                    <div style="background:#1f2937;border-radius:4px;height:6px;overflow:hidden">
                        <div style="background:{color};width:{pct:.0f}%;height:100%;border-radius:4px"></div>
                    </div>
                </td>
            </tr>"""
        top_products_html = f"""
        <div class="section">
            <h2>📦 Топ товаров по выручке</h2>
            <table class="data-table">
                <thead><tr><th>#</th><th>Товар</th><th>Выручка</th><th>Доля</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>"""

    # ABC анализ
    abc_html = ""
    if stats.get("abc_a") or stats.get("abc_c"):
        a_items = ", ".join(stats.get("abc_a", [])[:6]) or "—"
        c_items = ", ".join(stats.get("abc_c", [])[:6]) or "—"
        abc_html = f"""
        <div class="section">
            <h2>📊 ABC-анализ ассортимента</h2>
            <div class="abc-grid">
                <div class="abc-card abc-a">
                    <div class="abc-badge">A</div>
                    <div class="abc-label">80% выручки — держать в приоритете</div>
                    <div class="abc-items">{a_items}</div>
                </div>
                <div class="abc-card abc-c">
                    <div class="abc-badge">C</div>
                    <div class="abc-label">Хвост — кандидаты на вывод</div>
                    <div class="abc-items">{c_items}</div>
                </div>
            </div>
        </div>"""

    # Инсайты
    insights_html = ""
    if insights:
        items = ""
        for ins in insights:
            icon_map = {"positive": "✅", "warning": "⚠️", "neutral": "💡"}
            color_map = {"positive": "#166534", "warning": "#7f1d1d", "neutral": "#1e3a5f"}
            border_map = {"positive": "#4ade80", "warning": "#f87171", "neutral": "#60a5fa"}
            t = ins.get("type", "neutral")
            items += f"""
            <div style="background:{color_map[t]}22;border-left:3px solid {border_map[t]};
                        border-radius:8px;padding:16px 20px;margin-bottom:12px">
                <strong style="color:{border_map[t]}">{icon_map[t]} {ins.get('title','')}</strong>
                <p style="margin:8px 0 0;color:#d1d5db;line-height:1.6">{ins.get('text','')}</p>
            </div>"""
        insights_html = f"""
        <div class="section">
            <h2>🤖 AI-рекомендации</h2>
            {items}
        </div>"""

    trend_pct = stats.get("trend_pct", 0)
    trend_text = f"▲ +{trend_pct:.1f}%" if trend_pct > 0 else f"▼ {trend_pct:.1f}%"
    trend_color = "#4ade80" if trend_pct > 0 else "#f87171"

    date_range = ""
    if stats.get("date_range"):
        d1, d2 = stats["date_range"]
        date_range = f"{d1.strftime('%d.%m.%Y')} — {d2.strftime('%d.%m.%Y')}"

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BizView — Отчёт о продажах</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Unbounded:wght@400;700&family=Inter:wght@300;400;500&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0a0a0f; color: #e8e8f0; font-family: 'Inter', sans-serif; padding: 40px 20px; }}
  .container {{ max-width: 860px; margin: 0 auto; }}
  .header {{ text-align: center; padding: 40px 0 50px; }}
  .logo {{ font-family: 'Unbounded', sans-serif; font-size: 2rem; font-weight: 700;
         background: linear-gradient(135deg, #fff, #a78bfa, #06b6d4);
         -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
  .subtitle {{ color: #6666aa; margin-top: 8px; font-size: 0.9rem; }}
  .meta {{ color: #4444aa; font-size: 0.8rem; margin-top: 16px; }}
  .trend-badge {{ display: inline-block; color: {trend_color}; background: {trend_color}22;
                border: 1px solid {trend_color}44; border-radius: 100px; padding: 4px 12px;
                font-size: 0.8rem; font-weight: 500; margin-top: 12px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 30px 0; }}
  .kpi-card {{ background: #12121e; border: 1px solid #1e1e35; border-radius: 12px; padding: 20px;
               position: relative; overflow: hidden; }}
  .kpi-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
                       background: linear-gradient(90deg, #7c3aed, #06b6d4); }}
  .kpi-label {{ font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: #6666aa; margin-bottom: 8px; }}
  .kpi-value {{ font-family: 'Unbounded', sans-serif; font-size: 1.4rem; font-weight: 700; color: #fff; }}
  .section {{ background: #0f0f1e; border: 1px solid #1e1e35; border-radius: 16px; padding: 28px; margin: 20px 0; }}
  .section h2 {{ font-family: 'Unbounded', sans-serif; font-size: 0.9rem; font-weight: 600;
                 color: #e8e8f0; margin-bottom: 20px; }}
  .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  .data-table th {{ color: #6666aa; font-weight: 500; font-size: 0.75rem; text-transform: uppercase;
                    letter-spacing: 1px; padding: 8px 12px; border-bottom: 1px solid #1e1e35; text-align: left; }}
  .data-table td {{ padding: 10px 12px; border-bottom: 1px solid #111122; color: #c8c8e0; }}
  .abc-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .abc-card {{ border-radius: 12px; padding: 20px; }}
  .abc-a {{ background: #0d2e1a; border: 1px solid #166534; }}
  .abc-c {{ background: #2e0d0d; border: 1px solid #7f1d1d; }}
  .abc-badge {{ font-family: 'Unbounded', sans-serif; font-size: 1.5rem; font-weight: 700; margin-bottom: 8px; }}
  .abc-a .abc-badge {{ color: #4ade80; }}
  .abc-c .abc-badge {{ color: #f87171; }}
  .abc-label {{ font-size: 0.8rem; color: #9ca3af; margin-bottom: 10px; }}
  .abc-items {{ font-size: 0.85rem; color: #e8e8f0; line-height: 1.6; }}
  .footer {{ text-align: center; color: #333355; font-size: 0.75rem; padding: 40px 0 20px; }}
  @media (max-width: 600px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .abc-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">BizView</div>
    <div class="subtitle">AI-анализ продаж</div>
    <div class="meta">Отчёт сформирован: {now}{f" · Период: {date_range}" if date_range else ""}</div>
    {f'<div class="trend-badge">Тренд: {trend_text}</div>' if trend_pct != 0 else ""}
  </div>

  {kpi_cards}
  {top_products_html}
  {abc_html}
  {insights_html}

  <div class="footer">Сгенерировано BizView · bizview.app</div>
</div>
</body>
</html>"""

    return html
