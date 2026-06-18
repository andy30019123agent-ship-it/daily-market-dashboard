import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.lib.parsers import (  # noqa: E402
    roc_to_iso, parse_twse_index, parse_fmtqik, twse_top_gainers, parse_fred_csv,
)


def test_roc_to_iso():
    assert roc_to_iso("1150617") == "2026-06-17"


def test_parse_twse_index():
    rows = [
        {"指數": "寶島股價指數", "收盤指數": "51,189.67", "漲跌": "+", "漲跌點數": "97.19", "漲跌百分比": "0.19"},
        {"指數": "發行量加權股價指數", "收盤指數": "22,486.31", "漲跌": "+", "漲跌點數": "182.40", "漲跌百分比": "0.82"},
    ]
    out = parse_twse_index(rows)
    assert out["close"] == 22486.31
    assert out["change_pct"] == 0.82


def test_parse_twse_index_negative():
    rows = [{"指數": "發行量加權股價指數", "收盤指數": "100", "漲跌": "-", "漲跌點數": "5", "漲跌百分比": "5"}]
    out = parse_twse_index(rows)
    assert out["change_pct"] == -5
    assert out["change"] == -5


def test_parse_fmtqik():
    rows = [
        {"Date": "1150616", "TradeValue": "1696398095158", "TAIEX": "45557.31", "Change": "219.40"},
        {"Date": "1150617", "TradeValue": "412000000000", "TAIEX": "22486.31", "Change": "182.40"},
    ]
    out = parse_fmtqik(rows)
    assert out["taiex"] == 22486.31
    assert out["trade_value_yi"] == 4120
    assert out["spark"][-1] == 22486.31


def test_twse_top_gainers_filters_and_sorts():
    rows = [
        {"Code": "2330", "Name": "台積電", "ClosingPrice": "1085", "Change": "22", "TradeValue": "90000000000"},
        {"Code": "3231", "Name": "緯創", "ClosingPrice": "105", "Change": "5.3", "TradeValue": "20000000000"},
        {"Code": "9999", "Name": "冷門小股", "ClosingPrice": "10", "Change": "0.9", "TradeValue": "1000000"},  # 量太小濾掉
        {"Code": "00940", "Name": "某ETF", "ClosingPrice": "10", "Change": "1", "TradeValue": "90000000000"},  # 非4碼濾掉
    ]
    out = twse_top_gainers(rows, n=5)
    codes = [s["code"] for s in out]
    assert codes == ["3231", "2330"]  # 緯創 +5.3% > 台積電 +2.07%
    assert "9999" not in codes and "00940" not in codes


def test_parse_fred_csv():
    csv_text = "observation_date,SP500\n2026-06-16,7511.35\n2026-06-17,7420.10\n"
    out = parse_fred_csv(csv_text)
    assert out["close"] == 7420.10
    assert out["change_pct"] == round((7420.10 - 7511.35) / 7511.35 * 100, 2)


def test_parse_fred_csv_skips_blanks():
    csv_text = "observation_date,VIXCLS\n2026-06-15,.\n2026-06-16,16.41\n2026-06-17,18.44\n"
    out = parse_fred_csv(csv_text)
    assert out["close"] == 18.44
