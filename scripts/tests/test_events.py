import datetime, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.lib.events import third_friday, is_quadruple_witching, upcoming_known


def test_third_friday_june_2026():
    assert third_friday(2026, 6) == datetime.date(2026, 6, 19)


def test_quadruple_witching():
    assert is_quadruple_witching(datetime.date(2026, 6, 19))
    assert not is_quadruple_witching(datetime.date(2026, 6, 18))
    assert not is_quadruple_witching(datetime.date(2026, 5, 15))  # 5月非四巫月


def test_upcoming_known():
    out = upcoming_known(datetime.date(2026, 6, 15), 7)
    assert any(e["name"].startswith("四巫日") for e in out)
