from billing import ledger, metering


def record(conn, meter_id, subject, quantity, occurred_at):
    conn.execute(
        "INSERT INTO usage_events (customer_id, meter_id, subject, quantity, occurred_at, idempotency_key)"
        " VALUES ('cus_03', ?, ?, ?, ?, ?)",
        (meter_id, subject, quantity, occurred_at, f"{meter_id}-{subject}-{occurred_at}"),
    )


def november_lines():
    with ledger.connect() as conn:
        record(conn, "mtr_api_calls", "proj_main", 100, "2026-11-02T10:00:00Z")
        record(conn, "mtr_api_calls", "proj_main", 250, "2026-11-14T10:00:00Z")
        record(conn, "mtr_api_calls", "proj_main", 40, "2026-11-30T23:59:00Z")
        record(conn, "mtr_storage", "bucket_primary", 12, "2026-11-03T08:00:00Z")
        record(conn, "mtr_storage", "bucket_primary", 30, "2026-11-17T08:00:00Z")
        record(conn, "mtr_storage", "bucket_primary", 18, "2026-11-28T08:00:00Z")
        record(conn, "mtr_storage", "bucket_primary", 99, "2026-12-01T00:00:00Z")
        record(conn, "mtr_seats", "usr_hal", 1, "2026-11-04T09:00:00Z")
        record(conn, "mtr_seats", "usr_ines", 1, "2026-11-05T09:00:00Z")
        record(conn, "mtr_seats", "usr_hal", 1, "2026-11-20T09:00:00Z")
        return {line["meter_id"]: line for line in metering.compute_lines(conn, "cus_03", "2026-11")}


def test_sum_meter_adds_every_quantity_in_the_period():
    assert november_lines()["mtr_api_calls"] == {"meter_id": "mtr_api_calls", "quantity": 390, "amount_minor": 390}


def test_max_meter_takes_the_period_peak_and_ignores_the_next_period():
    assert november_lines()["mtr_storage"] == {"meter_id": "mtr_storage", "quantity": 30, "amount_minor": 1200}


def test_unique_count_meter_counts_distinct_subjects():
    assert november_lines()["mtr_seats"] == {"meter_id": "mtr_seats", "quantity": 2, "amount_minor": 500}


def test_meters_without_events_get_no_line():
    assert sorted(november_lines()) == ["mtr_api_calls", "mtr_seats", "mtr_storage"]


def test_other_customers_events_are_not_counted():
    with ledger.connect() as conn:
        assert metering.compute_lines(conn, "cus_03", "2026-09") == []


def test_computing_twice_over_the_same_events_gives_the_same_lines():
    with ledger.connect() as conn:
        first = metering.compute_lines(conn, "cus_01", "2026-09")
        second = metering.compute_lines(conn, "cus_01", "2026-09")
        stored = ledger.get_invoice(conn, "inv_1001")["lines"]
    assert first == second == stored
