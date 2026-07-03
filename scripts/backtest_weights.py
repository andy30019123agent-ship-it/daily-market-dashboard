"""回測「籌碼/價量結構/基本面」權重（離線研究工具）。

用 TWSE 官方 T86（法人）＋ FinMind（價量/月營收）重建過去 N 個月的低基期候選＋三子分，
量測入選後未來 horizon 交易日報酬，網格搜尋最佳權重，出建議報告。

用法：
  python3 scripts/backtest_weights.py --start 2026-04-01 --end 2026-06-30 --topk 40 --grid-step 0.2

一律快取到 backtest/cache/（抓過不重抓）；禁前視（計分只用 as-of 日以前資料）。
結果是「建議」，不自動改線上權重。
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


def _cache_json(path, produce):
    """通用磁碟快取：有就讀、沒有就 produce() 存。"""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    val = produce()
    path.write_text(json.dumps(val, ensure_ascii=False), encoding="utf-8")
    return val


def trading_days(start, end, sleep):
    """逐日試抓 T86，回 [(date_iso, {code:shares}), ...] 只含交易日。"""
    days = []
    d = datetime.date.fromisoformat(start)
    endd = datetime.date.fromisoformat(end)
    while d <= endd:
        if d.weekday() < 5:  # 週末直接跳過，省呼叫
            ymd = d.strftime("%Y%m%d")
            cached = (CACHE / f"t86-{ymd}.json").exists()
            t86 = th.fetch_t86_cached(ymd, CACHE)
            if t86:
                days.append((d.isoformat(), t86))
            if not cached:
                time.sleep(sleep)  # 只在真的新抓時睡，避免撞 TWSE 限流
        d += datetime.timedelta(days=1)
    return days


def price_rows(code, start_date, sleep):
    rows = _cache_json(CACHE / f"px-{code}.json",
                       lambda: finmind_history(code, start_date))
    if rows:
        rows.sort(key=lambda r: r.get("date", ""))
    return rows


def revenue_rows(code, start_date, sleep):
    return _cache_json(CACHE / f"rev-{code}.json",
                       lambda: finmind_revenue(code, start_date))


def build_samples(args):
    days = trading_days(args.start, args.end, args.sleep)
    print(f"交易日數：{len(days)}")
    empty_meta = {"trading_days": len(days), "asof_dates": 0,
                  "unique_codes": 0, "samples": 0}
    if len(days) < args.window:
        print("⚠️ 交易日不足（需 ≥ window），請拉長區間。")
        return [], empty_meta

    # as-of 日只需要 window 天前置（吸籌窗口）；未來 horizon 報酬由 FinMind 資料提供，
    # 不受 T86 抓取區間限制（近 horizon 交易日內的 as-of 因無未來資料，會在 ret=None 時剔除）。
    idxs = list(range(args.window - 1, len(days)))
    asof_idxs = idxs[::args.rebalance]  # 每 rebalance 個交易日取一個 as-of
    fin_start = (datetime.date.fromisoformat(args.start)
                 - datetime.timedelta(days=420)).isoformat()

    samples = []
    seen_codes = set()
    for ai in asof_idxs:
        D = days[ai][0]
        win = days[ai - args.window + 1: ai + 1]  # 近 window 交易日（含 D）
        # 聚合法人淨額股數
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
                px = price_rows(code, fin_start, args.sleep)
                if code not in seen_codes:
                    seen_codes.add(code)
                    time.sleep(args.sleep)  # 只在真的新抓時 sleep（快取命中不睡）
                if not px:
                    continue
                px_upto = [r for r in px if r.get("date", "") <= D]
                if len(px_upto) < 60:
                    continue
                close_by_date = {r["date"]: r.get("close") for r in px}
                # chip：Σ 淨額股數×當日收盤/1e8（億）＋買超天數
                inst_yi = 0.0
                for dd, t86 in win:
                    sh = t86.get(code, 0)
                    c = close_by_date.get(dd)
                    if sh and c:
                        inst_yi += sh * c / 1e8
                chip_s = chip_score({"inst_net_yi": round(inst_yi, 2),
                                     "buy_days": bdays.get(code, 0)},
                                    args.window, DEFAULTS["chip_sat"])
                # struct：低基期指標（截止 D）→ 過 gate
                m = low_base_metrics(px_upto)
                if not m or m["price_pos"] > DEFAULTS["pos_max"]:
                    continue
                struct_s = structure_score(m, DEFAULTS["vol_hi"], DEFAULTS["pos_ref"])
                # fund：月營收 YoY（截止 D）。**禁前視**：月營收約次月 10 日才公告，
                # 故以 FinMind 的 create_time（公告日）≤ D 過濾，不能只看營收月份。
                rev = revenue_rows(code, fin_start, args.sleep)
                rev_upto = [r for r in rev
                            if (r.get("create_time") or r.get("date") or "") <= D]
                fund_s = fundamental_score(revenue_yoy(rev_upto), DEFAULTS["yoy_full"])
                # 未來報酬
                ret = bt.forward_return(px, D, args.horizon)
                if ret is None:
                    continue
                samples.append({"date": D, "code": code, "chip": chip_s,
                                "struct": struct_s, "fund": fund_s, "ret": ret})
            except Exception as e:
                print(f"  跳過 {code}@{D}：{e}")
    meta = {"trading_days": len(days), "asof_dates": len(asof_idxs),
            "unique_codes": len(seen_codes), "samples": len(samples)}
    print(f"樣本：{meta}")
    return samples, meta


def write_report(args, samples, meta, res, halves):
    rundate = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    js = {"args": vars(args), "meta": meta, "result": res, "halves": halves}
    (OUTDIR / f"report-{rundate}.json").write_text(
        json.dumps(js, ensure_ascii=False, indent=1), encoding="utf-8")

    def fmt_w(w):
        return f"籌碼 {w['chip']:.0%}／價量結構 {w['struct']:.0%}／基本面 {w['fund']:.0%}"

    lines = [f"# 權重回測報告 · {rundate}", ""]
    lines.append(f"- 區間：{args.start} ～ {args.end}（僅上市、每 {args.rebalance} 交易日取一次）")
    lines.append(f"- 未來報酬視窗：{args.horizon} 交易日｜吸籌窗口：{args.window} 交易日｜每次 top{args.topk}")
    lines.append(f"- 樣本數：**{meta['samples']}**（as-of 日 {meta['asof_dates']} 個、個股 {meta['unique_codes']} 檔）")
    lines.append("")
    if res.get("best"):
        b = res["best"]
        lines.append(f"## 建議權重：{fmt_w(b['w'])}")
        lines.append(f"- 排序 IC＝**{b['ic']}**（越接近 1 越能把贏家排前面）｜高分−低分五分位報酬差＝{b['spread']}")
        lines.append(f"- 對照：目前線上（題材除外的三項相對比）約 籌碼 44%／價量結構 44%／基本面 12%")
        lines.append("")
        lines.append("### IC 前 10 名權重組合")
        lines.append("| 籌碼 | 價量結構 | 基本面 | IC | 五分位差 |")
        lines.append("|---|---|---|---|---|")
        for r in res["top"]:
            w = r["w"]
            lines.append(f"| {w['chip']:.0%} | {w['struct']:.0%} | {w['fund']:.0%} | {r['ic']} | {r['spread']} |")
        lines.append("")
    else:
        lines.append("## ⚠️ 樣本不足，無法得出建議權重（請拉長區間或提高 topk）")
        lines.append("")
    if halves.get("first") and halves.get("second"):
        lines.append("### 穩定度（前後兩半各自最佳）")
        lines.append(f"- 前半最佳：{fmt_w(halves['first']['w'])}（IC {halves['first']['ic']}）")
        lines.append(f"- 後半最佳：{fmt_w(halves['second']['w'])}（IC {halves['second']['ic']}）")
        lines.append("- 前後半差異大＝過度配適風險高，權重別照抄。")
        lines.append("")
    lines.append("---")
    lines.append("⚠️ 回測是過去統計、**僅研究參考，不保證未來**；題材分未進回測（維持固定加分）。")
    lines.append("此為建議，需人工確認後才手動更新 `scripts/lib/potential.py` 的 DEFAULTS 權重。")
    path = OUTDIR / f"report-{rundate}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--window", type=int, default=10)
    ap.add_argument("--topk", type=int, default=60)
    ap.add_argument("--rebalance", type=int, default=5)
    ap.add_argument("--grid-step", type=float, default=0.1)
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()

    samples, meta = build_samples(args)
    res = bt.grid_search_weights(samples, step=args.grid_step)
    # 前後兩半交叉（依 as-of 日期切）
    halves = {}
    if samples:
        dates = sorted({s["date"] for s in samples})
        mid = dates[len(dates) // 2] if dates else None
        first = [s for s in samples if s["date"] < mid]
        second = [s for s in samples if s["date"] >= mid]
        h1 = bt.grid_search_weights(first, step=args.grid_step)
        h2 = bt.grid_search_weights(second, step=args.grid_step)
        halves = {"first": h1.get("best"), "second": h2.get("best")}
    path = write_report(args, samples, meta, res, halves)
    print(f"報告：{path}")
    if res.get("best"):
        b = res["best"]
        print(f"建議權重：籌碼{b['w']['chip']:.0%}/結構{b['w']['struct']:.0%}/基本面{b['w']['fund']:.0%}"
              f"（IC {b['ic']}，樣本 {meta['samples']}）")


if __name__ == "__main__":
    main()
