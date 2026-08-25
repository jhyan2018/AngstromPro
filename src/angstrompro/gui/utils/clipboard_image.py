"""Helpers for publishing bitmap-backed SVG images to the clipboard."""

from __future__ import annotations

import base64
import re

from angstrompro.utils.qt_compat import QtCore, QtWidgets


_WRITE_ONLY = (
    QtCore.QIODevice.OpenModeFlag.WriteOnly
    if hasattr(QtCore.QIODevice, "OpenModeFlag")
    else QtCore.QIODevice.WriteOnly
)

_SVG_FONT_SIZE_PX = re.compile(
    rb"(font-size:\s*)([0-9]+(?:\.[0-9]+)?)px\b"
)
_SVG_TEXT = re.compile(
    rb"<text\b(?P<attrs>[^>]*)>.*?</text>", re.DOTALL
)
_SVG_TSPAN = re.compile(rb"<tspan\b[^>]*>", re.DOTALL)
_SVG_COORD = re.compile(
    rb'\b(?P<name>x|y|dx|dy)="(?P<value>[0-9.eE+-]+)"'
)


def pixmap_png_bytes(pixmap) -> bytes:
    """Encode a QPixmap as PNG bytes without touching the filesystem."""
    encoded = QtCore.QByteArray()
    buffer = QtCore.QBuffer(encoded)
    if not buffer.open(_WRITE_ONLY) or not pixmap.save(buffer, "PNG"):
        raise ValueError("Could not encode clipboard bitmap as PNG")
    buffer.close()
    return bytes(encoded)


def raster_svg_bytes(pixmap) -> bytes:
    """Wrap a raster QPixmap in an SVG document at its native pixel size."""
    image = pixmap.toImage()
    width = image.width()
    height = image.height()
    encoded = base64.b64encode(pixmap_png_bytes(pixmap)).decode("ascii")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'  <image width="{width}" height="{height}" '
        f'xlink:href="data:image/png;base64,{encoded}"/>\n'
        '</svg>\n'
    ).encode("utf-8")


def _powerpoint_font_sizes(svg: bytes) -> bytes:
    return _SVG_FONT_SIZE_PX.sub(
        lambda match: (
            match.group(1)
            + format(float(match.group(2)) * 4.0 / 3.0, ".8g").encode("ascii")
            + b"px"
        ),
        svg,
    )


def _first_coordinate(attrs: bytes, name: bytes) -> float:
    match = re.search(
        rb"\b" + name + rb'="([0-9.eE+-]+)', attrs
    )
    return float(match.group(1)) if match is not None else 0.0


def svg_text_for_powerpoint(svg: bytes) -> bytes:
    """Keep editable SVG text the same size through PowerPoint conversion.

    Office converts SVG px to 0.75 pt. Each text element therefore uses a
    compensated font size inside an inverse local transform. The two cancel
    while rendering; Convert to Shape retains the font size and bakes the
    transform into the text box geometry.
    """
    scale = 4.0 / 3.0
    inverse = 1.0 / scale

    def convert_text(match: re.Match[bytes]) -> bytes:
        original = match.group(0)
        converted = _powerpoint_font_sizes(original)
        if converted == original:
            return original

        attrs = match.group("attrs")
        anchor_x = _first_coordinate(attrs, b"x")
        anchor_y = _first_coordinate(attrs, b"y")

        # MathText uses individually positioned tspans. Expand those offsets
        # before the inverse group scale so their original spacing survives.
        def convert_tspan(tspan_match: re.Match[bytes]) -> bytes:
            def convert_coordinate(coord_match: re.Match[bytes]) -> bytes:
                name = coord_match.group("name")
                value = float(coord_match.group("value"))
                if name == b"x":
                    value = anchor_x + (value - anchor_x) * scale
                elif name == b"y":
                    value = anchor_y + (value - anchor_y) * scale
                else:
                    value *= scale
                return (
                    name + b'="' + format(value, ".10g").encode("ascii") + b'"'
                )

            return _SVG_COORD.sub(convert_coordinate, tspan_match.group(0))

        converted = _SVG_TSPAN.sub(convert_tspan, converted)
        translate_x = anchor_x * (1.0 - inverse)
        translate_y = anchor_y * (1.0 - inverse)
        transform = (
            b'<g transform="matrix('
            + format(inverse, ".10g").encode("ascii")
            + b" 0 0 " + format(inverse, ".10g").encode("ascii")
            + b" " + format(translate_x, ".10g").encode("ascii")
            + b" " + format(translate_y, ".10g").encode("ascii")
            + b')">'
        )
        return transform + converted + b"</g>"

    return _SVG_TEXT.sub(convert_text, svg)


def set_svg_with_bitmap_fallback(svg: bytes, fallback_pixmap) -> None:
    """Publish SVG plus PNG/native-image fallbacks to the system clipboard."""
    mime = QtCore.QMimeData()
    mime.setData("image/svg+xml", QtCore.QByteArray(svg))
    mime.setData("image/png", QtCore.QByteArray(pixmap_png_bytes(fallback_pixmap)))
    mime.setImageData(fallback_pixmap.toImage())
    QtWidgets.QApplication.clipboard().setMimeData(mime)
