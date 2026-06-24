import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.lib.parsers import (  # noqa: E402
    roc_to_iso, parse_twse_index, parse_fmtqik, twse_top_gainers, parse_fred_csv,
    parse_bfi82u, parse_t86_top, parse_rwd_sectors, build_sector_constituents,
    parse_rwd_index, parse_rwd_gainers,
)


# 真實 RWD MI_INDEX 格式：漲跌欄含顏色標記、漲跌點數「無號」、漲跌百分比「已帶號」。
def test_parse_rwd_index_down_day():
    payload = {"data": [
        ["發行量加權股價指數", "46,043.60", "<p style ='color:green'>-</p>", "1,057.05", "-2.24", ""],
    ]}
    out = parse_rwd_index(payload)
    assert out["close"] == 46043.60
    assert out["change"] == -1057.05    # 點數無號 → 乘 sign(-1)
    assert out["change_pct"] == -2.24   # 百分比已帶號 → 不再乘 sign（否則負負得正）


def test_parse_rwd_index_up_day():
    payload = {"data": [
        ["發行量加權股價指數", "47,100.65", "<p style ='color:red'>+</p>", "587.81", "1.28", ""],
    ]}
    out = parse_rwd_index(payload)
    assert out["change"] == 587.81
    assert out["change_pct"] == 1.28


def test_parse_rwd_gainers_accepts_csv_shape():
    # STOCK_DAY_ALL 端點偶爾回 CSV；get_table 轉成的 {fields, data} 應能正常解析
    payload = {
        "fields": ["日期", "證券代號", "證券名稱", "成交股數", "成交金額",
                   "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
        "data": [
            ["1150624", "2330", "台積電", "30000000", "30000000000",
             "1000", "1050", "995", "1040", "40", "50000"],
            ["1150624", "00631L", "元大台灣50正2", "1000", "9999999999",
             "200", "201", "199", "200", "0", "100"],  # 非 4 碼 → 濾掉
        ],
    }
    out = parse_rwd_gainers(payload, n=5)
    assert len(out) == 1 and out[0]["code"] == "2330"
    assert out[0]["change_pct"] == round(40 / 1000 * 100, 2)


def test_parse_rwd_sectors():
    payload = {"tables": [{"data": [
        ["發行量加權股價指數", "46,465.20", "<p style='color:red'>+</p>", "587", "1.28", ""],
        ["塑膠類指數", "261.34", "<p style='color:red'>+</p>", "17", "7.27", ""],
        ["食品類指數", "1,925.88", "<p style='color:green'>-</p>", "22", "-1.16", ""],
        ["未含金融指數", "41,713.54", "<p style='color:red'>+</p>", "1", "1.27", ""],
    ]}]}
    out = parse_rwd_sectors(payload, n=5)
    assert out["in"][0]["name"] == "塑膠" and out["in"][0]["amount"] == "+7.27%"
    assert out["out"][0]["name"] == "食品" and out["out"][0]["amount"] == "-1.16%"
    assert not any(s["name"].startswith("未含") for s in out["in"] + out["out"])  # 排除彙總


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


def test_parse_bfi82u():
    payload = {"fields": ["單位名稱", "買進金額", "賣出金額", "買賣差額"], "data": [
        ["自營商(自行買賣)", "1", "1", "1,876,576,965"],
        ["自營商(避險)", "1", "1", "-6,145,439,321"],
        ["投信", "1", "1", "-206,062,001"],
        ["外資及陸資(不含外資自營商)", "1", "1", "-20,683,737,771"],
        ["外資自營商", "0", "0", "0"],
        ["合計", "1", "1", "-25,158,662,128"],
    ]}
    out = parse_bfi82u(payload)
    assert out["外資"] == -206.8       # -20,683,737,771 / 1e8
    assert out["投信"] == -2.1
    assert out["自營"] == -42.7        # (1,876,576,965 - 6,145,439,321)/1e8


def test_parse_t86_top():
    fields = ["證券代號", "證券名稱",
              "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)", "外陸資買賣超股數(不含外資自營商)",
              "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
              "投信買進股數", "投信賣出股數", "投信買賣超股數", "自營商買賣超股數",
              "自營商買進股數(自行買賣)", "自營商賣出股數(自行買賣)", "自營商買賣超股數(自行買賣)",
              "自營商買進股數(避險)", "自營商賣出股數(避險)", "自營商買賣超股數(避險)", "三大法人買賣超股數"]
    data = [
        ["2330", "台積電", "0", "0", "10,000,000", "0", "0", "0", "0", "0", "2,000,000", "500,000", "0", "0", "0", "0", "0", "0", "0"],
        ["2317", "鴻海", "0", "0", "5,000,000", "0", "0", "0", "0", "0", "9,000,000", "100,000", "0", "0", "0", "0", "0", "0", "0"],
        ["1303", "南亞", "0", "0", "-1,000,000", "0", "0", "0", "0", "0", "0", "-50,000", "0", "0", "0", "0", "0", "0", "0"],
    ]
    out = parse_t86_top({"fields": fields, "data": data}, n=5)
    # 買超榜
    assert out["foreign"]["buy"][0]["code"] == "2330" and out["foreign"]["buy"][0]["zhang"] == 10000
    assert out["trust"]["buy"][0]["code"] == "2317" and out["trust"]["buy"][0]["zhang"] == 9000
    # 賣超榜（南亞外資 -1,000,000 股 = 1000 張，顯示為正）
    assert out["foreign"]["sell"][0]["code"] == "1303" and out["foreign"]["sell"][0]["zhang"] == 1000
    assert all(s["zhang"] > 0 for g in out.values() for side in g.values() for s in side)


def test_parse_fred_csv():
    csv_text = "observation_date,SP500\n2026-06-16,7511.35\n2026-06-17,7420.10\n"
    out = parse_fred_csv(csv_text)
    assert out["close"] == 7420.10
    assert out["change_pct"] == round((7420.10 - 7511.35) / 7511.35 * 100, 2)


def test_parse_fred_csv_skips_blanks():
    csv_text = "observation_date,VIXCLS\n2026-06-15,.\n2026-06-16,16.41\n2026-06-17,18.44\n"
    out = parse_fred_csv(csv_text)
    assert out["close"] == 18.44


def test_build_sector_constituents():
    sda = {"fields": ["證券代號", "證券名稱", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
           "data": [
               ["2330", "台積電", "1", "9000000000", "1", "1", "1", "1085", "+22", "1"],
               ["1303", "南亞", "1", "5000000000", "1", "1", "1", "100", "+9", "1"],
               ["2317", "鴻海", "1", "8000000000", "1", "1", "1", "200", "-2", "1"],
           ]}
    basic = [{"公司代號": "2330", "產業別": "24"}, {"公司代號": "1303", "產業別": "03"}, {"公司代號": "2317", "產業別": "28"}]
    out = build_sector_constituents(["半導體", "塑膠"], sda, basic, n=5)
    assert out["半導體"][0]["code"] == "2330"
    assert out["塑膠"][0]["code"] == "1303" and out["塑膠"][0]["change_pct"] == round(9 / 91 * 100, 2)
