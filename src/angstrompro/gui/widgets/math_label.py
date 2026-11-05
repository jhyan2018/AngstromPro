"""Theme-aware scientific equation label rendered with Matplotlib MathText."""

from __future__ import annotations

import logging

import numpy as np

from angstrompro.utils.qt_compat import IS_QT6, QtCore, QtGui, QtWidgets


log = logging.getLogger(__name__)

_IMAGE_FORMAT_RGBA = (
    QtGui.QImage.Format.Format_RGBA8888
    if IS_QT6 else QtGui.QImage.Format_RGBA8888
)
_WINDOW_TEXT = (
    QtGui.QPalette.ColorRole.WindowText
    if IS_QT6 else QtGui.QPalette.WindowText
)
_EXPANDING = (
    QtWidgets.QSizePolicy.Policy.Expanding
    if IS_QT6 else QtWidgets.QSizePolicy.Expanding
)
_PREFERRED = (
    QtWidgets.QSizePolicy.Policy.Preferred
    if IS_QT6 else QtWidgets.QSizePolicy.Preferred
)
_ALIGN_CENTER = (
    QtCore.Qt.AlignmentFlag.AlignCenter if IS_QT6 else QtCore.Qt.AlignCenter
)
_TEXT_WORD_WRAP = (
    QtCore.Qt.TextFlag.TextWordWrap if IS_QT6 else QtCore.Qt.TextWordWrap
)
_SMOOTH_PIXMAP = (
    QtGui.QPainter.RenderHint.SmoothPixmapTransform
    if IS_QT6 else QtGui.QPainter.SmoothPixmapTransform
)


class MathLabel(QtWidgets.QWidget):
    """Display a Matplotlib MathText expression as scalable transparent text.

    MathText supplies familiar LaTeX-like scientific notation without requiring
    a system LaTeX installation. The foreground follows the Qt palette and the
    point size follows AngstromPro's application font.
    """

    def __init__(
        self,
        math_text: str = "",
        parent=None,
        *,
        font_scale: float = 1.1,
    ) -> None:
        super().__init__(parent)
        self._math_text = str(math_text)
        self._font_scale = max(0.5, float(font_scale))
        self._padding = 6
        self._pixmap = QtGui.QPixmap()
        self._render_error: str | None = None
        self.setSizePolicy(_EXPANDING, _PREFERRED)
        self.setAccessibleName("Scientific equation")
        self._render_math()

    @property
    def math_text(self) -> str:
        return self._math_text

    @property
    def render_error(self) -> str | None:
        return self._render_error

    def set_math_text(self, math_text: str) -> None:
        math_text = str(math_text)
        if math_text == self._math_text:
            return
        self._math_text = math_text
        self._render_math()

    def _render_math(self) -> None:
        if not self._math_text:
            self._pixmap = QtGui.QPixmap()
            self._render_error = None
            self.updateGeometry()
            self.update()
            return

        try:
            import matplotlib as mpl
            from matplotlib.font_manager import FontProperties
            from matplotlib.mathtext import MathTextParser

            point_size = self.font().pointSizeF()
            if point_size <= 0:
                point_size = 10.0
            point_size *= self._font_scale
            device_ratio = max(1.0, float(self.devicePixelRatioF()))
            dpi = max(72.0, float(self.logicalDpiY())) * device_ratio

            # STIX is bundled with Matplotlib and gives stable mathematical
            # glyphs without inheriting a possibly unavailable rcParams font.
            with mpl.rc_context({
                "font.family": "STIXGeneral",
                "mathtext.fontset": "stix",
            }):
                parsed = MathTextParser("agg").parse(
                    self._math_text,
                    dpi=dpi,
                    prop=FontProperties(
                        family="STIXGeneral",
                        size=point_size,
                    ),
                )

            alpha = np.asarray(parsed.image, dtype=np.uint8)
            height, width = alpha.shape
            colour = self.palette().color(_WINDOW_TEXT)
            rgba = np.empty((height, width, 4), dtype=np.uint8)
            rgba[..., 0] = colour.red()
            rgba[..., 1] = colour.green()
            rgba[..., 2] = colour.blue()
            rgba[..., 3] = (
                alpha.astype(np.uint16) * colour.alpha() // 255
            ).astype(np.uint8)

            image = QtGui.QImage(
                rgba.data,
                width,
                height,
                int(rgba.strides[0]),
                _IMAGE_FORMAT_RGBA,
            ).copy()
            pixmap = QtGui.QPixmap.fromImage(image)
            pixmap.setDevicePixelRatio(device_ratio)
            self._pixmap = pixmap
            self._render_error = None
        except Exception as exc:  # retain a readable fallback in the UI
            self._pixmap = QtGui.QPixmap()
            self._render_error = str(exc)
            log.warning("Could not render mathematical label: %s", exc)

        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QtCore.QSize:
        if self._pixmap.isNull():
            metrics = self.fontMetrics()
            return QtCore.QSize(240, metrics.height() * 2 + self._padding * 2)
        ratio = max(1.0, float(self._pixmap.devicePixelRatio()))
        width = round(self._pixmap.width() / ratio) + self._padding * 2
        height = round(self._pixmap.height() / ratio) + self._padding * 2
        return QtCore.QSize(width, height)

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(140, self.sizeHint().height())

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(_SMOOTH_PIXMAP, True)
        target_area = QtCore.QRectF(self.rect()).adjusted(
            self._padding,
            self._padding,
            -self._padding,
            -self._padding,
        )

        if self._pixmap.isNull():
            painter.setPen(self.palette().color(_WINDOW_TEXT))
            painter.drawText(
                target_area,
                int(_ALIGN_CENTER | _TEXT_WORD_WRAP),
                self._math_text,
            )
            return

        ratio = max(1.0, float(self._pixmap.devicePixelRatio()))
        natural_width = self._pixmap.width() / ratio
        natural_height = self._pixmap.height() / ratio
        scale = min(1.0, target_area.width() / max(1.0, natural_width))
        width = natural_width * scale
        height = natural_height * scale
        target = QtCore.QRectF(
            target_area.center().x() - width / 2,
            target_area.center().y() - height / 2,
            width,
            height,
        )
        painter.drawPixmap(target, self._pixmap, QtCore.QRectF(self._pixmap.rect()))

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        event_types = (
            QtCore.QEvent.Type.FontChange,
            QtCore.QEvent.Type.PaletteChange,
            QtCore.QEvent.Type.StyleChange,
        ) if IS_QT6 else (
            QtCore.QEvent.FontChange,
            QtCore.QEvent.PaletteChange,
            QtCore.QEvent.StyleChange,
        )
        if event.type() in event_types:
            self._render_math()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Rendering before the widget is assigned to a high-DPI screen uses the
        # default ratio. Refresh once the final screen is known.
        self._render_math()
