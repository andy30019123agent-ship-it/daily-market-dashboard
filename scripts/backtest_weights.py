"""回測「籌碼/價量結構/基本面」權重（離線研究工具，v2 方法論）。

用 TWSE 官方 T86（法人）＋ FinMind（價量/月營收）重建過去 N 個月的低基期候選＋三子分，
量測入選後未來多個 horizon 報酬，以「每日 IC 時間序列」為主指標網格搜尋最佳權重，出建議報告。

v2 重點（比 v1 更正確）：
- 候選對齊線上：法人淨買超「億元」＋門檻（≥inst_min_yi、低基期 gate），非只用股數 top-K。
- 主指標＝每個 as-of 日各自算 IC，取平均＋t 值＋為正比例（處理樣本不獨立）。
- K-fold 穩定度；多 horizon（10/20/40）交叉印證。
- 禁前視：計分只用 as-of 以前資料；月營收以 create_time（公告日）≤ as-of 過濾。

用法：
  python3 scripts/backtest_weights.py --start 2025-07-01 --end 2026-06-05 --topk 300

結果是「建議」，不自動改線上權重。全部快取到 backtest/cache/。
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import time

from scripts.lib import backtest as bt
from scripts.lib import twse_hist as th
from scripts.lib.potential import (
    DEFAULTS, chip_score, low_base_metrics, structure_score,
    revenue_yoy, fundamental_score, finmind_history, finmind_revenue,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "backtest" / "cache"
OUTDIR = ROOT / "backtest"


def _cache_list(path, produce):
    """磁碟快取，但**只快取非空結果**——FinMind 限流失敗回 []，若快取起來會永久
    把該檔誤存成無資料。空結果不快取，下次重試。"""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    val = produce() or []
    if val:
        path.write_text(json.dumps(val, ensure_ascii=False), encoding="utf-8")
    return val


def trading_days(start, end, sleep):
    days = []
    d = datetime.date.fromisoformat(start)
    endd = datetime.date.fromisoformat(end)
    while d <= endd:
        if d.weekday() < 5:
            ymd = d.strftime("%Y%m%d")
            cached = (CACHE / f"t86-{ymd}.json").exists()
            t86 = th.fetch_t86_cached(ymd, CACHE)
            if t86:
                days.append((d.isoformat(), t86))
            if not cached:
                time.sleep(sleep)
        d += datetime.timedelta(days=1)
    return days


def price_rows(code, start_date):
    rows = _cache_list(CACHE / f"px-{code}.json",
                       lambda: finmind_history(code, start_date))
    if rows:
        rows.sort(key=lambda r: r.get("date", ""))
    return rows


def revenue_rows(code, start_date):
    return _cache_list(CACHE / f"rev-{code}.json",
                       lambda: finmind_revenue(code, start_date))


def build_samples(args, horizons):
    days = trading_days(args.start, args.end, args.sleep)
    print(f"交易日數：{len(days)}")
    empty = {"trading_days": len(days), "asof_dates": 0, "unique_codes": 0, "samples": 0}
    if len(days) < args.window:
        print("⚠️ 交易日不足（需 ≥ window）。")
        return [], empty
    idxs = list(range(args.window - 1, len(days)))
    asof_idxs = idxs[::args.rebalance]
    fin_start = (datetime.date.fromisoformat(args.start)
                 - datetime.timedelta(days=420)).isoformat()

    samples = []
    seen = set()
    for ai in asof_idxs:
        D = days[ai][0]
        win = days[ai - args.window + 1: ai + 1]
        agg = {}
        bdays = {}
        for _, t86 in win:
            for code, sh in t86.items():
                agg[code] = agg.get(code, 0) + sh
                if sh > 0:
                    bdays[code] = bdays.get(code, 0) + 1
        cands = sorted((c for c in agg if agg[c] > 0), key=lambda c: agg[c], reverse=True)[:args.topk]
        for code in cands:
            try:
                px = price_rows(code, fin_start)
                if code not in seen:
                    seen.add(code)
                    time.sleep(args.sleep)
                if not px:
                    continue
                px_upto = [r for r in px if r.get("date", "") <= D]
                if len(px_upto) < 60:
                    continue
                close_by_date = {r["date"]: r.get("close") for r in px}
                # 億元法人淨買超（對齊線上）＋門檻
                inst_yi = 0.0
                for dd, t86 in win:
                    sh = t86.get(code, 0)
                    c = close_by_date.get(dd)
                    if sh and c:
                        inst_yi += sh * c / 1e8
                if inst_yi < DEFAULTS["inst_min_yi"]:
                    continue  # 對齊線上 pick_accumulators 門檻
                chip_s = chip_score({"inst_net_yi": round(inst_yi, 2),
                                     "buy_days": bdays.get(code, 0)},
                                    args.window, DEFAULTS["chip_sat"])
                m = low_base_metrics(px_upto)
                if not m or m["price_pos"] > DEFAULTS["pos_max"]:
                    continue
                struct_s = structure_score(m, DEFAULTS["vol_hi"], DEFAULTS["pos_ref"])
                rev = revenue_rows(code, fin_start)
                rev_upto = [r for r in rev if (r.get("create_time") or r.get("date") or "") <= D]
                fund_s = fundamental_score(revenue_yoy(rev_upto), DEFAULTS["yoy_full"])
                ret_by_h = {h: bt.forward_return(px, D, h) for h in horizons}
                if all(v is None for v in ret_by_h.values()):
                    continue
                samples.append({"date": D, "code": code, "chip": chip_s,
                                "struct": struct_s, "fund": fund_s, "ret_by_h": ret_by_h})
            except Exception as e:
                print(f"  跳過 {code}@{D}：{e}")
    meta = {"trading_days": len(days), "asof_dates": len(asof_idxs),
            "unique_codes": len(seen), "samples": len(samples)}
    print(f"樣本：{meta}")
    return samples, meta


def analyze_horizon(samples, h, step):
    """單一 horizon：把 ret 攤平後跑 per-date IC 搜尋＋K-fold 穩定度。"""
    sm = [{**s, "ret": s["ret_by_h"].get(h)} for s in samples if s["ret_by_h"].get(h) is not None]
    res = bt.grid_search_ic(sm, step=step)
    if res.get("best"):
        w = res["best"]["w"]
        res["best"]["folds"] = bt.fold_means(sm, w, k=4)
        # 分數校準：用最佳權重把每檔算成 0~100 分 → 各分數帶的歷史命中率/平均報酬
        scored = [(round(100 * bt.weighted_score(s, w)), s["ret"]) for s in sm]
        res["best"]["calibration"] = bt.score_calibration(scored, edges=[40, 55, 70])
    res["n_ret"] = len(sm)
    return res


def fmt_w(w):
    return f"籌碼 {w['chip']:.0%}／價量結構 {w['struct']:.0%}／基本面 {w['fund']:.0%}"


def write_report(args, meta, by_h, horizons):
    rundate = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / f"report-{rundate}.json").write_text(
        json.dumps({"args": vars(args), "meta": meta, "by_horizon": by_h},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    L = [f"# 權重回測報告 v2 · {rundate}", ""]
    L.append(f"- 區間：{args.start} ～ {args.end}（僅上市、每 {args.rebalance} 交易日一次、每次 top{args.topk}、億元門檻 {DEFAULTS['inst_min_yi']}）")
    L.append(f"- 吸籌窗口：{args.window} 交易日｜樣本 **{meta['samples']}**（as-of {meta['asof_dates']} 個、個股 {meta['unique_codes']} 檔）")
    L.append(f"- **主指標＝每日 IC 平均＋t 值**（t≳2 才算訊號可信）；多 horizon 交叉印證")
    L.append("")
    L.append("## 各持有天數的建議權重")
    L.append("| Horizon | 建議權重 | 平均IC | t值 | 正IC日% | 前後折穩定 |")
    L.append("|---|---|---|---|---|---|")
    for h in horizons:
        r = by_h[h]
        b = r.get("best")
        if not b:
            L.append(f"| {h} 日 | 樣本不足 | — | — | — | — |")
            continue
        folds = "/".join(f"{x:.2f}" for x in (b.get("folds") or []))
        L.append(f"| {h} 日 | {fmt_w(b['w'])} | {b['mean_ic']} | {b['t']} | "
                 f"{int((b['pos_frac'] or 0)*100)}% | {folds} |")
    L.append("")
    # 以 20 日為主檔詳列 top 組合
    main = by_h.get(20) or by_h.get(horizons[0])
    if main and main.get("best"):
        L.append(f"## 主 horizon（{20 if by_h.get(20) else horizons[0]} 日）IC 前 10")
        L.append("| 籌碼 | 價量結構 | 基本面 | 平均IC | t值 | 正IC日% |")
        L.append("|---|---|---|---|---|---|")
        for r in main["top"]:
            w = r["w"]
            L.append(f"| {w['chip']:.0%} | {w['struct']:.0%} | {w['fund']:.0%} | "
                     f"{r['mean_ic']} | {r['t']} | {int((r['pos_frac'] or 0)*100)}% |")
        L.append("")
    # 分數校準（主 horizon）：分數帶 → 歷史命中率/平均報酬
    if main and main.get("best") and main["best"].get("calibration"):
        L.append(f"## 分數校準（{20 if by_h.get(20) else horizons[0]} 日）——「幾分」代表什麼")
        L.append("| 分數帶 | 樣本數 | 歷史命中率(報酬>0) | 平均報酬 |")
        L.append("|---|---|---|---|")
        for b in main["best"]["calibration"]:
            hr = f"{int(b['hit_rate']*100)}%" if b["hit_rate"] is not None else "—"
            ar = f"{b['avg_ret']*100:+.1f}%" if b["avg_ret"] is not None else "—"
            L.append(f"| {b['lo']}–{b['hi']} 分 | {b['n']} | {hr} | {ar} |")
        L.append("_註：以最佳權重回算的分數帶統計；讓「76 分」對應到歷史命中率/期望報酬。_")
        L.append("")
    L.append("### 怎麼讀")
    L.append("- **t 值**：各持有天數若 t 都 ≳2 且權重方向一致 → 訊號可信、可考慮微調線上權重；t 偏低或各 horizon 打架 → 別動，續蒐資料。")
    L.append("- **前後折穩定**：4 段各自的平均 IC，差異大＝過度配適，權重別照抄。")
    L.append("- 對照現行線上（題材除外）約 籌碼 44%／價量結構 44%／基本面 12%。")
    L.append("")
    L.append("---")
    L.append("⚠️ 過去統計、**僅研究參考不保證未來**；題材分未進回測；倖存者偏誤/交易成本未建模。此為建議，需人工確認才手動改 DEFAULTS。")
    path = OUTDIR / f"report-{rundate}.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--horizons", default="10,20,40")
    ap.add_argument("--window", type=int, default=10)
    ap.add_argument("--topk", type=int, default=300)
    ap.add_argument("--rebalance", type=int, default=5)
    ap.add_argument("--grid-step", type=float, default=0.1)
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()
    horizons = [int(x) for x in args.horizons.split(",")]

    samples, meta = build_samples(args, horizons)
    by_h = {h: analyze_horizon(samples, h, args.grid_step) for h in horizons}
    path = write_report(args, meta, by_h, horizons)
    print(f"報告：{path}")
    for h in horizons:
        b = by_h[h].get("best")
        if b:
            print(f"  {h}日：{fmt_w(b['w'])}｜平均IC {b['mean_ic']}｜t {b['t']}｜正IC日 {int((b['pos_frac'] or 0)*100)}%")


if __name__ == "__main__":
    main()
