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

    out = {}
    for g, lst in groups.items():
        lst.sort(key=lambda x: x["net"], reverse=True)
        out[g] = [{"code": s["code"], "name": s["name"],
                   "zhang": round(s["net"] / 1000)} for s in lst[:n] if s["net"] > 0]
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
