# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 13:11:14 2026

@author: jiahaoYan
"""
import os
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from angstrompro.utils.qt_compat import QtCore, QtWidgets, QtGui, Signal


class ColorBarPreview(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(34)
        self._data = [
            {"position": 0.0, "red": 0.0, "green": 0.0, "blue": 0.0},
            {"position": 1.0, "red": 1.0, "green": 1.0, "blue": 1.0},
        ]

    def setData(self, data):
        self._data = [dict(d) for d in data]
        self.update()

    @staticmethod
    def _clamp01(v):
        return max(0.0, min(1.0, float(v)))

    def _build_cdict(self):
        anchors = sorted(self._data, key=lambda d: d["position"])
        cdict = {"red": [], "green": [], "blue": []}
        for a in anchors:
            x = self._clamp01(a["position"])
            r, g, b = self._clamp01(a["red"]), self._clamp01(a["green"]), self._clamp01(a["blue"])
            cdict["red"].append([x, r, r])
            cdict["green"].append([x, g, g])
            cdict["blue"].append([x, b, b])
        return cdict

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing
                        if hasattr(QtGui.QPainter, "RenderHint") else QtGui.QPainter.Antialiasing)

        w    = max(2, self.width())
        rect = self.rect().adjusted(1, 1, -1, -1)

        try:
            cmap = LinearSegmentedColormap("preview_cmap", self._build_cdict(), N=512)
            xs   = np.linspace(0.0, 1.0, w)
            rgba = cmap(xs)
            rgb  = (rgba[:, :3] * 255).astype(np.uint8)

            img = QtGui.QImage(w, 1, QtGui.QImage.Format.Format_RGB888
                               if hasattr(QtGui.QImage, "Format") else QtGui.QImage.Format_RGB888)
            ptr = img.bits()
            ptr.setsize(w * 3)
            np.frombuffer(ptr, np.uint8).reshape((1, w, 3))[0, :, :] = rgb
            p.drawImage(rect, img)
        except Exception:
            p.fillRect(rect, QtGui.QColor(200, 200, 200))

        p.setPen(QtGui.QPen(QtGui.QColor(120, 120, 120), 1))
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush
                   if hasattr(QtCore.Qt, "BrushStyle") else QtCore.Qt.NoBrush)
        p.drawRoundedRect(QtCore.QRectF(rect), 4, 4)


class MultiHandleSlider(QtWidgets.QWidget):
    valuesChanged    = Signal(list)
    selectionChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.handles        = [0.0, 1.0]
        self.selected_index = -1
        self.dragging_index = -1
        self.margin   = 14
        self.track_h  = 6
        self.handle_r = 10
        self.hit_r    = 10
        self.setMinimumHeight(44)
        self.setMouseTracking(True)

    def values(self):
        return self.handles.copy()

    def setValues(self, values, keep_selected=True):
        if not values or len(values) < 2:
            return False
        vals    = sorted(max(0.0, min(1.0, float(v))) for v in values)
        vals[0] = 0.0; vals[-1] = 1.0
        self.handles = vals
        if not keep_selected:
            self.selected_index = -1
        self.update()
        self.valuesChanged.emit(self.values())
        self.selectionChanged.emit(self.selected_index)
        return True

    def selectedHandleIndex(self):
        return self.selected_index

    def setSelectedIndex(self, idx, emit_signal=True):
        if idx < -1 or idx >= len(self.handles):
            return False
        if idx != self.selected_index:
            self.selected_index = idx
            if emit_signal:
                self.selectionChanged.emit(self.selected_index)
            self.update()
        return True

    def setHandleValue(self, index, value, emit_signal=True):
        if not isinstance(index, int) or not (0 <= index < len(self.handles)):
            return False
        v = max(0.0, min(1.0, float(value)))
        if index == 0:
            if abs(v) > 1e-12: return False
            self.handles[0] = 0.0
        elif index == len(self.handles) - 1:
            if abs(v - 1.0) > 1e-12: return False
            self.handles[-1] = 1.0
        else:
            left, right = self.handles[index - 1], self.handles[index + 1]
            eps = 1e-6
            if not (left + eps < v < right - eps): return False
            self.handles[index] = v
        self.update()
        if emit_signal:
            self.valuesChanged.emit(self.values())
        return True

    def removeHandle(self, index, emit_signal=True):
        if not isinstance(index, int) or not (0 < index < len(self.handles) - 1):
            return False
        self.handles.pop(index)
        if self.selected_index == index:
            self.selected_index = min(index, len(self.handles) - 1)
            if emit_signal: self.selectionChanged.emit(self.selected_index)
        elif self.selected_index > index:
            self.selected_index -= 1
            if emit_signal: self.selectionChanged.emit(self.selected_index)
        self.update()
        if emit_signal: self.valuesChanged.emit(self.values())
        return True

    # geometry helpers
    def _track_left(self):  return self.margin
    def _track_right(self): return self.width() - self.margin
    def _track_w(self):     return max(1.0, self._track_right() - self._track_left())
    def _value_to_x(self, v): return self._track_left() + v * self._track_w()
    def _x_to_value(self, x): return max(0.0, min(1.0, (x - self._track_left()) / self._track_w()))

    def _nearest_handle_index(self, pos):
        px, py = pos.x(), pos.y()
        cy = self.height() / 2.0
        best, best_d2 = -1, (self.hit_r + 2) ** 2
        for i, v in enumerate(self.handles):
            hx = self._value_to_x(v)
            d2 = (px - hx) ** 2 + (py - cy) ** 2
            if d2 <= best_d2:
                best_d2, best = d2, i
        return best

    def _insert_sorted(self, v):
        idx = 0
        while idx < len(self.handles) and self.handles[idx] < v:
            idx += 1
        self.handles.insert(idx, v)
        return idx

    def _left_button(self):
        try: return QtCore.Qt.MouseButton.LeftButton
        except AttributeError: return QtCore.Qt.LeftButton

    def _right_button(self):
        try: return QtCore.Qt.MouseButton.RightButton
        except AttributeError: return QtCore.Qt.RightButton

    def mousePressEvent(self, event):
        idx = self._nearest_handle_index(event.pos())
        if event.button() == self._right_button():
            v = self._x_to_value(event.pos().x())
            eps = 1e-6
            if any(abs(hv - v) < eps for hv in self.handles):
                return
            new_idx = self._insert_sorted(v)
            self.setSelectedIndex(new_idx, emit_signal=True)
            self.valuesChanged.emit(self.values())
            self.update()
        elif event.button() == self._left_button():
            if idx >= 0:
                self.setSelectedIndex(idx, emit_signal=True)
                if 0 < idx < len(self.handles) - 1:
                    self.dragging_index = idx
            else:
                self.setSelectedIndex(-1, emit_signal=True)
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging_index >= 0 and (event.buttons() & self._left_button()):
            i = self.dragging_index
            v = self._x_to_value(event.pos().x())
            eps = 1e-6
            v = max(self.handles[i - 1] + eps, min(v, self.handles[i + 1] - eps))
            self.handles[i] = v
            self.valuesChanged.emit(self.values())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == self._left_button():
            self.dragging_index = -1
            self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing
                        if hasattr(QtGui.QPainter, "RenderHint") else QtGui.QPainter.Antialiasing)

        cy   = self.height() / 2.0
        left, right = self._track_left(), self._track_right()

        try: no_pen = QtCore.Qt.PenStyle.NoPen
        except AttributeError: no_pen = QtCore.Qt.NoPen

        groove = QtCore.QRectF(left, cy - self.track_h / 2, right - left, self.track_h)
        p.setPen(no_pen)
        p.setBrush(QtGui.QColor(210, 210, 210))
        p.drawRoundedRect(groove, 3, 3)

        for i, v in enumerate(self.handles):
            x    = self._value_to_x(v)
            fill = (QtGui.QColor(255, 230, 170) if i == self.selected_index
                    else QtGui.QColor(235, 235, 235) if i in (0, len(self.handles) - 1)
                    else QtGui.QColor(255, 255, 255))
            p.setPen(QtGui.QPen(QtGui.QColor(80, 80, 80), 1))
            p.setBrush(QtGui.QBrush(fill))
            p.drawEllipse(QtCore.QRectF(x - self.handle_r, cy - self.handle_r,
                                        2 * self.handle_r, 2 * self.handle_r))


class HandlerInfoPanel(QtWidgets.QWidget):
    dataChanged  = Signal(list)
    updateCdict  = Signal(list)

    def __init__(self, slider: MultiHandleSlider, colorbar: ColorBarPreview, parent=None):
        super().__init__(parent)
        self.slider   = slider
        self.colorbar = colorbar

        self.data = [
            {"position": 0.0, "red": 0.0, "green": 0.0, "blue": 0.0},
            {"position": 1.0, "red": 1.0, "green": 1.0, "blue": 1.0},
        ]

        self.lbl_idx_val = QtWidgets.QLabel("-")
        self.edit_pos = QtWidgets.QLineEdit()
        self.edit_r   = QtWidgets.QLineEdit()
        self.edit_g   = QtWidgets.QLineEdit()
        self.edit_b   = QtWidgets.QLineEdit()

        self.btn_delete    = QtWidgets.QPushButton("Delete Anchor")
        self.btn_color     = QtWidgets.QPushButton("")
        self.btn_color.setFixedSize(90, 36)
        self.btn_clipboard = QtWidgets.QPushButton("Clipboard")
        self.btn_export    = QtWidgets.QPushButton("Export")
        self.btn_update    = QtWidgets.QPushButton("Update")

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Current index:"), 0, 0)
        grid.addWidget(self.lbl_idx_val, 0, 1)
        grid.addWidget(QtWidgets.QLabel("Position:"), 1, 0)
        grid.addWidget(self.edit_pos, 1, 1)
        grid.addWidget(QtWidgets.QLabel("Red:"), 2, 0)
        grid.addWidget(self.edit_r, 2, 1)
        grid.addWidget(QtWidgets.QLabel("Green:"), 3, 0)
        grid.addWidget(self.edit_g, 3, 1)
        grid.addWidget(QtWidgets.QLabel("Blue:"), 4, 0)
        grid.addWidget(self.edit_b, 4, 1)

        btn_col = QtWidgets.QVBoxLayout()
        for btn in (self.btn_delete, self.btn_color, self.btn_clipboard,
                    self.btn_export, self.btn_update):
            btn_col.addWidget(btn)
        btn_col.addStretch(1)

        main = QtWidgets.QHBoxLayout(self)
        main.addLayout(grid, 1)
        main.addLayout(btn_col, 0)

        self.slider.valuesChanged.connect(self.on_slider_values_changed)
        self.slider.selectionChanged.connect(self.on_slider_selection_changed)
        self.edit_pos.editingFinished.connect(self.on_position_edit_finished)
        self.edit_r.editingFinished.connect(self.on_rgb_edit_finished)
        self.edit_g.editingFinished.connect(self.on_rgb_edit_finished)
        self.edit_b.editingFinished.connect(self.on_rgb_edit_finished)
        self.btn_delete.clicked.connect(self.on_delete_anchor_clicked)
        self.btn_color.clicked.connect(self.on_pick_color_clicked)
        self.btn_clipboard.clicked.connect(self.on_copy_colorbar_to_clipboard)
        self.btn_export.clicked.connect(self.on_export_colormap)
        self.btn_update.clicked.connect(self.on_update_colormap)

        self.sync_data_with_slider()
        self.refresh_widgets()
        self.dataChanged.emit([dict(d) for d in self.data])

    @staticmethod
    def _clamp01(x): return max(0.0, min(1.0, float(x)))

    def _apply_color_button_style(self, r, g, b):
        rr, gg, bb = (int(round(self._clamp01(c) * 255)) for c in (r, g, b))
        self.btn_color.setStyleSheet(
            f"QPushButton {{background-color: rgb({rr},{gg},{bb});"
            "border: 1px solid #666; border-radius: 4px;}")

    def _emit_data_changed(self):
        self.dataChanged.emit([dict(d) for d in self.data])

    def _set_current_rgb(self, r, g, b, update_lineedits=True):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)):
            return False
        r, g, b = self._clamp01(r), self._clamp01(g), self._clamp01(b)
        self.data[idx].update({"red": r, "green": g, "blue": b})
        if update_lineedits:
            for edit, v in zip((self.edit_r, self.edit_g, self.edit_b), (r, g, b)):
                with QtCore.QSignalBlocker(edit):
                    edit.setText(f"{v:.6f}")
        self._apply_color_button_style(r, g, b)
        self._emit_data_changed()
        return True

    def _build_cdict_from_data(self):
        anchors = sorted(self.data, key=lambda d: d["position"])
        cdict = {"red": [], "green": [], "blue": []}
        for a in anchors:
            x = self._clamp01(a["position"])
            r, g, b = self._clamp01(a["red"]), self._clamp01(a["green"]), self._clamp01(a["blue"])
            cdict["red"].append([x, r, r])
            cdict["green"].append([x, g, g])
            cdict["blue"].append([x, b, b])
        return cdict

    def on_export_colormap(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Colormap", "", "Text Files (*.txt);;All Files (*)")
        if not filepath:
            return
        base = os.path.splitext(os.path.basename(filepath))[0]
        if not filepath.lower().endswith(".txt"):
            filepath += ".txt"
        try:
            cmap = LinearSegmentedColormap(base, self._build_cdict_from_data(), N=4096)
            rgb  = np.clip(np.round(cmap(np.linspace(0, 1, 256))[:, :3] * 65025), 0, 65025).astype(int)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"{base}[][0]\t{base}[][1]\t{base}[][2]\n")
                for r, g, b in rgb:
                    f.write(f"{r}\t{g}\t{b}\n")
            QtWidgets.QMessageBox.information(self, "Export", f"Colormap exported:\n{filepath}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export Error", str(e))

    def on_update_colormap(self):
        self.updateCdict.emit([dict(d) for d in self.data])

    def sync_data_with_slider(self):
        vals  = self.slider.values()
        old   = self.data
        n_old, n_new = len(old), len(vals)
        eps   = 1e-9

        if n_new == n_old:
            for i in range(n_new):
                old[i]["position"] = vals[i]
            return

        if n_new == n_old + 1:
            ins = next((i for i, (nv, ov) in enumerate(zip(vals, old))
                        if abs(nv - ov["position"]) >= eps), n_new - 1)
            new_data = []
            i_old = 0
            for i_new in range(n_new):
                if i_new == ins:
                    ref = new_data[-1] if new_data else old[0]
                    new_data.append({"position": vals[i_new],
                                     "red": ref["red"], "green": ref["green"], "blue": ref["blue"]})
                else:
                    item = dict(old[i_old]); item["position"] = vals[i_new]
                    new_data.append(item); i_old += 1
            self.data = new_data
            return

        if n_new == n_old - 1:
            rem = next((i for i, ov in enumerate(old)
                        if not any(abs(ov["position"] - nv) < eps for nv in vals)), n_old - 1)
            self.data = [dict(old[i]) for i in range(n_old) if i != rem]
            for i, nv in enumerate(vals):
                self.data[i]["position"] = nv
            return

        m = min(n_old, n_new)
        self.data = []
        for i in range(m):
            item = dict(old[i]); item["position"] = vals[i]; self.data.append(item)
        for i in range(m, n_new):
            ref = self.data[-1] if self.data else {"red": 0.0, "green": 0.0, "blue": 0.0}
            self.data.append({"position": vals[i],
                              "red": ref["red"], "green": ref["green"], "blue": ref["blue"]})

    def refresh_widgets(self):
        idx   = self.slider.selectedHandleIndex()
        valid = (0 <= idx < len(self.data))

        if not valid:
            self.lbl_idx_val.setText("-")
            for e in (self.edit_pos, self.edit_r, self.edit_g, self.edit_b):
                with QtCore.QSignalBlocker(e): e.setText("")
                e.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_color.setEnabled(False)
            self._apply_color_button_style(0.85, 0.85, 0.85)
            return

        item = self.data[idx]
        self.lbl_idx_val.setText(str(idx))
        pairs = [(self.edit_pos, f"{item['position']:.6f}"),
                 (self.edit_r,   f"{item['red']:.6f}"),
                 (self.edit_g,   f"{item['green']:.6f}"),
                 (self.edit_b,   f"{item['blue']:.6f}")]
        for edit, text in pairs:
            with QtCore.QSignalBlocker(edit): edit.setText(text)

        is_endpoint = (idx == 0 or idx == len(self.data) - 1)
        self.edit_pos.setEnabled(not is_endpoint)
        for e in (self.edit_r, self.edit_g, self.edit_b): e.setEnabled(True)
        self.btn_delete.setEnabled(not is_endpoint)
        self.btn_color.setEnabled(True)
        self._apply_color_button_style(item["red"], item["green"], item["blue"])

    def on_rgb_edit_finished(self):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)):
            return
        cur = self.data[idx]

        def parse(edit, old):
            try: return self._clamp01(float(edit.text().strip()))
            except ValueError: return old

        self._set_current_rgb(parse(self.edit_r, cur["red"]),
                              parse(self.edit_g, cur["green"]),
                              parse(self.edit_b, cur["blue"]))
        self.refresh_widgets()

    def on_position_edit_finished(self):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)) or idx in (0, len(self.data) - 1):
            self.refresh_widgets(); return
        try: x = float(self.edit_pos.text().strip())
        except ValueError: self.refresh_widgets(); return
        left, right = self.slider.handles[idx - 1], self.slider.handles[idx + 1]
        if not (left < x < right): self.refresh_widgets(); return
        if self.slider.setHandleValue(idx, x, emit_signal=False):
            self.data[idx]["position"] = x
            self.slider.update()
        self.refresh_widgets(); self._emit_data_changed()

    def on_delete_anchor_clicked(self):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)) or idx in (0, len(self.data) - 1):
            return
        if self.slider.removeHandle(idx, emit_signal=True):
            self.sync_data_with_slider()
            self.refresh_widgets()
            self._emit_data_changed()

    def on_pick_color_clicked(self):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)):
            return
        cur = self.data[idx]
        initial = QtGui.QColor(*(int(round(self._clamp01(cur[k]) * 255))
                                 for k in ("red", "green", "blue")))
        color = QtWidgets.QColorDialog.getColor(initial=initial, parent=self, title="Pick Anchor Color")
        if color.isValid():
            self._set_current_rgb(color.redF(), color.greenF(), color.blueF())
            self.refresh_widgets()

    def on_copy_colorbar_to_clipboard(self):
        QtWidgets.QApplication.clipboard().setImage(self.colorbar.grab().toImage())

    def on_slider_values_changed(self, _vals):
        self.sync_data_with_slider(); self.refresh_widgets(); self._emit_data_changed()

    def on_slider_selection_changed(self, _idx):
        self.sync_data_with_slider(); self.refresh_widgets()


class ColorMapEditorWidget(QtWidgets.QWidget):
    updateCdict = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.colorbar = ColorBarPreview()
        self.slider   = MultiHandleSlider()
        self.panel    = HandlerInfoPanel(self.slider, self.colorbar)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.colorbar)
        lay.addWidget(self.slider)
        lay.addWidget(self.panel)

        self.panel.dataChanged.connect(self.colorbar.setData)
        self.panel.updateCdict.connect(self.updateCdict)
        self.colorbar.setData(self.panel.data)

    def setWidgetTitle(self, title):
        self.setWindowTitle(title)

    def get_anchors(self):
        return [dict(d) for d in self.panel.data]

    def set_anchors(self, data):
        if not data or len(data) < 2:
            return False
        items = []
        for d in data:
            try:
                items.append({
                    "position": max(0.0, min(1.0, float(d["position"]))),
                    "red":   max(0.0, min(1.0, float(d["red"]))),
                    "green": max(0.0, min(1.0, float(d["green"]))),
                    "blue":  max(0.0, min(1.0, float(d["blue"]))),
                })
            except Exception:
                continue
        if len(items) < 2:
            return False
        items.sort(key=lambda t: t["position"])
        items[0]["position"] = 0.0; items[-1]["position"] = 1.0
        self.slider.setValues([d["position"] for d in items], keep_selected=False)
        self.panel.data = [dict(d) for d in items]
        self.panel.sync_data_with_slider()
        self.panel.refresh_widgets()
        self.panel._emit_data_changed()
        return True

    def copy_colorbar_to_clipboard(self):
        self.panel.on_copy_colorbar_to_clipboard()
