import json
from pathlib import Path

import pandas as pd
import pytest

from excel_visualization_pipeline.overview_summary import build_overview_summary, build_statistics_summary, count_issues
from excel_visualization_pipeline.date_ranges import aggregation_period_ranges


def entities(project="P"):
    return pd.DataFrame([
        {"project_label": project, "entity_id": ref, "parent_entity_id": parent,
         "entity_level": level, "entity_label": ref, "effective_unit": "Lượt"}
        for ref, parent, level in [("root", None, "project"), ("group", "root", "section"),
                                  ("a", "group", "item"), ("b", "group", "item"),
                                  ("sub", "a", "subitem")]
    ])


def frame(ref="root", values=(10, 20, 15), dates=None, kind="numeric", project="P"):
    dates = pd.date_range("2026-09-07", periods=len(values)) if dates is None else dates
    return pd.DataFrame([
        {"project_label": project, "entity_id": ref, "parent_entity_id": None if ref == "root" else "group",
         "entity_level": "project" if ref == "root" else "item", "entity_label": ref,
         "effective_unit": "Lượt", "date": pd.Timestamp(day), "chart_value": value,
         "value_kind": kind if value is not None else "not_recorded", "validation_status": "valid",
         "metric_normalized": "Tổng số"}
        for day, value in zip(dates, values)
    ])


POLICY = {"policyVersion": "test-v1", "projects": {"P": {"default": "a", "sources": ["a", "b"]}}}


def summarize(data, start="2026-09-07", end="2026-09-09", grain="day", source=None, hierarchy=None):
    return build_overview_summary(data, entities() if hierarchy is None else hierarchy, "P", start, end, grain, POLICY, source)


def statistics_summary(data, grain="week", mode="sum", periods=None):
    periods = aggregation_period_ranges(pd.to_datetime(data.date).dt.date, grain) if periods is None else periods
    dates = pd.to_datetime(data.date)
    start = max(periods[0].start, dates.min().date()) if periods else None
    end = min(periods[-1].end, dates.max().date()) if periods else None
    return build_statistics_summary(data, entities(), "P", start, end, grain, periods, mode, POLICY)


@pytest.mark.parametrize("mode,peak,low,delta,unit", [
    ("sum", 140, 70, 70, "Lượt"), ("both", 140, 70, 70, "Lượt"),
    ("average", 20, 10, 10, "Lượt/ngày"),
])
def test_statistics_cards_match_canonical_sum_average_and_both(mode, peak, low, delta, unit):
    result = statistics_summary(frame("a", [10] * 7 + [20] * 7), mode=mode)
    assert result["issueCount"]["value"] == 1
    assert result["peak"]["value"] == peak
    assert result["lowest"]["value"] == low
    assert result["largestChange"]["absolute"] == delta
    assert result["largestChange"]["relativePercent"] == 100
    assert result["peak"]["unit"] == result["largestChange"]["unit"] == unit
    assert result["requestedMode"] == mode


@pytest.mark.parametrize("grain", ["day", "week", "month", "quarter"])
def test_statistics_grains_reuse_original_calculation(grain):
    from excel_visualization_pipeline.visualization import prepare_period_statistics
    data = frame("a", [10] * 92, dates=pd.date_range("2026-07-01", periods=92))
    original = prepare_period_statistics(data, "2026-07-01", "2026-09-30", grain, coverage_data=data, semantic_data=data)
    for mode, column in [("sum", "period_sum"), ("average", "average_per_day")]:
        result = statistics_summary(data, grain=grain, mode=mode)
        assert result["peak"]["value"] == original[column].max()
        assert result["lowest"]["value"] == original[column].min()


def test_statistics_missing_days_use_eligible_days_not_calendar_days():
    result = statistics_summary(frame("a", [10, None, 20]), mode="average")
    assert result["peak"]["value"] == 15
    assert result["peak"]["period"]["eligibleDayCount"] == 2
    assert result["peak"]["period"]["complete"] is False
    assert result["largestChange"]["status"] == "insufficient_data"


def test_statistics_marker_inherited_coverage_and_zero_are_not_conflated():
    data = pd.concat([frame("group", [10, 20]), frame("a", [None, None], kind="source_marker")])
    data.loc[data.entity_id.eq("a"), "value_kind"] = "source_marker"
    result = statistics_summary(data, mode="average")
    assert result["peak"]["status"] == "no_data"
    assert result["issueCount"]["value"] == 0
    assert statistics_summary(frame("a", [0, 0]), mode="average")["peak"]["value"] == 0


def test_statistics_selected_periods_determine_count_and_do_not_join_calendar_gaps():
    data = pd.concat([frame("a", [10, 20], dates=pd.to_datetime(["2026-09-07", "2026-09-09"])),
                      frame("b", [30], dates=pd.to_datetime(["2026-09-08"]))])
    periods = aggregation_period_ranges(pd.to_datetime(["2026-09-07", "2026-09-09"]).date, "day")
    result = statistics_summary(data, grain="day", periods=periods)
    assert result["issueCount"]["value"] == 1
    assert result["expectedPeriodCount"] == 2
    assert result["largestChange"]["status"] == "insufficient_data"
    empty = statistics_summary(data, periods=[])
    assert empty["window"] is None
    assert empty["issueCount"]["status"] == empty["peak"]["status"] == "no_data"


def test_counts_distinct_owned_issues_and_physical_zero():
    data = pd.concat([frame("a", [0, 1]), frame("sub", [2, 3]), frame("b", [0]), frame("group", [100]), frame("root", [100])])
    assert count_issues(data, entities())["value"] == 2


@pytest.mark.parametrize("kind", ["not_recorded", "source_marker", "text", "default_zero_rate"])
def test_non_source_numeric_kinds_do_not_count(kind):
    assert count_issues(frame("a", [0], kind=kind), entities())["value"] == 0


def test_count_excludes_invalid_non_finite_and_out_of_window_project():
    data = pd.concat([frame("a", [1, float("inf"), None]), frame("b", [2], project="Other")])
    data.loc[data.entity_id.eq("a"), "validation_status"] = "error"
    assert summarize(data)["issueCount"]["value"] == 0


def test_prefers_root_and_requires_approved_source():
    data = pd.concat([frame(), frame("a", [100, 200])])
    result = summarize(data)
    assert result["scope"] == "project"
    assert result["source"]["entityRef"] == "root"
    with pytest.raises(ValueError):
        summarize(data, source="a")


def test_named_source_is_not_claimed_to_be_project_total():
    data = pd.concat([frame("a"), frame("b", [50])])
    result = summarize(data, source="b")
    assert result["scope"] == "source"
    assert result["source"]["entityRef"] == "b"
    assert result["issueCount"]["value"] == 2
    with pytest.raises(ValueError):
        summarize(data, source="sub")


def test_missing_unit_and_cumulative_sources_fail_closed():
    for unit in [None, "Lượt (lũy kế)"]:
        hierarchy = entities()
        hierarchy.loc[hierarchy.entity_id.isin(["a", "b"]), "effective_unit"] = unit
        result = summarize(frame("a"), hierarchy=hierarchy)
        assert result["source"] is None
        assert result["peak"]["status"] == "unavailable"


def test_unknown_project_does_not_sum_child_sources():
    result = build_overview_summary(frame("a"), entities(), "P", "2026-09-07", "2026-09-09", "day", {"policyVersion": "v1", "projects": {}})
    assert result["source"] is None
    assert result["issueCount"]["value"] == 1


def test_committed_mapping_covers_all_approved_named_sources():
    policy = json.loads((Path(__file__).parents[1] / "config/overview-sources.json").read_text(encoding="utf-8"))
    assert set(policy["projects"]) == {"VSO", "ANVF", "V-Pet"}
    assert len(policy["projects"]["ANVF"]["sources"]) == 3
    assert policy["projects"]["V-Pet"]["sources"] == ["canh-bao-vi-pham-f62756dca4eb"]


def test_extrema_zero_missing_single_and_latest_tie():
    result = summarize(frame(values=[0, None, 0]))
    assert result["peak"]["value"] == result["lowest"]["value"] == 0
    assert result["peak"]["tieCount"] == 2
    assert result["peak"]["period"]["start"] == "2026-09-09"
    single = summarize(frame(values=[12]))
    assert single["peak"]["value"] == single["lowest"]["value"] == 12
    missing = summarize(frame(values=[None, None]))
    assert missing["peak"]["status"] == "no_data"  # Approved source exists, but has no values.


@pytest.mark.parametrize("grain", ["week", "month"])
def test_grouped_extrema_matches_existing_total_sum(grain):
    from excel_visualization_pipeline.visualization import prepare_period_metric_summary
    data = frame(values=[10, None, 20])
    result = summarize(data, grain=grain)
    original = prepare_period_metric_summary(data, "2026-09-07", "2026-09-09", grain)
    assert result["peak"]["value"] == result["lowest"]["value"] == original.iloc[0].total_sum == 30
    assert result["peak"]["period"]["complete"] is False
    assert result["peak"]["period"]["observedDayCount"] == 2
    assert result["peak"]["inferredZero"] is False


def test_range_is_inclusive_and_source_selection_does_not_change_issue_count():
    data = pd.concat([frame("a", [10, 20, 30]), frame("b", [100, 200, 300])])
    first = summarize(data, start="2026-09-08", source="a")
    second = summarize(data, start="2026-09-08", source="b")
    assert first["lowest"]["value"] == 20
    assert second["lowest"]["value"] == 200
    assert first["issueCount"] == second["issueCount"]


def test_orphans_cycles_and_retired_default_are_not_guessed():
    hierarchy = entities()
    hierarchy.loc[hierarchy.entity_id.eq("a"), "parent_entity_id"] = "a"
    hierarchy.loc[hierarchy.entity_id.eq("b"), "parent_entity_id"] = "unknown"
    result = count_issues(pd.concat([frame("a"), frame("b")]), hierarchy)
    assert result["value"] == 0
    assert result["excludedCount"] == 2
    result = summarize(frame("b"), hierarchy=entities()[~entities().entity_id.eq("a")])
    assert result["source"] is None


def test_largest_change_ranks_absolute_not_relative_with_latest_tie():
    change = summarize(frame(values=[1, 10, 50]))["largestChange"]
    assert change["absolute"] == 40
    assert change["from"]["value"] == 10
    assert change["relativePercent"] == 400
    change = summarize(frame(values=[10, 20, 10]))["largestChange"]
    assert change["absolute"] == -10
    assert change["to"]["period"]["start"] == "2026-09-09"
    assert change["tieCount"] == 2


def test_change_never_crosses_missing_day_and_preserves_zero_baseline():
    result = summarize(frame(values=[10, None, 100]))
    assert result["peak"]["value"] == 100
    assert result["largestChange"]["status"] == "insufficient_data"
    change = summarize(frame(values=[0, 10]))["largestChange"]
    assert change["absolute"] == 10
    assert change["relativePercent"] is None
    assert "bằng 0" in change["relativeReason"]
    change = summarize(frame(values=[0, 0, 0]))["largestChange"]
    assert change["status"] == "ready"
    assert change["direction"] == "unchanged"


@pytest.mark.parametrize("grain,start,end", [("week", "2026-09-07", "2026-09-27"), ("month", "2026-07-01", "2026-09-30")])
def test_calendar_pairs_grouped_and_boundary_exclusion(grain, start, end):
    dates = pd.date_range(start, end)
    data = frame(values=list(range(1, len(dates) + 1)), dates=dates)
    full = summarize(data, start, end, grain)
    assert full["largestChange"]["eligiblePairCount"] == 2
    clipped = summarize(data, str((dates[0] + pd.Timedelta(days=1)).date()), str((dates[-1] - pd.Timedelta(days=1)).date()), grain)
    assert clipped["largestChange"]["status"] == "insufficient_data"


def test_no_ai_sixty_period_limit_and_missing_calendar_periods_are_retained():
    dates = pd.date_range("2026-01-01", periods=100)
    data = frame(values=[1] * 100, dates=dates)
    result = summarize(data, str(dates[0].date()), str(dates[-1].date()))
    assert result["validPeriodCount"] == 100
    assert result["largestChange"]["eligiblePairCount"] == 99
    assert result["peak"]["period"]["start"] == str(dates[-1].date())
