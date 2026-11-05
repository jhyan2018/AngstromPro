from __future__ import annotations

import os
import subprocess
import sys


def test_math_label_renders_scientific_notation_without_font_warning():
    # Keep Qt application lifetime isolated from the other GUI tests. Some Qt
    # bindings cannot safely create/destroy multiple QApplication instances in
    # one process, while this widget specifically needs a real QPixmap.
    code = """
from angstrompro.gui.modules.planewave_synthesiser import _SYNTHESIS_EQUATION
from angstrompro.gui.widgets.math_label import MathLabel
from angstrompro.utils.qt_compat import QtWidgets

app = QtWidgets.QApplication([])
label = MathLabel(_SYNTHESIS_EQUATION)
label.resize(320, label.sizeHint().height())
assert label.math_text == _SYNTHESIS_EQUATION
assert label.render_error is None
assert not label._pixmap.isNull()
label.close()
"""
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "findfont" not in result.stderr.lower()
