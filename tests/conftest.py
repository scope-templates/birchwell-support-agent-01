import pytest

from billing import ledger


@pytest.fixture(autouse=True)
def seeded_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("BIRCHWELL_DB", str(tmp_path / "birchwell.sqlite"))
    monkeypatch.delenv("BIRCHWELL_MODEL", raising=False)
    with ledger.connect() as conn:
        ledger.seed(conn)
