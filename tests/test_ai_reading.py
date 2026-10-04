import json


import pytest

from excel_visualization_pipeline.ai import OutputValidator
from excel_visualization_pipeline.ai.reading import plain_text
from test_ai_synthesis import model_value, snapshot


def test_shared_phases_explain_the_full_series_without_daily_dump():
    value = snapshot([16, 8, 10, 8, 19, 43, 32, 22, 22])
    report = value["synthesis"]["reading"]
    assert len(report["phases"]) == 4
    assert "có cả lần tăng và giảm" in report["overview"]["text"]
    assert "giữ nguyên" in report["overview"]["text"]
    assert [p["start"] for p in report["phases"]] == ["2026-09-01", "2026-09-04", "2026-09-06", "2026-09-08"]
    assert "tăng từ 8 lên 43" in report["phases"][1]["text"]
    assert "giảm từ 43 xuống 22" in report["phases"][2]["text"]
    assert "giữ nguyên ở 22" in report["phases"][3]["text"]
    ids = {f["factId"] for f in value["facts"]}
    evidence = {e["evidenceId"] for e in value["evidence"]}
    assert set(report["overview"]["factIds"]) <= ids
    for phase in report["phases"]:
        assert set(phase["factIds"]) <= ids
        assert set(phase["evidenceIds"]) <= evidence
        assert all(label in phase["text"] for label in ("Báo sai/Lỗi", "% báo sai"))
    assert "Tổng số giữ nguyên" in report["overview"]["text"]


def test_shared_phases_never_bridge_missing_data():
    value = snapshot([16, 8, None, 19, 43, 32, 22, 22])
    report = value["synthesis"]["reading"]
    assert "các đoạn có dữ liệu" in report["overview"]["text"]
    # The complete Total series may span the missing Error period, but cannot
    # smuggle Error observations into that shared continuous phase.
    assert all(not any(ref.startswith("error:") for ref in p["factIds"])
               for p in report["phases"] if p["start"] < "2026-09-03" < p["end"])


@pytest.mark.parametrize("errors,totals", [
    ([10, 15], [100, 200]), ([10, 10], [100, 200]), ([20, 15], [200, 100]),
    ([10, 20], [100, 200]),
])
def test_short_reading_has_joint_explanation_without_quality_or_cause(errors, totals):
    value = snapshot(errors, totals)
    report = value["synthesis"]["reading"]
    assert "chưa xác định xu hướng" in report["overview"]["text"]
    assert len(report["phases"]) == 1 and report["phases"][0]["explanation"]
    text = " ".join([report["overview"]["text"], *[p["text"] + p["explanation"] for p in report["phases"]], *[t["text"] for t in report["takeaways"]]])
    assert all(term not in text for term in ("chất lượng", "volume", "toàn khoảng", "correlation"))
    assert OutputValidator().validate(json.dumps(model_value(value)), value).valid


def test_other_metric_direction_uses_inside_periods_not_only_endpoints():
    report = snapshot([5, 10, 15, 20], [100, 200, 80, 250])["synthesis"]["reading"]
    assert "Tổng số có cả lần tăng và giảm" in report["phases"][0]["text"]
    assert "Tổng số tăng từ 100" not in report["phases"][0]["text"]


def test_plain_language_keeps_named_subjects_and_short_sentences():
    assert plain_text("chỉ số tăng trong toàn khoảng; tỷ trọng lỗi giảm.", "Báo sai/Lỗi") == "Báo sai/Lỗi tăng trong thời gian đã chọn. Tỷ lệ báo sai giảm."

def test_plain_paraphrase_keeps_the_same_closed_grammar():
    value = snapshot([16, 8, 10, 8, 19, 43, 32, 22, 22])
    output = model_value(value)
    output["claims"][0]["text"] = "Báo sai/Lỗi: đà tăng tới đỉnh đã đảo chiều. Báo sai/Lỗi giảm sau khi đạt đỉnh. Các kỳ cuối giữ nguyên."
    assert OutputValidator().validate(json.dumps(output), value).valid
    output["claims"][0]["text"] += " Chất lượng tốt hơn."
    assert not OutputValidator().validate(json.dumps(output), value).valid

