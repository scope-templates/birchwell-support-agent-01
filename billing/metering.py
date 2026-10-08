def compute_lines(conn, customer_id, period):
    rows = conn.execute(
        """
        SELECT m.id, m.aggregation, m.unit_price_minor,
               sum(e.quantity) AS total, max(e.quantity) AS peak, count(DISTINCT e.subject) AS subjects
        FROM usage_events e JOIN meters m ON m.id = e.meter_id
        WHERE e.customer_id = ? AND substr(e.occurred_at, 1, 7) = ?
        GROUP BY m.id
        ORDER BY m.id
        """,
        (customer_id, period),
    )
    lines = []
    for row in rows:
        quantity = {"sum": row["total"], "max": row["peak"], "unique_count": row["subjects"]}[row["aggregation"]]
        lines.append(
            {"meter_id": row["id"], "quantity": quantity, "amount_minor": quantity * row["unit_price_minor"]}
        )
    return lines
