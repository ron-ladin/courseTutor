import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st

from travel_agent.planner import compute_raw_score, normalize_scores


tag = st.text(min_size=1, max_size=12).filter(lambda value: bool(value.strip()))


@given(st.lists(tag, max_size=20), st.lists(tag, max_size=10))
def test_compute_raw_score_counts_overlapping_tags(item_tags, user_style):
    # Implementation uses set intersection (unique overlapping tags)
    expected = float(len(set(item_tags) & set(user_style)))

    assert compute_raw_score(item_tags, user_style) == expected


@given(
    st.lists(
        st.floats(
            min_value=-1_000_000,
            max_value=1_000_000,
            allow_nan=False,
            allow_infinity=False,
            width=32,
        ),
        min_size=2,
        max_size=10,
        unique=True,
    )
)
def test_normalize_scores_maps_min_to_zero_and_max_to_one(scores):
    normalized = normalize_scores(scores)

    assert min(normalized) == pytest.approx(0.0)
    assert max(normalized) == pytest.approx(1.0)


def test_normalize_scores_returns_one_when_all_scores_equal():
    assert normalize_scores([4.0, 4.0, 4.0]) == [1.0, 1.0, 1.0]
