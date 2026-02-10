# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 13:11:14 2026

@author: jiahaoYan
"""

import os
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QSignalBlocker
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QImage
from PyQt5.QtWidgets import (
    QWidget, QApplication, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QColorDialog, QFileDialog, QMessageBox
)


class ColorBarPreview(QWidget):
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
            r = self._clamp01(a["red"])
            g = self._clamp01(a["green"])
            b = self._clamp01(a["blue"])
            cdict["red"].append([x, r, r])
            cdict["green"].append([x, g, g])
            cdict["blue"].append([x, b, b])
        return cdict

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = max(2, self.width())
        rect = self.rect().adjusted(1, 1, -1, -1)

        try:
            cdict = self._build_cdict()
            cmap = LinearSegmentedColormap("preview_cmap", cdict, N=512)

            xs = np.linspace(0.0, 1.0, w)
            rgba = cmap(xs)
            rgb = (rgba[:, :3] * 255).astype(np.uint8)

            img = QImage(w, 1, QImage.Format_RGB888)
            ptr = img.bits()
            ptr.setsize(w * 3)
            arr = np.frombuffer(ptr, np.uint8).reshape((1, w, 3))
            arr[0, :, :] = rgb

            p.drawImage(rect, img)
        except Exception:
            p.fillRect(rect, QColor(200, 200, 200))

        p.setPen(QPen(QColor(120, 120, 120), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(rect), 4, 4)


class MultiHandleSlider(QWidget):
    valuesChanged = pyqtSignal(list)
    selectionChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.handles = [0.0, 1.0]
        self.selected_index = -1
        self.dragging_index = -1

        self.margin = 14
        self.track_h = 6
        self.handle_r = 10
        self.hit_r = 10

        self.setMinimumHeight(44)
        self.setMouseTracking(True)

    def values(self):
        return self.handles.copy()

    def setValues(self, values, keep_selected=True):
        if not values or len(values) < 2:
            return False
        vals = [max(0.0, min(1.0, float(v))) for v in values]
        vals = sorted(vals)
        vals[0] = 0.0
        vals[-1] = 1.0

        self.handles = vals
        if keep_selected and 0 <= self.selected_index < len(self.handles):
            pass
        else:
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
        if not isinstance(index, int):
            return False
        if index < 0 or index >= len(self.handles):
            return False

        v = max(0.0, min(1.0, float(value)))

        if index == 0:
            if abs(v - 0.0) > 1e-12:
                return False
            self.handles[index] = 0.0
        elif index == len(self.handles) - 1:
            if abs(v - 1.0) > 1e-12:
                return False
            self.handles[index] = 1.0
        else:
            left = self.handles[index - 1]
            right = self.handles[index + 1]
            eps = 1e-6
            if not (v > left + eps and v < right - eps):
                return False
            self.handles[index] = v

        self.update()
        if emit_signal:
            self.valuesChanged.emit(self.values())
        return True

    def removeHandle(self, index, emit_signal=True):
        if not isinstance(index, int):
            return False
        if index <= 0 or index >= len(self.handles) - 1:
            return False

        self.handles.pop(index)

        if self.selected_index == index:
            self.selected_index = min(index, len(self.handles) - 1)
            if emit_signal:
                self.selectionChanged.emit(self.selected_index)
        elif self.selected_index > index:
            self.selected_index -= 1
            if emit_signal:
                self.selectionChanged.emit(self.selected_index)

        self.update()
        if emit_signal:
            self.valuesChanged.emit(self.values())
        return True

    def _track_left(self):
        return self.margin

    def _track_right(self):
        return self.width() - self.margin

    def _track_w(self):
        return max(1.0, self._track_right() - self._track_left())

    def _value_to_x(self, v):
        return self._track_left() + v * self._track_w()

    def _x_to_value(self, x):
        t = (x - self._track_left()) / self._track_w()
        return max(0.0, min(1.0, t))

    def _nearest_handle_index(self, pos):
        px, py = pos.x(), pos.y()
        cy = self.height() / 2.0
        best = -1
        best_d2 = (self.hit_r + 2) ** 2
        for i, v in enumerate(self.handles):
            hx = self._value_to_x(v)
            dx = px - hx
            dy = py - cy
            d2 = dx * dx + dy * dy
            if d2 <= best_d2:
                best_d2 = d2
                best = i
        return best

    def _insert_sorted(self, v):
        idx = 0
        while idx < len(self.handles) and self.handles[idx] < v:
            idx += 1
        self.handles.insert(idx, v)
        return idx

    def mousePressEvent(self, event):
        idx = self._nearest_handle_index(event.pos())

        if event.button() == Qt.RightButton:
            v = self._x_to_value(event.x())
            eps = 1e-6
            for hv in self.handles:
                if abs(hv - v) < eps:
                    return
            new_idx = self._insert_sorted(v)
            self.setSelectedIndex(new_idx, emit_signal=True)
            self.valuesChanged.emit(self.values())
            self.update()
            return

        if event.button() == Qt.LeftButton:
            if idx >= 0:
                self.setSelectedIndex(idx, emit_signal=True)
                if idx != 0 and idx != len(self.handles) - 1:
                    self.dragging_index = idx
            else:
                self.setSelectedIndex(-1, emit_signal=True)
            self.update()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging_index >= 0 and (event.buttons() & Qt.LeftButton):
            i = self.dragging_index
            v = self._x_to_value(event.x())

            left = self.handles[i - 1]
            right = self.handles[i + 1]
            eps = 1e-6
            v = max(v, left + eps)
            v = min(v, right - eps)

            self.handles[i] = v
            self.valuesChanged.emit(self.values())
            self.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_index = -1
            self.update()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        cy = self.height() / 2.0
        left, right = self._track_left(), self._track_right()

        groove = QRectF(left, cy - self.track_h / 2, right - left, self.track_h)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(210, 210, 210))
        p.drawRoundedRect(groove, 3, 3)

        for i, v in enumerate(self.handles):
            x = self._value_to_x(v)
            if i == self.selected_index:
                fill = QColor(255, 230, 170)
            elif i == 0 or i == len(self.handles) - 1:
                fill = QColor(235, 235, 235)
            else:
                fill = QColor(255, 255, 255)

            p.setPen(QPen(QColor(80, 80, 80), 1))
            p.setBrush(QBrush(fill))
            p.drawEllipse(QRectF(x - self.handle_r, cy - self.handle_r,
                                 2 * self.handle_r, 2 * self.handle_r))


class HandlerInfoPanel(QWidget):
    dataChanged = pyqtSignal(list)
    updateCdict = pyqtSignal(list)

    def __init__(self, slider: MultiHandleSlider, colorbar: ColorBarPreview, parent=None):
        super().__init__(parent)
        self.slider = slider
        self.colorbar = colorbar

        self.data = [
            {"position": 0.0, "red": 0.0, "green": 0.0, "blue": 0.0},
            {"position": 1.0, "red": 1.0, "green": 1.0, "blue": 1.0},
        ]

        self.lbl_idx_val = QLabel("-")
        self.edit_pos = QLineEdit()
        self.edit_r = QLineEdit()
        self.edit_g = QLineEdit()
        self.edit_b = QLineEdit()

        self.btn_delete = QPushButton("Delete Anchor")
        self.btn_color = QPushButton("")
        self.btn_color.setFixedSize(90, 36)
        self.btn_clipboard = QPushButton("Clipboard")
        self.btn_export = QPushButton("Export")
        self.btn_update = QPushButton("Update")

        grid = QGridLayout()
        grid.addWidget(QLabel("Current index:"), 0, 0)
        grid.addWidget(self.lbl_idx_val,         0, 1)
        grid.addWidget(QLabel("Position:"),      1, 0)
        grid.addWidget(self.edit_pos,            1, 1)
        grid.addWidget(QLabel("Red:"),           2, 0)
        grid.addWidget(self.edit_r,              2, 1)
        grid.addWidget(QLabel("Green:"),         3, 0)
        grid.addWidget(self.edit_g,              3, 1)
        grid.addWidget(QLabel("Blue:"),          4, 0)
        grid.addWidget(self.edit_b,              4, 1)

        btn_col = QVBoxLayout()
        btn_col.addWidget(self.btn_delete)
        btn_col.addWidget(self.btn_color)
        btn_col.addWidget(self.btn_clipboard)
        btn_col.addWidget(self.btn_export)
        btn_col.addWidget(self.btn_update)
        btn_col.addStretch(1)

        main = QHBoxLayout(self)
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
    def _clamp01(x):
        return max(0.0, min(1.0, float(x)))

    def _apply_color_button_style(self, r, g, b):
        rr = int(round(self._clamp01(r) * 255))
        gg = int(round(self._clamp01(g) * 255))
        bb = int(round(self._clamp01(b) * 255))
        self.btn_color.setStyleSheet(
            "QPushButton {"
            f"background-color: rgb({rr},{gg},{bb});"
            "border: 1px solid #666; border-radius: 4px;}"
        )

    def _emit_data_changed(self):
        self.dataChanged.emit([dict(d) for d in self.data])

    def _set_current_rgb(self, r, g, b, update_lineedits=True):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)):
            return False

        r = self._clamp01(r)
        g = self._clamp01(g)
        b = self._clamp01(b)

        self.data[idx]["red"] = r
        self.data[idx]["green"] = g
        self.data[idx]["blue"] = b

        if update_lineedits:
            with QSignalBlocker(self.edit_r):
                self.edit_r.setText(f"{r:.6f}")
            with QSignalBlocker(self.edit_g):
                self.edit_g.setText(f"{g:.6f}")
            with QSignalBlocker(self.edit_b):
                self.edit_b.setText(f"{b:.6f}")

        self._apply_color_button_style(r, g, b)
        self._emit_data_changed()
        return True

    def _build_cdict_from_data(self):
        anchors = sorted(self.data, key=lambda d: d["position"])
        cdict = {"red": [], "green": [], "blue": []}
        for a in anchors:
            x = self._clamp01(a["position"])
            r = self._clamp01(a["red"])
            g = self._clamp01(a["green"])
            b = self._clamp01(a["blue"])
            cdict["red"].append([x, r, r])
            cdict["green"].append([x, g, g])
            cdict["blue"].append([x, b, b])
        return cdict

    def on_export_colormap(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Colormap",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if not filepath:
            return

        base = os.path.splitext(os.path.basename(filepath))[0]
        if not filepath.lower().endswith(".txt"):
            filepath += ".txt"

        try:
            cdict = self._build_cdict_from_data()
            cmap = LinearSegmentedColormap(base, cdict, N=4096)

            xs = np.linspace(0.0, 1.0, 256)
            rgba = cmap(xs)
            rgb = np.clip(np.round(rgba[:, :3] * 65025.0), 0, 65025).astype(int)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"{base}[][0]\t{base}[][1]\t{base}[][2]\n")
                for i in range(256):
                    r, g, b = rgb[i]
                    f.write(f"{r}\t{g}\t{b}\n")

            QMessageBox.information(self, "Export", f"Colormap exported:\n{filepath}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
    
    def on_update_colormap(self):
        self.updateCdict.emit([dict(d) for d in self.data])
    
    def sync_data_with_slider(self):
        vals = self.slider.values()
        old = self.data
        n_old = len(old)
        n_new = len(vals)

        if n_new == n_old:
            for i in range(n_new):
                old[i]["position"] = vals[i]
            self.data = old
            return

        eps = 1e-9

        if n_new == n_old + 1:
            ins = None
            i_old = 0
            for i_new in range(n_new):
                if i_old < n_old and abs(vals[i_new] - old[i_old]["position"]) < eps:
                    i_old += 1
                else:
                    ins = i_new
                    break
            if ins is None:
                ins = n_new - 1

            new_data = []
            i_old = 0
            for i_new in range(n_new):
                if i_new == ins:
                    if i_new > 0:
                        left = new_data[i_new - 1]
                        item = {
                            "position": vals[i_new],
                            "red": left["red"],
                            "green": left["green"],
                            "blue": left["blue"],
                        }
                    else:
                        ref = old[0] if n_old > 0 else {"red": 0.0, "green": 0.0, "blue": 0.0}
                        item = {
                            "position": vals[i_new],
                            "red": ref["red"],
                            "green": ref["green"],
                            "blue": ref["blue"],
                        }
                    new_data.append(item)
                else:
                    item = dict(old[i_old])
                    item["position"] = vals[i_new]
                    new_data.append(item)
                    i_old += 1
            self.data = new_data
            return

        if n_new == n_old - 1:
            rem = None
            i_new = 0
            for i_old in range(n_old):
                if i_new < n_new and abs(old[i_old]["position"] - vals[i_new]) < eps:
                    i_new += 1
                else:
                    rem = i_old
                    break
            if rem is None:
                rem = n_old - 1

            new_data = []
            i_new = 0
            for i_old in range(n_old):
                if i_old == rem:
                    continue
                item = dict(old[i_old])
                item["position"] = vals[i_new]
                new_data.append(item)
                i_new += 1
            self.data = new_data
            return

        new_data = []
        m = min(n_old, n_new)
        for i in range(m):
            item = dict(old[i])
            item["position"] = vals[i]
            new_data.append(item)
        for i in range(m, n_new):
            if i > 0:
                left = new_data[i - 1]
                new_data.append({
                    "position": vals[i],
                    "red": left["red"],
                    "green": left["green"],
                    "blue": left["blue"],
                })
            else:
                new_data.append({
                    "position": vals[i],
                    "red": 0.0,
                    "green": 0.0,
                    "blue": 0.0,
                })
        self.data = new_data

    def refresh_widgets(self):
        idx = self.slider.selectedHandleIndex()
        valid = (0 <= idx < len(self.data))

        if not valid:
            self.lbl_idx_val.setText("-")
            for e in (self.edit_pos, self.edit_r, self.edit_g, self.edit_b):
                with QSignalBlocker(e):
                    e.setText("")
                e.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_color.setEnabled(False)
            self.btn_clipboard.setEnabled(True)
            self.btn_export.setEnabled(True)
            self._apply_color_button_style(0.85, 0.85, 0.85)
            return

        item = self.data[idx]
        self.lbl_idx_val.setText(str(idx))

        with QSignalBlocker(self.edit_pos):
            self.edit_pos.setText(f"{item['position']:.6f}")
        with QSignalBlocker(self.edit_r):
            self.edit_r.setText(f"{item['red']:.6f}")
        with QSignalBlocker(self.edit_g):
            self.edit_g.setText(f"{item['green']:.6f}")
        with QSignalBlocker(self.edit_b):
            self.edit_b.setText(f"{item['blue']:.6f}")

        last = len(self.data) - 1
        is_endpoint = (idx == 0 or idx == last)

        self.edit_pos.setEnabled(not is_endpoint)
        self.edit_r.setEnabled(True)
        self.edit_g.setEnabled(True)
        self.edit_b.setEnabled(True)

        self.btn_delete.setEnabled(not is_endpoint)
        self.btn_color.setEnabled(True)
        self.btn_clipboard.setEnabled(True)
        self.btn_export.setEnabled(True)
        self._apply_color_button_style(item["red"], item["green"], item["blue"])

    def on_rgb_edit_finished(self):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)):
            return

        cur = self.data[idx]

        def parse_or_keep(edit, old):
            txt = edit.text().strip()
            try:
                return self._clamp01(float(txt))
            except ValueError:
                return old

        r = parse_or_keep(self.edit_r, cur["red"])
        g = parse_or_keep(self.edit_g, cur["green"])
        b = parse_or_keep(self.edit_b, cur["blue"])

        self._set_current_rgb(r, g, b, update_lineedits=True)
        self.refresh_widgets()

    def on_position_edit_finished(self):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)):
            return
        if idx == 0 or idx == len(self.data) - 1:
            self.refresh_widgets()
            return

        txt = self.edit_pos.text().strip()
        try:
            x = float(txt)
        except ValueError:
            self.refresh_widgets()
            return

        left = self.slider.handles[idx - 1]
        right = self.slider.handles[idx + 1]
        if not (x > left and x < right):
            self.refresh_widgets()
            return

        ok = self.slider.setHandleValue(idx, x, emit_signal=False)
        if ok:
            self.data[idx]["position"] = x
            self.slider.update()

        self.refresh_widgets()
        self._emit_data_changed()

    def on_delete_anchor_clicked(self):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)):
            return
        if idx == 0 or idx == len(self.data) - 1:
            return

        ok = self.slider.removeHandle(idx, emit_signal=True)
        if not ok:
            return

        self.sync_data_with_slider()
        self.refresh_widgets()
        self._emit_data_changed()

    def on_pick_color_clicked(self):
        idx = self.slider.selectedHandleIndex()
        if not (0 <= idx < len(self.data)):
            return

        cur = self.data[idx]
        initial = QColor(
            int(round(self._clamp01(cur["red"]) * 255)),
            int(round(self._clamp01(cur["green"]) * 255)),
            int(round(self._clamp01(cur["blue"]) * 255)),
        )

        color = QColorDialog.getColor(initial=initial, parent=self, title="Pick Anchor Color")
        if not color.isValid():
            return

        self._set_current_rgb(color.redF(), color.greenF(), color.blueF(), update_lineedits=True)
        self.refresh_widgets()

    def on_copy_colorbar_to_clipboard(self):
        pixmap = self.colorbar.grab()
        QApplication.clipboard().setImage(pixmap.toImage())

    def on_slider_values_changed(self, _vals):
        self.sync_data_with_slider()
        self.refresh_widgets()
        self._emit_data_changed()

    def on_slider_selection_changed(self, _idx):
        self.sync_data_with_slider()
        self.refresh_widgets()


class ColorMapEditorWidget(QWidget):
    updateCdict = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.colorbar = ColorBarPreview()
        self.slider = MultiHandleSlider()
        self.panel = HandlerInfoPanel(self.slider, self.colorbar)

        lay = QVBoxLayout(self)
        lay.addWidget(self.colorbar)
        lay.addWidget(self.slider)
        lay.addWidget(self.panel)

        self.panel.dataChanged.connect(self.colorbar.setData)
        self.panel.updateCdict.connect(self.updateCdict)

        self.colorbar.setData(self.panel.data)

    def get_anchors(self):
        return [dict(d) for d in self.panel.data]

    def set_anchors(self, data):
        if not data or len(data) < 2:
            return False

        items = []
        for d in data:
            try:
                x = float(d["position"])
                r = float(d["red"])
                g = float(d["green"])
                b = float(d["blue"])
            except Exception:
                continue
            items.append({
                "position": max(0.0, min(1.0, x)),
                "red": max(0.0, min(1.0, r)),
                "green": max(0.0, min(1.0, g)),
                "blue": max(0.0, min(1.0, b)),
            })

        if len(items) < 2:
            return False

        items.sort(key=lambda t: t["position"])
        items[0]["position"] = 0.0
        items[-1]["position"] = 1.0

        positions = [d["position"] for d in items]
        self.slider.setValues(positions, keep_selected=False)
        self.panel.data = [dict(d) for d in items]
        self.panel.sync_data_with_slider()
        self.panel.refresh_widgets()
        self.panel._emit_data_changed()
        return True

    def copy_colorbar_to_clipboard(self):
        self.panel.on_copy_colorbar_to_clipboard()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    root = QWidget()
    layout = QVBoxLayout(root)

    cmap_editor = ColorMapEditorWidget()
    layout.addWidget(cmap_editor)

    def on_cdict_changed(cdict):
        print("anchors:", len(cdict))
        print(cdict)

    cmap_editor.updateCdict.connect(on_cdict_changed)

    root.resize(980, 460)
    root.show()
    sys.exit(app.exec_())
