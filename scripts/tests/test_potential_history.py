from scripts.lib import potential_history as ph


# --- Task 2: update_history ---
def test_update_history_new_and_streak():
    h = {}
    h = ph.update_history(h, [{"code": "2603", "name": "長榮", "score": 80}], "2026-07-01")
    assert h["stocks"]["2603"]["streak"] == 1
    assert h["stocks"]["2603"]["first_date"] == "2026-07-01"
    h = ph.update_history(h, [{"code": "2603", "name": "長榮", "score": 82}], "2026-07-02")
    assert h["stocks"]["2603"]["streak"] == 2
    assert h["last_date"] == "2026-07-02"


def test_update_history_idempotent_same_date():
    h = ph.update_history({}, [{"code": "2603", "name": "長榮", "score": 80}], "2026-07-01")
    h2 = ph.update_history(h, [{"code": "2603", "name": "長榮", "score": 80}], "2026-07-01")
    assert h2["stocks"]["2603"]["streak"] == 1  # 同日重跑不累加


def test_update_history_reset_after_gap():
    h = ph.update_history({}, [{"code": "2603", "name": "長榮", "score": 80}], "2026-07-01")
    h = ph.update_history(h, [{"code": "1216", "name": "統一", "score": 60}], "2026-07-02")
    h = ph.update_history(h, [{"code": "2603", "name": "長榮", "score": 70}], "2026-07-03")
    assert h["stocks"]["2603"]["streak"] == 1
    assert h["stocks"]["2603"]["first_date"] == "2026-07-03"


# --- Task 3: detect_breakouts ---
def test_detect_breakouts_flags_onboard_surge():
    h = {"last_date": "2026-07-02", "stocks": {
        "2603": {"name": "長榮", "streak": 3, "first_date": "2026-06-30",
                 "last_date": "2026-07-02", "last_score": 80},
    }}
    radar = [{"code": "2603", "name": "長榮", "pct": 6.2},
             {"code": "1216", "name": "統一", "pct": 5.0}]  # 1216 沒在榜→不提醒
    cfg = {"track_days": 5, "breakout_pct": 4.5}
    alerts = ph.detect_breakouts(h, radar, "2026-07-03", cfg)
    assert [a["code"] for a in alerts] == ["2603"]
    assert h["stocks"]["2603"]["alerted_date"] == "2026-07-03"
    # 再跑同日不重覆提醒
    assert ph.detect_breakouts(h, radar, "2026-07-03", cfg) == []


def test_update_history_keeps_score_parts():
    h = ph.update_history({}, [{"code": "2603", "name": "長榮", "score": 80,
                                "score_parts": {"chip": 60, "struct": 70, "theme": 50, "fund": 40}}],
                          "2026-07-01")
    assert h["stocks"]["2603"]["last_parts"]["chip"] == 60


def test_detect_breakouts_liquidity_floor():
    h = {"last_date": "2026-07-02", "stocks": {
        "9999": {"name": "小型股", "last_date": "2026-07-02"}}}
    radar = [{"code": "9999", "name": "小型股", "pct": 8.0, "value_yi": 0.5}]  # 漲夠但沒量
    cfg = {"track_days": 5, "breakout_pct": 4.5, "min_value_yi": 2.0}
    assert ph.detect_breakouts(h, radar, "2026-07-03", cfg) == []  # 量不足→不提醒
    radar2 = [{"code": "9999", "name": "小型股", "pct": 8.0, "value_yi": 5.0}]  # 有量
    assert [a["code"] for a in ph.detect_breakouts(h, radar2, "2026-07-03", cfg)] == ["9999"]
