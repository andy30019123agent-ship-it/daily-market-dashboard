"""一次性（或需要時重跑）回填台股加權指數歷史，供 regime.py 算 MA20/MA60。

用法：python -m scripts.backfill_index_history [--months N]
預設回填 8 個月（約 130+ 個交易日，滿足 MA60 需求）。可重複執行：採日期去重合併，
不會製造重複資料；之後每日 fetch_hard_data.py 會自動把當天收盤併入同一份檔案。
"""
import argparse

from scripts.fetch_hard_data import get_json
from scripts.lib.index_history import HISTORY_PATH, backfill, load_history, merge_entries, save_history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=8, help="往回回填幾個月（預設 8）")
    args = ap.parse_args()

    existing = load_history()
    fetched = backfill(get_json, months_back=args.months)
    merged = merge_entries(existing, fetched)
    save_history(merged)
    print(f"✅ 已寫入 {HISTORY_PATH}：共 {len(merged)} 個交易日"
          f"（原有 {len(existing)}、本次抓到 {len(fetched)}）")
    if merged:
        print(f"範圍：{merged[0]['date']} ~ {merged[-1]['date']}")


if __name__ == "__main__":
    main()
