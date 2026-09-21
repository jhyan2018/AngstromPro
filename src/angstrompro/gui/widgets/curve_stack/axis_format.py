"""Shared scientific-axis formatting for curve displays."""

from __future__ import annotations


def scientific_scalar_formatter():
    """Return a formatter with a visible shared power-of-ten multiplier."""
    from matplotlib.ticker import ScalarFormatter

    formatter = ScalarFormatter(useMathText=False)
    formatter.set_scientific(True)
    formatter.set_powerlimits((-3, 3))
    # Avoid a second, additive offset such as ``+1e6``.  The multiplicative
    # scientific exponent remains visible beside the axis.
    formatter.set_useOffset(False)
    return formatter


def apply_scientific_y_formatter(ax) -> None:
    """Use one explicit scientific exponent for a linear Y axis."""
    if ax is None or ax.get_yscale() != "linear":
        return
    ax.yaxis.set_major_formatter(scientific_scalar_formatter())


def apply_scientific_colorbar_formatter(colorbar) -> None:
    """Use the same explicit exponent convention on a signal colorbar."""
    if colorbar is None:
        return
    colorbar.formatter = scientific_scalar_formatter()
    colorbar.update_ticks()
