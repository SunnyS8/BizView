import json


def generate_insights(stats: dict) -> list[dict]:
    """
    Генерирует список инсайтов. Использует только локальные инсайты.
    Возвращает список dict: [{"title": ..., "text": ..., "type": "positive"|"warning"|"neutral"}]
    """
    return _fallback_insights(stats)


def _fallback_insights(stats: dict) -> list[dict]:
    """Базовые инсайты без внешнего API."""
    insights = []

    # Тренд
    trend = stats.get("trend_pct", 0)
    if trend > 10:
        insights.append({
            "title": "Выручка растёт",
            "text": f"Вторая половина периода принесла на {trend:.0f}% больше чем первая. Хороший сигнал — продолжай в том же духе и анализируй что изменилось.",
            "type": "positive"
        })
    elif trend < -10:
        insights.append({
            "title": "Выручка падает",
            "text": f"Вторая половина периода принесла на {abs(trend):.0f}% меньше чем первая. Стоит разобраться в причинах — сезонность, ассортимент или внешние факторы.",
            "type": "warning"
        })

    # Лучший/худший товар
    if stats.get("best_product"):
        insights.append({
            "title": f"Локомотив продаж — {stats['best_product']}",
            "text": f"Этот товар приносит наибольшую выручку. Убедись что он всегда в наличии, рассмотри расширение линейки на его основе.",
            "type": "positive"
        })

    if stats.get("worst_product") and stats.get("worst_product_revenue", 0) > 0:
        insights.append({
            "title": f"Аутсайдер — {stats['worst_product']}",
            "text": f"Этот товар приносит минимальную выручку ({stats['worst_product_revenue']:,.0f} руб). Оцени: стоит ли держать его в ассортименте или лучше заменить?",
            "type": "warning"
        })

    # ABC
    if stats.get("abc_c"):
        insights.append({
            "title": "Кандидаты на вывод из ассортимента",
            "text": f"Товары {', '.join(stats['abc_c'][:3])} вносят минимальный вклад в выручку. Они занимают место и отвлекают внимание. Рассмотри их замену.",
            "type": "warning"
        })

    # Дни недели
    if stats.get("best_weekday") and stats.get("worst_weekday"):
        insights.append({
            "title": f"Лучший день — {stats['best_weekday']}, худший — {stats['worst_weekday']}",
            "text": f"Планируй акции и запасы под пиковые дни. В {stats['worst_weekday']} попробуй специальные предложения чтобы поднять выручку.",
            "type": "neutral"
        })

    if not insights:
        insights.append({
            "title": "Анализ завершён",
            "text": f"Обработано {stats.get('total_orders', 0)} транзакций.",
            "type": "neutral"
        })

    return insights
