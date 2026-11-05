from __future__ import annotations

import numpy as np
import pytest

from angstrompro.gui.widgets.general.NumberExpression import NumberExpression


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (float("nan"), "nan"),
        (np.float64("nan"), "nan"),
        (float("inf"), "inf"),
        (float("-inf"), "-inf"),
    ],
)
def test_float_to_simplified_number_handles_non_finite_values(
    value: float,
    expected: str,
) -> None:
    assert NumberExpression.float_to_simplified_number(value) == expected


def test_float_to_simplified_number_keeps_si_prefix_formatting() -> None:
    assert NumberExpression.float_to_simplified_number(1.25e-3) == "1.250m"
