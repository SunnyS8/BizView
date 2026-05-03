import pandas as pd
import numpy as np
import re


DATE_KEYWORDS = ["дата", "date", "день", "day", "время", "time", "period", "период"]
PRODUCT_KEYWORDS = ["товар", "productline", "product", "наименование", "название", "item", "name", "категория", "category", "позиция", "линейка"]
QTY_KEYWORDS = ["количество", "quantityordered", "qty", "quantity", "кол", "шт", "count", "объем", "объём"]
REVENUE_KEYWORDS = ["сумма", "sales", "revenue", "выручка", "доход", "продажа", "amount", "price", "цена", "стоимость", "итого", "total"]


def detect_columns(df: pd.DataFrame) -> dict:
    """Пытается автоматически определить роли колонок."""
    cols = {"date": None, "product": None, "quantity": None, "revenue": None}
    col_names_lower = {c: c.lower() for c in df.columns}

    for col, col_lower in col_names_lower.items():
        if not cols["date"] and any(k in col_lower for k in DATE_KEYWORDS):
            cols["date"] = col
        elif not cols["product"] and any(k in col_lower for k in PRODUCT_KEYWORDS):
            cols["product"] = col
        elif not cols["quantity"] and any(k in col_lower for k in QTY_KEYWORDS):
            cols["quantity"] = col
        elif not cols["revenue"] and any(k in col_lower for k in REVENUE_KEYWORDS):
            cols["revenue"] = col

    # Если не нашли по имени — пробуем по типу данных (только если реально нужно)
    import warnings
    for col in df.columns:
        if not cols["date"] and df[col].dtype == object:
            sample = df[col].dropna().head(5)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
                    if parsed.notna().sum() >= 3:
                        cols["date"] = col
                except:
                    pass
        if not cols["revenue"] and df[col].dtype in [np.float64, np.int64]:
            if df[col].mean() > 50:
                cols["revenue"] = col
        if not cols["quantity"] and df[col].dtype in [np.float64, np.int64]:
            if df[col].mean() <= 50:
                cols["quantity"] = col

    return cols


def analyze_dataframe(df: pd.DataFrame, cols: dict) -> dict:
    """Основной анализ. Возвращает словарь со всеми метриками."""
    df = df.copy()
    stats = {}

    # ── Дата ──────────────────────────────────────────────────────────────────
    if cols.get("date"):
        df["_date"] = pd.to_datetime(df[cols["date"]], errors="coerce")
        df = df.dropna(subset=["_date"])
        stats["date_range"] = (df["_date"].min(), df["_date"].max())
    else:
        df["_date"] = pd.NaT

    # ── Выручка ───────────────────────────────────────────────────────────────
    if cols.get("revenue"):
        df["_revenue"] = pd.to_numeric(df[cols["revenue"]], errors="coerce").fillna(0)
    else:
        df["_revenue"] = 0

    # ── Количество ────────────────────────────────────────────────────────────
    if cols.get("quantity"):
        df["_qty"] = pd.to_numeric(df[cols["quantity"]], errors="coerce").fillna(1)
    else:
        df["_qty"] = 1

    # ── Товар ─────────────────────────────────────────────────────────────────
    if cols.get("product"):
        df["_product"] = df[cols["product"]].astype(str)
    else:
        df["_product"] = "Без категории"

    # ── KPI ───────────────────────────────────────────────────────────────────
    stats["total_revenue"] = float(df["_revenue"].sum())
    stats["total_orders"] = int(len(df))
    stats["unique_products"] = int(df["_product"].nunique())
    stats["avg_order"] = float(df["_revenue"].mean()) if len(df) > 0 else 0

    # ── Динамика выручки ──────────────────────────────────────────────────────
    if not df["_date"].isna().all():
        freq = "W" if (df["_date"].max() - df["_date"].min()).days > 60 else "D"
        rev_time = (
            df.groupby(pd.Grouper(key="_date", freq=freq))["_revenue"]
            .sum()
            .reset_index()
        )
        rev_time.columns = ["date", "revenue"]
        stats["revenue_over_time"] = rev_time

        # Тренд (рост/падение)
        if len(rev_time) >= 4:
            half = len(rev_time) // 2
            first_half = rev_time["revenue"].iloc[:half].mean()
            second_half = rev_time["revenue"].iloc[half:].mean()
            stats["trend_pct"] = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
        else:
            stats["trend_pct"] = 0

        # По дням недели
        df["_weekday"] = df["_date"].dt.day_name()
        weekday_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        weekday_ru = {"Monday":"Пн","Tuesday":"Вт","Wednesday":"Ср","Thursday":"Чт",
                      "Friday":"Пт","Saturday":"Сб","Sunday":"Вс"}
        wd = df.groupby("_weekday")["_revenue"].sum().reindex(weekday_order).fillna(0).reset_index()
        wd.columns = ["weekday", "revenue"]
        wd["weekday"] = wd["weekday"].map(weekday_ru)
        stats["weekday_revenue"] = wd
        stats["best_weekday"] = wd.loc[wd["revenue"].idxmax(), "weekday"]
        stats["worst_weekday"] = wd.loc[wd["revenue"].idxmin(), "weekday"]
    else:
        stats["revenue_over_time"] = None
        stats["weekday_revenue"] = None
        stats["trend_pct"] = 0
        stats["best_weekday"] = None
        stats["worst_weekday"] = None

    # ── Топ товаров ───────────────────────────────────────────────────────────
    product_stats = (
        df.groupby("_product")
        .agg(revenue=("_revenue", "sum"), qty=("_qty", "sum"), orders=("_revenue", "count"))
        .reset_index()
        .rename(columns={"_product": "product"})
        .sort_values("revenue", ascending=False)
    )
    stats["top_products"] = product_stats

    if len(product_stats) > 0:
        stats["best_product"] = product_stats.iloc[0]["product"]
        stats["worst_product"] = product_stats.iloc[-1]["product"]
        stats["best_product_revenue"] = float(product_stats.iloc[0]["revenue"])
        stats["worst_product_revenue"] = float(product_stats.iloc[-1]["revenue"])

        # ABC-анализ
        product_stats_sorted = product_stats.sort_values("revenue", ascending=False).copy()
        product_stats_sorted["cumulative_pct"] = (
            product_stats_sorted["revenue"].cumsum() / product_stats_sorted["revenue"].sum() * 100
        )
        stats["abc_a"] = list(product_stats_sorted[product_stats_sorted["cumulative_pct"] <= 80]["product"])
        stats["abc_c"] = list(product_stats_sorted[product_stats_sorted["cumulative_pct"] > 95]["product"])

    # ── Аномалии ──────────────────────────────────────────────────────────────
    if not df["_date"].isna().all() and stats.get("revenue_over_time") is not None:
        daily = df.groupby("_date")["_revenue"].sum()
        mean_daily = daily.mean()
        std_daily = daily.std()
        anomalies = daily[daily > mean_daily + 2 * std_daily]
        stats["anomaly_days"] = len(anomalies)
        stats["mean_daily_revenue"] = float(mean_daily)
    else:
        stats["anomaly_days"] = 0
        stats["mean_daily_revenue"] = stats["avg_order"]

    return stats