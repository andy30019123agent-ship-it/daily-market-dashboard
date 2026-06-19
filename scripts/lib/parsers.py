"""純解析函式（可單元測試，不發網路請求）。

對應 Task 0 驗證過的資料源：
- TWSE MI_INDEX（大盤各指數每日）
- TWSE FMTQIK（大盤成交統計，含 TAIEX 與成交金額歷史）
- TWSE STOCK_DAY_ALL（個股當日成交，用來取漲幅榜熱門股）
- FRED fredgraph.csv（美股指數 / VIX 收盤歷史）
"""
import csv
import io


def roc_to_iso(roc: str) -> str:
    """民國日期 '1150617' -> '2026-06-17'。"""
    roc = str(roc).strip()
    if len(roc) != 7:
        return roc
    y = int(roc[:3]) + 1911
    return f"{y}-{roc[3:5]}-{roc[5:7]}"


def _f(x):
    """容錯轉 float：去逗號、'--'/'X' 視為 None。"""
    try:
        s = str(x).replace(",", "").strip()
        if s in ("", "--", "X", "N/A"):
            return None
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_twse_index(rows: list, name: str = "發行量加權股價指數") -> dict:
    """從 MI_INDEX 取指定指數的收盤與漲跌幅。"""
    for r in rows:
        if r.get("指數") == name:
            sign = -1 if r.get("漲跌", "+").strip() in ("-", "－") else 1
            return {
                "name": name,
                "close": _f(r.get("收盤指數")),
                "change": (_f(r.get("漲跌點數")) or 0) * sign,
                "change_pct": (_f(r.get("漲跌百分比")) or 0) * sign,
            }
    raise KeyError(f"MI_INDEX 找不到指數：{name}")


def parse_fmtqik(rows: list, spark_n: int = 20) -> dict:
    """從 FMTQIK 取最新成交金額（億元）與 TAIEX 走勢取樣。"""
    valid = [r for r in rows if _f(r.get("TAIEX")) is not None]
    if not valid:
        raise ValueError("FMTQIK 無有效資料")
    last = valid[-1]
    trade_value = _f(last.get("TradeValue"))
    return {
        "date": roc_to_iso(last.get("Date", "")),
        "taiex": _f(last.get("TAIEX")),
        "trade_value_yi": round(trade_value / 1e8) if trade_value else None,  # 元 -> 億
        "spark": [_f(r.get("TAIEX")) for r in valid[-spark_n:]],
    }


def twse_top_gainers(rows: list, n: int = 5, min_value_yi: float = 5) -> list:
    """從 STOCK_DAY_ALL 取漲幅榜前 N（過濾成交金額過小的冷門股）。"""
    out = []
    for r in rows:
        close = _f(r.get("ClosingPrice"))
        change = _f(r.get("Change"))
        value = _f(r.get("TradeValue"))
        code = (r.get("Code") or "").strip()
        if close is None or change is None or value is None:
            continue
        if value < min_value_yi * 1e8:
            continue
        if len(code) != 4:  # 只取上市普通股（4 碼），濾掉 ETF/權證等
            continue
        prev = close - change
        if prev <= 0:
            continue
        pct = round(change / prev * 100, 2)
        out.append({"code": code, "name": (r.get("Name") or "").strip(), "change_pct": pct})
    out.sort(key=lambda x: x["change_pct"], reverse=True)
    return out[:n]


def _col(fields: list, *keys, exact=False):
    for i, f in enumerate(fields):
        f = f.strip()
        for k in keys:
            if (f == k) if exact else (k in f):
                return i
    return None


def _sign_from_cell(s) -> int:
    s = str(s)
    if "green" in s or "-" in s or "−" in s:
        return -1
    return 1


def roc_slash_to_ymd(s: str) -> str:
    """'115/06/18' -> '20260618'。"""
    p = str(s).strip().split("/")
    if len(p) == 3:
        return f"{int(p[0]) + 1911}{p[1]}{p[2]}"
    return s


def parse_rwd_index(payload: dict, name: str = "發行量加權股價指數") -> dict:
    """RWD afterTrading/MI_INDEX(type=IND) -> 指定指數收盤與漲跌幅。

    回應為多表（tables）結構，價格指數在第一張表。
    """
    rows = payload.get("data", [])
    if not rows:
        for t in payload.get("tables", []):
            rows = rows + list(t.get("data", []))
    for row in rows:
        if (row[0] or "").strip() == name:
            sign = _sign_from_cell(row[2])
            return {"name": name, "close": _f(row[1]),
                    "change": (_f(row[3]) or 0) * sign,
                    "change_pct": (_f(row[4]) or 0) * sign}
    raise KeyError(f"RWD MI_INDEX 找不到 {name}")


def parse_rwd_fmtqik(payload: dict, spark_n: int = 20) -> dict:
    """RWD afterTrading/FMTQIK -> 最新成交金額（億）、TAIEX、走勢、交易日。"""
    fields, rows = payload.get("fields", []), payload.get("data", [])
    ci_val = _col(fields, "成交金額")
    ci_idx = _col(fields, "發行量加權股價指數")
    ci_date = _col(fields, "日期")
    valid = [r for r in rows if _f(r[ci_idx]) is not None]
    if not valid:
        raise ValueError("RWD FMTQIK 無有效資料")
    last = valid[-1]
    tv = _f(last[ci_val])
    return {
        "date_ymd": roc_slash_to_ymd(last[ci_date]),
        "taiex": _f(last[ci_idx]),
        "trade_value_yi": round(tv / 1e8) if tv else None,
        "spark": [_f(r[ci_idx]) for r in valid[-spark_n:]],
    }


def parse_rwd_gainers(payload: dict, n: int = 5, min_value_yi: float = 5) -> list:
    """RWD afterTrading/STOCK_DAY_ALL -> 漲幅榜前 N（濾 4 碼、成交額）。"""
    fields = payload.get("fields", [])
    ci_code = _col(fields, "證券代號", exact=True)
    ci_name = _col(fields, "證券名稱", exact=True)
    ci_close = _col(fields, "收盤價", exact=True)
    ci_chg = _col(fields, "漲跌價差", exact=True)
    ci_val = _col(fields, "成交金額", exact=True)
    out = []
    for r in payload.get("data", []):
        code = (r[ci_code] or "").strip()
        if len(code) != 4:
            continue
        close, chg, val = _f(r[ci_close]), _f(r[ci_chg]), _f(r[ci_val])
        if None in (close, chg, val) or val < min_value_yi * 1e8:
            continue
        prev = close - chg
        if prev <= 0:
            continue
        out.append({"code": code, "name": (r[ci_name] or "").strip(),
                    "change_pct": round(chg / prev * 100, 2)})
    out.sort(key=lambda x: x["change_pct"], reverse=True)
    return out[:n]


def parse_bfi82u(payload: dict) -> dict:
    """大盤三大法人買賣超金額（rwd JSON）-> 外資/投信/自營 買賣差額（億元，四捨五入到小數 1 位）。"""
    rows = payload.get("data", [])
    net = {"外資": 0.0, "投信": 0.0, "自營": 0.0}
    found = False
    for r in rows:
        name = (r[0] or "").strip()
        diff = _f(r[-1])  # 買賣差額
        if diff is None:
            continue
        if name.startswith("外資及陸資") or name == "外資自營商":
            net["外資"] += diff; found = True
        elif name == "投信":
            net["投信"] += diff; found = True
        elif name.startswith("自營商"):              # 自行買賣 + 避險
            net["自營"] += diff; found = True
    if not found:
        raise ValueError("BFI82U 無法人資料")
    return {k: round(v / 1e8, 1) for k, v in net.items()}


def _t86_index(fields: list) -> dict:
    """T86 欄位名 -> 索引（容忍名稱微調）。"""
    idx = {}
    for i, f in enumerate(fields):
        f = f.strip()
        if f.startswith("證券代號"):
            idx["code"] = i
        elif f.startswith("證券名稱"):
            idx["name"] = i
        elif f == "外陸資買賣超股數(不含外資自營商)":
            idx["foreign_main"] = i
        elif f == "外資自營商買賣超股數":
            idx["foreign_dealer"] = i
        elif f == "投信買賣超股數":
            idx["trust"] = i
        elif f == "自營商買賣超股數":
            idx["dealer"] = i
    return idx


def parse_t86_top(payload: dict, n: int = 5) -> dict:
    """個股三大法人買賣超（rwd JSON）-> 外資/投信/自營 各買超前 N（單位：張）。"""
    fields = payload.get("fields", [])
    rows = payload.get("data", [])
    idx = _t86_index(fields)
    required = ("code", "name", "trust", "dealer")
    if not all(k in idx for k in required) or not ("foreign_main" in idx):
        raise ValueError(f"T86 欄位不符：{fields}")

    groups = {"foreign": [], "trust": [], "dealer": []}
    for r in rows:
        code = (r[idx["code"]] or "").strip()
        if len(code) != 4:                      # 只取上市普通股
            continue
        name = (r[idx["name"]] or "").strip()
        foreign = (_f(r[idx["foreign_main"]]) or 0) + (_f(r[idx.get("foreign_dealer", -1)]) or 0 if "foreign_dealer" in idx else 0)
        trust = _f(r[idx["trust"]]) or 0
        dealer = _f(r[idx["dealer"]]) or 0
        groups["foreign"].append({"code": code, "name": name, "net": foreign})
        groups["trust"].append({"code": code, "name": name, "net": trust})
        groups["dealer"].append({"code": code, "name": name, "net": dealer})

    def fmt(lst, sign):
        return [{"code": s["code"], "name": s["name"], "zhang": round(abs(s["net"]) / 1000)}
                for s in lst if s["net"] * sign > 0][:n]

    out = {}
    for g, lst in groups.items():
        buy = sorted(lst, key=lambda x: x["net"], reverse=True)   # 買超：淨額大→小
        sell = sorted(lst, key=lambda x: x["net"])                # 賣超：淨額負最大→
        out[g] = {"buy": fmt(buy, 1), "sell": fmt(sell, -1)}
    return out


def parse_rwd_sectors(payload: dict, n: int = 5) -> dict:
    """RWD MI_INDEX(table[0]) 各類股指數 -> 漲幅 / 跌幅 Top N（真實類股表現）。"""
    rows = payload.get("data", [])
    if not rows:
        for t in payload.get("tables", []):
            rows = rows + list(t.get("data", []))
    secs = []
    for r in rows:
        nm = (r[0] or "").strip()
        # 只取單一產業類指數，排除「未含…」「報酬」「跨市場」等彙總
        if not nm.endswith("類指數") or nm.startswith("未含"):
            continue
        pct = _f(r[4])
        if pct is None:
            continue
        sign = _sign_from_cell(r[2])
        secs.append({"name": nm.replace("類指數", ""), "pct": pct * sign})
    if not secs:
        raise ValueError("MI_INDEX 無類股指數")
    up = sorted(secs, key=lambda x: x["pct"], reverse=True)[:n]
    down = sorted(secs, key=lambda x: x["pct"])[:n]
    mx = max((abs(s["pct"]) for s in secs), default=1) or 1

    def row(s):
        return {"name": s["name"], "amount": f"{'+' if s['pct'] >= 0 else ''}{s['pct']:.2f}%",
                "weight": round(abs(s["pct"]) / mx, 2)}
    return {"in": [row(s) for s in up], "out": [row(s) for s in down]}


# TWSE 上市產業別代碼 → 名稱
INDUSTRY = {
    "01": "水泥", "02": "食品", "03": "塑膠", "04": "紡織纖維", "05": "電機機械",
    "06": "電器電纜", "08": "玻璃陶瓷", "09": "造紙", "10": "鋼鐵", "11": "橡膠",
    "12": "汽車", "14": "建材營造", "15": "航運", "16": "觀光餐旅", "17": "金融保險",
    "18": "貿易百貨", "20": "其他", "21": "化學工業", "22": "生技醫療", "23": "油電燃氣",
    "24": "半導體", "25": "電腦及週邊設備", "26": "光電", "27": "通信網路", "28": "電子零組件",
    "29": "電子通路", "30": "資訊服務", "31": "其他電子", "35": "綠能環保", "36": "數位雲端",
    "37": "運動休閒", "38": "居家生活",
}
# 類股指數名（MI_INDEX）對不上單一產業時的覆寫
SECTOR_OVERRIDE = {
    "塑膠化工": ["03", "21"], "金融": ["17"], "金融保險": ["17"],
    "觀光": ["16", "37"], "觀光餐旅": ["16", "37"], "化學生技醫療": ["21", "22"],
}


def sector_to_codes(name: str) -> list:
    if name in SECTOR_OVERRIDE:
        return SECTOR_OVERRIDE[name]
    codes = [c for c, n in INDUSTRY.items() if n == name]
    if not codes:
        codes = [c for c, n in INDUSTRY.items() if name in n or n in name]
    return codes


def build_sector_constituents(sector_names: list, sda_payload: dict, basic_list: list, n: int = 12) -> dict:
    """類股名 -> 成分股（依成交值取前 n，含當日漲跌）。
    串 STOCK_DAY_ALL（價/量）與上市公司基本資料（產業別）。
    """
    stock_ind = {r.get("公司代號"): r.get("產業別") for r in basic_list}
    fields = sda_payload.get("fields", [])
    ci_code = _col(fields, "證券代號", exact=True)
    ci_name = _col(fields, "證券名稱", exact=True)
    ci_close = _col(fields, "收盤價", exact=True)
    ci_chg = _col(fields, "漲跌價差", exact=True)
    ci_val = _col(fields, "成交金額", exact=True)

    rows = []
    for r in sda_payload.get("data", []):
        code = (r[ci_code] or "").strip()
        if len(code) != 4:
            continue
        close, chg, val = _f(r[ci_close]), _f(r[ci_chg]), _f(r[ci_val])
        if None in (close, chg, val) or close == 0:
            continue
        prev = close - chg
        pct = round(chg / prev * 100, 2) if prev else 0
        rows.append({"code": code, "name": (r[ci_name] or "").strip(),
                     "change_pct": pct, "value": val, "ind": stock_ind.get(code)})

    out = {}
    for name in sector_names:
        codes = set(sector_to_codes(name))
        members = [s for s in rows if s["ind"] in codes]
        members.sort(key=lambda x: x["value"], reverse=True)
        out[name] = [{"code": s["code"], "name": s["name"], "change_pct": s["change_pct"]}
                     for s in members[:n]]
    return out


def parse_fred_csv(csv_text: str) -> dict:
    """FRED fredgraph.csv -> 最新收盤與漲跌幅（用最後兩個有效值）。"""
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader, None)
    vals = []  # (date, close)
    for row in reader:
        if len(row) < 2:
            continue
        v = _f(row[1])
        if v is not None:
            vals.append((row[0], v))
    if not vals:
        raise ValueError("FRED CSV 無有效數值")
    date, close = vals[-1]
    prev = vals[-2][1] if len(vals) >= 2 else None
    change_pct = round((close - prev) / prev * 100, 2) if prev else None
    return {
        "date": date,
        "close": close,
        "change_pct": change_pct,
        "spark": [v for _, v in vals[-20:]],
    }
