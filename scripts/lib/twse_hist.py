"""TWSE T86（三大法人買賣超）逐日抓取＋解析＋磁碟快取。"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess

T86_URL = ("https://www.twse.com.tw/rwd/zh/fund/T86"
           "?date={date}&selectType=ALLBUT0999&response=json")


def parse_t86(payload: dict) -> dict:
    """TWSE T86 JSON → {4碼證券代號: 三大法人買賣超淨額股數}。非交易日/空回 {}。"""
    if not payload or payload.get("stat") != "OK":
        return {}
    out = {}
    for row in payload.get("data") or []:
        code = (row[0] or "").strip()
        if not re.fullmatch(r"\d{4}", code):
            continue
        try:
            out[code] = int(str(row[-1]).replace(",", ""))
        except (ValueError, IndexError):
            continue
    return out


def _curl(url: str) -> str:
    return subprocess.run(
        ["curl", "-s", "--http1.1", "-4", "--max-time", "25", url],
        capture_output=True, text=True, timeout=40).stdout


def fetch_t86_cached(date: str, cache_dir, get=_curl) -> dict:
    """先讀快取，無則抓 TWSE、存快取再回。date=YYYYMMDD。"""
    cache_dir = pathlib.Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = cache_dir / f"t86-{date}.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    try:
        raw = get(T86_URL.format(date=date))
        payload = json.loads(raw) if raw else None
    except Exception:
        payload = None
    # 抓取/解析失敗（payload None）→ 不快取，下次重試，避免把「網路失敗」誤存成
    # 「非交易日空白」永久污染。只有拿到可解析回應（stat OK 或官方回非交易日）才快取。
    if payload is None:
        return {}
    parsed = parse_t86(payload)
    fp.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
    return parsed
