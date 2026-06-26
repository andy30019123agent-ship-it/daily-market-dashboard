import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.lib.sanity import (  # noqa: E402
    check_consistency,
    check_news_consistency,
    collect_warnings,
)


def _day(featured, **extra):
    d = {"overview": {"tw": {"featured": featured}, "us": [1, 2, 3, 4]},
         "hot_stocks": {"tw": [{"code": "2330"}]},
         "sectors": {"tw": {"in": [{"name": "半導體"}]}}}
    d.update(extra)
    return d


def test_consistency_catches_sign_mismatch():
    # 本次事故：點數說跌(-1057)、漲跌幅卻是正(+2.24)
    day = _day({"close": 46043.6, "change": -1057.05, "change_pct": 2.24,
                "spark": [47100.65, 46043.6]})
    errs = check_consistency(day)
    assert errs and any("正負不一致" in e for e in errs)


def test_consistency_passes_clean_up_day():
    day = _day({"close": 47100.65, "change": 587.81, "change_pct": 1.28,
                "spark": [46000.0, 46512.84, 47100.65]})
    assert check_consistency(day) == []


def test_consistency_passes_clean_down_day():
    # 真正下跌日（點數負、漲跌幅負）應通過
    day = _day({"close": 46043.6, "change": -1057.05, "change_pct": -2.24,
                "spark": [47100.65, 46043.6]})
    assert check_consistency(day) == []


def test_collect_warnings_flags_empty_sections():
    day = _day({"close": 46043.6, "change": -1057.05, "change_pct": -2.24},
               hot_stocks={"tw": []})  # 熱門股空
    warns = collect_warnings(day)
    assert "台股熱門個股" in warns


def test_collect_warnings_clean():
    day = _day({"close": 46043.6, "change": -1057.05, "change_pct": -2.24})
    assert collect_warnings(day) == []


def test_news_consistency_catches_up_news_on_down_day():
    # 本次事故：大跌日(-2.24%)卻混進「台積電…收最高」(別天的上漲新聞)
    day = _day({"close": 46043.6, "change": -1057.05, "change_pct": -2.24},
               news=[{"tag": "pos", "title": "台股盤後：台積電拉尾盤收最高45809點"}])
    errs = check_news_consistency(day)
    assert errs and "方向矛盾" in errs[0]


def test_news_consistency_catches_down_news_on_up_day():
    day = _day({"close": 47100.65, "change": 587.81, "change_pct": 1.34},
               news=[{"tag": "neg", "title": "台股加權暴跌千點"}])
    assert check_news_consistency(day)


def test_news_consistency_passes_aligned_down_day():
    # 大跌日配下跌新聞 → 通過
    day = _day({"close": 46043.6, "change": -1057.05, "change_pct": -2.24},
               news=[{"tag": "neg", "title": "台股連跌3天近3000點，守住4萬3"}])
    assert check_news_consistency(day) == []


def test_news_consistency_ignores_non_tw_news():
    # 美股創新高的新聞不該被台股加權方向誤殺
    day = _day({"close": 46043.6, "change": -1057.05, "change_pct": -2.24},
               news=[{"tag": "pos", "title": "美股三大指數同步創新高"}])
    assert check_news_consistency(day) == []
