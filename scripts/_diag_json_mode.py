"""一次性診斷：Responses API + web_search 下，模型輸出能不能穩定 parse 成 JSON。

跑兩種請求各一次，把「原始輸出」與「parse 結果」都印出來：
  A. 不指定格式（現況）
  B. text.format = json_object（強制合法 JSON；官方文件未載明能否與 web_search 併用，實測才知道）
用完即刪。
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_soft_openai as g  # noqa: E402

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "public" / "data"
KEY = os.environ["OPENAI_API_KEY"]
partial = json.loads(sorted(DATA_DIR.glob("*.partial.json"))[-1].read_text(encoding="utf-8"))
PROMPT = g.PROMPT.format(hard=g._hard_context(partial))


def call(label, extra):
    body = {"model": g.MODEL, "tools": [{"type": "web_search"}], "input": PROMPT}
    body.update(extra)
    req = urllib.request.Request(
        g.API, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    print(f"\n{'='*70}\n### {label}\n{'='*70}")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}：{g._scrub(e.read().decode('utf-8', 'replace')[:600])}")
        return
    text = g._responses_text(resp)
    print(f"--- 原始輸出前 700 字 ---\n{text[:700]}")
    print(f"--- 原始輸出後 300 字 ---\n{text[-300:]}")
    try:
        d = g._extract_json(text)
        print(f"✅ parse 成功：news {len(d.get('news', []))} 則、"
              f"台股 {d.get('verdict', {}).get('tw', {}).get('stance')}")
    except Exception as e:
        print(f"❌ parse 失敗：{type(e).__name__}: {e}")
        if isinstance(e, json.JSONDecodeError):
            lo, hi = max(0, e.pos - 200), e.pos + 200
            print(f"--- 出錯位置 char {e.pos} 前後 ---\n{text[lo:hi]}")


call("A. 不指定格式（現況）", {})
call("B. text.format = json_object", {"text": {"format": {"type": "json_object"}}})
