# -*- coding: utf-8 -*-
"""
Image stack viewer widget — QGraphicsScene/QGraphicsView backend.

Replaces the old matplotlib FigureCanvas with QGraphicsView for:
  - Hardware-accelerated smooth zoom and pan
  - Draggable annotation items (picked points, region box, line)
  - Live info labels (pixel coordinates, distance between points, angle)
"""

import math
import numpy as np
from matplotlib import colors as mcolors, pyplot
from matplotlib.colors import Normalize

from angstrompro.utils.qt_compat import (
    QtGui, QtCore, QtWidgets, QueuedConnection, Vertical,
    LeftButton, RightButton, Signal, IS_QT6,
    KeepAspectRatio, DashLine, ScrollBarAlwaysOff, SmoothPixmapTransform,
)
from .ScaleWidget import ScaleWidget
from .general.NumberExpression import NumberExpression
from .ColorMapEditorWidget import ColorMapEditorWidget

# ─── Qt5 / Qt6 enum adapters ────────────────────────────────────────────────

if IS_QT6:
    _FMT_RGBA    = QtGui.QImage.Format.Format_RGBA8888
    _NO_BRUSH    = QtCore.Qt.BrushStyle.NoBrush
    _CLOSED_HAND = QtCore.Qt.CursorShape.ClosedHandCursor
    _ARROW       = QtCore.Qt.CursorShape.ArrowCursor
    _SMOOTH_TM   = QtCore.Qt.TransformationMode.FastTransformation
    _SP_EXPAND   = QtWidgets.QSizePolicy.Policy.Expanding
    _SP_PREFER   = QtWidgets.QSizePolicy.Policy.Preferred
    _GIF_MOVABLE = QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
    _GIF_SELECT  = QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
    _GIF_GEOM    = QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
    _GIF_IGNORE  = QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
    _GIC_POS     = QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
    _VIEW_ANCHOR = QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
    _NO_DRAG     = QtWidgets.QGraphicsView.DragMode.NoDrag
else:
    _FMT_RGBA    = QtGui.QImage.Format_RGBA8888
    _NO_BRUSH    = QtCore.Qt.NoBrush
    _CLOSED_HAND = QtCore.Qt.ClosedHandCursor
    _ARROW       = QtCore.Qt.ArrowCursor
    _SMOOTH_TM   = QtCore.Qt.FastTransformation
    _SP_EXPAND   = QtWidgets.QSizePolicy.Expanding
    _SP_PREFER   = QtWidgets.QSizePolicy.Preferred
    _GIF_MOVABLE = QtWidgets.QGraphicsItem.ItemIsMovable
    _GIF_SELECT  = QtWidgets.QGraphicsItem.ItemIsSelectable
    _GIF_GEOM    = QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
    _GIF_IGNORE  = QtWidgets.QGraphicsItem.ItemIgnoresTransformations
    _GIC_POS     = QtWidgets.QGraphicsItem.ItemPositionHasChanged
    _VIEW_ANCHOR = QtWidgets.QGraphicsView.AnchorUnderMouse
    _NO_DRAG     = QtWidgets.QGraphicsView.NoDrag


# ─── Helper: numpy 2-D slice → QPixmap ──────────────────────────────────────

def _data_to_pixmap(data2d: np.ndarray, vmin: float, vmax: float,
                    colormap) -> tuple:
    """Return (pixmap, rgba8_buf).  Caller must keep rgba8_buf alive."""
    norm  = Normalize(vmin=vmin, vmax=vmax, clip=True)
    if isinstance(colormap, str):
        import matplotlib.cm as cm
        cmap = cm.get_cmap(colormap)
    else:
        cmap = colormap
    rgba_f = cmap(norm(data2d))                          # (H, W, 4) float64
    rgba8  = np.ascontiguousarray((rgba_f * 255).astype(np.uint8))
    H, W   = rgba8.shape[:2]
    qimg   = QtGui.QImage(rgba8.data, W, H, W * 4, _FMT_RGBA)
    return QtGui.QPixmap.fromImage(qimg), rgba8


# ─── Draggable picked-point item ─────────────────────────────────────────────

class _PickedPointItem(QtWidgets.QGraphicsEllipseItem):
    """Crosshair-circle marker in scene (image-pixel) coordinates.

    Dragging updates the coordinate label live.
    Set ``on_moved`` to a callable invoked on every position change.
    """

    RADIUS = 5   # scene units (= image pixels)

    def __init__(self, col: float, row: float, index: int,
                 color: QtGui.QColor, on_moved=None):
        r = self.RADIUS
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.setPos(col, row)
        self.setFlag(_GIF_MOVABLE, True)
        self.setFlag(_GIF_SELECT,  True)
        self.setFlag(_GIF_GEOM,    True)
        self.setZValue(10)

        pen = QtGui.QPen(color)
        pen.setCosmetic(True)
        pen.setWidthF(1.5)
        self.setPen(pen)
        self.setBrush(QtGui.QBrush(_NO_BRUSH))

        # Label child — ignores view transform so text stays readable at any zoom
        self._lbl = QtWidgets.QGraphicsTextItem(self)
        self._lbl.setDefaultTextColor(color)
        self._lbl.setFlag(_GIF_IGNORE,  True)
        self._lbl.setFlag(_GIF_MOVABLE, True)
        self._lbl.setFlag(_GIF_SELECT,  True)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        self._lbl.setFont(font)
        self._lbl.setPos(r + 3, -r)
        self._lbl.setZValue(11)

        self._idx      = index
        self._on_moved = on_moved
        self._refresh_label()

    def scene_col(self) -> float:
        return self.pos().x()

    def scene_row(self) -> float:
        return self.pos().y()

    def _refresh_label(self):
        self._lbl.setPlainText(
            f"{self._idx}: ({self.scene_col():.1f}, {self.scene_row():.1f})")

    def itemChange(self, change, value):
        if change == _GIC_POS:
            self._refresh_label()
            if self._on_moved:
                self._on_moved()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen())
        r = self.RADIUS
        painter.drawEllipse(QtCore.QRectF(-r, -r, 2 * r, 2 * r))
        painter.drawLine(QtCore.QLineF(-r, 0.0, r, 0.0))
        painter.drawLine(QtCore.QLineF(0.0, -r, 0.0, r))


# ─── Custom graphics view ─────────────────────────────────────────────────────

class _ImageGraphicsView(QtWidgets.QGraphicsView):
    """QGraphicsView for image data.

    - Mouse wheel: zoom in / out centred on cursor.
    - Left-drag on background: pan.
    - Right-click: emit ``scenePointPicked`` with scene (col, row).
    - Mouse move: emit ``sceneMouseMoved`` with scene (col, row).

    Scene coordinate (x, y) equals image (col, row) because the pixmap
    item is placed at the scene origin.
    """

    sceneMouseMoved  = Signal(float, float)          # col, row
    scenePointPicked = Signal(float, float)          # col, row (right-click)
    mouseReleased    = Signal(str)                   # "LEFT_BUTTON" | "RIGHT_BUTTON"
    wheelScrolled    = Signal(float, float, int)     # col, row, angleDelta_y

    _ZOOM_FACTOR = 1.25

    def __init__(self, scene: QtWidgets.QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setTransformationAnchor(_VIEW_ANCHOR)
        self.setResizeAnchor(_VIEW_ANCHOR)
        self.setVerticalScrollBarPolicy(ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(ScrollBarAlwaysOff)
        self.setDragMode(_NO_DRAG)
        self.setRenderHint(SmoothPixmapTransform, False)
        self.setMouseTracking(True)
        sp = QtWidgets.QSizePolicy(_SP_EXPAND, _SP_EXPAND)
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)
        self._panning   = False
        self._pan_start = QtCore.QPoint()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return width

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        f = self._ZOOM_FACTOR if delta > 0 else 1.0 / self._ZOOM_FACTOR
        self.scale(f, f)
        pt = self.mapToScene(event.pos())
        self.wheelScrolled.emit(pt.x(), pt.y(), delta)

    def mousePressEvent(self, event):
        if event.button() == LeftButton:
            super().mousePressEvent(event)
            if self.scene().mouseGrabberItem() is None:
                self._panning   = True
                self._pan_start = event.pos()
                self.setCursor(_CLOSED_HAND)
        elif event.button() == RightButton:
            pt = self.mapToScene(event.pos())
            self.scenePointPicked.emit(pt.x(), pt.y())
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pt = self.mapToScene(event.pos())
        self.sceneMouseMoved.emit(pt.x(), pt.y())
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == LeftButton:
            self._panning = False
            self.setCursor(_ARROW)
            self.mouseReleased.emit("LEFT_BUTTON")
        elif event.button() == RightButton:
            self.mouseReleased.emit("RIGHT_BUTTON")
        super().mouseReleaseEvent(event)

    def fit_scene(self):
        """Fit all scene content into the viewport with aspect-ratio preserved."""
        r = self.scene().itemsBoundingRect()
        if not r.isEmpty():
            self.fitInView(r, KeepAspectRatio)


# ─── Main widget ──────────────────────────────────────────────────────────────

class ImageStackViewerWidget(QtWidgets.QWidget):
    sendMsgSignal = Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initNonUiMembers()
        self.initUiMembers()
        self.initUiLayout()

    # ── palette / colormap ────────────────────────────────────────────────

    def setup_palette(self, cmap_list: list) -> None:
        self.ui_cb_img_palette_list.currentIndexChanged.disconnect(self.imageColorMapChanged)
        self.ui_cb_img_palette_list.clear()
        self.ui_cb_img_palette_list.addItems(cmap_list)
        self.ui_cb_img_palette_list.setCurrentIndex(0)
        self.ui_cb_img_palette_list.currentIndexChanged.connect(self.imageColorMapChanged)
        self.set_colormap()

    # ── widget construction ───────────────────────────────────────────────

    def initUiMembers(self):
        # Graphics scene + view
        self._scene = QtWidgets.QGraphicsScene(self)
        self._view  = _ImageGraphicsView(self._scene)
        self._view.sceneMouseMoved.connect(self._on_scene_mouse_moved)
        self._view.scenePointPicked.connect(self._on_scene_point_picked)
        self._view.mouseReleased.connect(self._on_scene_mouse_released)
        self._view.wheelScrolled.connect(self._on_scene_wheel_scrolled)

        self._pixmap_item = QtWidgets.QGraphicsPixmapItem()
        self._pixmap_item.setTransformationMode(_SMOOTH_TM)
        self._scene.addItem(self._pixmap_item)
        self._rgba_buf = None   # keep alive while pixmap is valid

        # Control widgets
        self.ui_lb_widget_name       = QtWidgets.QLabel()
        self.ui_pb_select_var        = QtWidgets.QPushButton("Select Variable")
        self.ui_pb_select_var.clicked.connect(self.selectVar)
        self.ui_lb_selected_var_name = QtWidgets.QLabel("Name: ")
        self.ui_le_selected_var      = QtWidgets.QLineEdit()
        self.ui_le_image_data_type   = QtWidgets.QLabel("Type: ")
        self.ui_cb_image_data_type   = QtWidgets.QComboBox()
        self.ui_cb_image_data_type.addItems(self.var_data_type_list)
        self.ui_cb_image_data_type.currentIndexChanged.connect(self.imageDataTypeChanged)
        self.ui_cb_image_data_type.setEnabled(False)
        self.ui_lb_image_layer       = QtWidgets.QLabel("Layer: ")
        self.ui_sb_image_layers      = QtWidgets.QSpinBox()
        self.ui_sb_image_layers.valueChanged.connect(self.imageLayerChanged, QueuedConnection)
        self.ui_sb_image_layers.setEnabled(False)
        self.ui_le_layer_value       = QtWidgets.QLineEdit()
        self.ui_le_layer_value.setEnabled(False)
        self.ui_lb_layer_unit        = QtWidgets.QLabel("")

        self.ui_scale_widget = ScaleWidget(Vertical)
        self.ui_scale_widget.scaleChanged.connect(self.imgeScaleChanged)

        self.ui_lb_img_palette             = QtWidgets.QLabel("Palette: ")
        self.ui_cb_img_palette_list        = QtWidgets.QComboBox()
        self.ui_cb_img_rt_cmp              = QtWidgets.QCheckBox("RT-ColorMap")
        self.ui_cb_img_rt_cmp.clicked.connect(self.imageIsRtCmpOnChanged)

        self.ui_lb_img_picked_points       = QtWidgets.QLabel("Picked Points: ")
        self.ui_cb_img_pk_pts_palette_list = QtWidgets.QComboBox()
        self.ui_cb_img_pk_pts_palette_list.addItems(self.img_marker_cn_list)
        self.ui_cb_img_pk_pts_palette_list.currentIndexChanged.connect(
            self.imageMarkerColorChanged)

        self.ui_cb_img_pk_pts_mode = QtWidgets.QComboBox()
        self.ui_cb_img_pk_pts_mode.setMinimumWidth(90)
        self.ui_cb_img_pk_pts_mode.addItems(["Points", "Lines", "Circle", "Region"])
        self.ui_cb_img_pk_pts_mode.currentIndexChanged.connect(
            self._update_annotation_overlay)

        self.ui_lw_img_picked_points = QtWidgets.QListWidget()
        self.ui_pb_img_picked_points_remove = QtWidgets.QPushButton("Remove Point")
        self.ui_pb_img_picked_points_remove.clicked.connect(self.removePickedPoint)

        self.ui_lb_img_to_data_coord      = QtWidgets.QLabel("Data coords（column, row）: ")
        self.ui_le_img_to_data_coordinate = QtWidgets.QLineEdit()
        self.ui_lb_uds_data_info          = QtWidgets.QLabel("Info: ")
        self.ui_lw_uds_data_info          = QtWidgets.QListWidget()

        self.ui_rt_cmp = ColorMapEditorWidget()
        self.ui_rt_cmp.updateCdict.connect(self.imageIsRtCmpOnChanged)

        # Seed palette
        self.ui_cb_img_palette_list.addItem('gray')
        self.ui_cb_img_palette_list.currentIndexChanged.connect(self.imageColorMapChanged)
        self.set_colormap()

    def initUiLayout(self):
        right_top = QtWidgets.QVBoxLayout()
        right_top.addWidget(self.ui_scale_widget)
        right_top.addWidget(self.ui_lb_img_palette)
        right_top.addWidget(self.ui_cb_img_palette_list)
        right_top.addWidget(self.ui_cb_img_rt_cmp)
        right_top.addWidget(self.ui_lb_img_picked_points)
        pk_row = QtWidgets.QHBoxLayout()
        pk_row.addWidget(self.ui_cb_img_pk_pts_palette_list)
        pk_row.addWidget(self.ui_cb_img_pk_pts_mode)
        right_top.addLayout(pk_row)
        right_top.addWidget(self.ui_lw_img_picked_points)
        right_top.addWidget(self.ui_pb_img_picked_points_remove)

        right_panel = QtWidgets.QWidget()
        right_panel.setLayout(right_top)
        right_panel.setMaximumWidth(200)
        right_panel.setSizePolicy(_SP_PREFER, _SP_EXPAND)

        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(self._view, stretch=1)
        top_row.addWidget(right_panel)

        left_bot = QtWidgets.QVBoxLayout()
        left_bot.addWidget(self.ui_pb_select_var)
        hn = QtWidgets.QHBoxLayout()
        hn.addWidget(self.ui_lb_selected_var_name)
        hn.addWidget(self.ui_le_selected_var)
        left_bot.addLayout(hn)
        ht = QtWidgets.QHBoxLayout()
        ht.addWidget(self.ui_le_image_data_type)
        ht.addWidget(self.ui_cb_image_data_type)
        left_bot.addLayout(ht)
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.ui_lb_image_layer)
        hl.addWidget(self.ui_sb_image_layers)
        hl.addWidget(self.ui_le_layer_value)
        hl.addWidget(self.ui_lb_layer_unit)
        left_bot.addLayout(hl)

        right_bot = QtWidgets.QVBoxLayout()
        right_bot.addWidget(self.ui_lb_img_to_data_coord)
        right_bot.addWidget(self.ui_le_img_to_data_coordinate)
        right_bot.addWidget(self.ui_lb_uds_data_info)
        right_bot.addWidget(self.ui_lw_uds_data_info)

        bot_row = QtWidgets.QHBoxLayout()
        bot_row.addLayout(left_bot)
        bot_row.addLayout(right_bot)

        vlay = QtWidgets.QVBoxLayout()
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.addWidget(self.ui_lb_widget_name)
        vlay.addLayout(top_row, stretch=1)
        vlay.addLayout(bot_row)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(vlay, 0, 0)
        grid.setContentsMargins(0, 0, 0, 0)
        self.setLayout(grid)

    def initNonUiMembers(self):
        self.uds_variable            = 0
        self.selected_var_name       = ''
        self.uds_variable_type       = ''
        self.uds_variable_dataCopy   = 0
        self.uds_variable_dataAcCopy = 0
        self.uds_var_layer_value     = []

        self.msg_type = [
            'SELECT_USD_VARIABLE',
            'SYNC_LAYER',
            'REMOVE_SYNC_PICKED_POINTS',
            'CANVAS_MOUSE_MOVED',
            'CANVAS_MOUSE_PRESSED',
            'CANVAS_MOUSE_RELEASED',
            'CANVAS_WHEALED',
        ]

        self.selected_data_pt_x = 0
        self.selected_data_pt_y = 0

        self.img_picked_points_list = []
        self._point_items           = []   # _PickedPointItem objects in scene
        self._overlay_items         = []   # line / rect / shape items (redrawn on every update)
        self._label_items           = []   # movable label items (redrawn only on topology change)
        self._label_key             = None # (n, mode) — detects topology change
        self._rt_cursor_item        = None
        self._bias_text_item        = None
        self._bias_text_color       = '#ff0000'

        self.img_current_layer = 0
        self.sync_rt_points    = False
        self.bias_text_shown   = False

        # Legacy mouse-state attributes read by parent module via sendMsgSignal
        self.mouse_event_button          = ''
        self.mouse_event_x               = 0
        self.mouse_event_y               = 0
        self.mouse_event_angleDelta_y    = 0
        self.mouse_left_button_released  = True
        self.mouse_right_button_released = True

        self.var_data_type_list = ['Abs', 'Angle', 'Real', 'Image']

        self.img_color_map_builtin_list  = pyplot.colormaps()
        self.customizedColorPalletFolder = './ScienceY/GUI/customizedColorPallets/'
        self.img_is_rt_cmp_on            = False
        self.img_color_map               = 'gray'

        self.img_marker_cv_list = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#000000', '#ffffff']
        self.img_marker_cn_list = ['Red', 'Green', 'Blue', 'Yellow', 'Black', 'White']

        self.d = 0
        self.c = 0

    # ── scene mouse handlers ──────────────────────────────────────────────

    def _on_scene_mouse_moved(self, col: float, row: float):
        self.selected_data_pt_x = col
        self.selected_data_pt_y = row
        if isinstance(self.uds_variable_dataCopy, np.ndarray):
            d_r = self.uds_variable_dataCopy.shape[-2]
            d_c = self.uds_variable_dataCopy.shape[-1]
            ci, ri = int(col), int(row)
            if 0 <= ci < d_c and 0 <= ri < d_r:
                val = self.uds_variable_dataCopy[self.img_current_layer, ri, ci]
                sn  = NumberExpression.float_to_simplified_number(val)
                self.ui_le_img_to_data_coordinate.setText(f'Z( {ci} : {ri} ) = {sn}')
            else:
                self.ui_le_img_to_data_coordinate.setText(f'( {ci} : {ri} )')
        if self.sync_rt_points:
            self._update_rt_cursor()
        self.sendMsgSignalEmit(self.msg_type.index('CANVAS_MOUSE_MOVED'))

    def _on_scene_point_picked(self, col: float, row: float):
        self.mouse_event_button = 'RIGHT_BUTTON'
        self._add_picked_point(col, row)
        self.sendMsgSignalEmit(self.msg_type.index('CANVAS_MOUSE_PRESSED'))

    def _on_scene_mouse_released(self, button: str):
        self.mouse_event_button = button
        self.sendMsgSignalEmit(self.msg_type.index('CANVAS_MOUSE_RELEASED'))

    def _on_scene_wheel_scrolled(self, col: float, row: float, delta: int):
        self.selected_data_pt_x   = col
        self.selected_data_pt_y   = row
        self.mouse_event_angleDelta_y = delta
        self.sendMsgSignalEmit(self.msg_type.index('CANVAS_WHEALED'))

    # ── picked-point management ───────────────────────────────────────────

    def _mk_qcolor(self) -> QtGui.QColor:
        idx = self.ui_cb_img_pk_pts_palette_list.currentIndex()
        return QtGui.QColor(self.img_marker_cv_list[idx])

    def _add_picked_point(self, col: float, row: float):
        idx   = len(self._point_items)
        color = self._mk_qcolor()
        item  = _PickedPointItem(col, row, idx, color,
                                 on_moved=self._on_point_moved)
        self._scene.addItem(item)
        self._point_items.append(item)
        self.img_picked_points_list.append(f"{int(col)},{int(row)}")
        self._sync_listwidget()
        self._update_annotation_overlay()

    def _on_point_moved(self):
        """Sync dragged item positions back into img_picked_points_list."""
        for i, item in enumerate(self._point_items):
            self.img_picked_points_list[i] = (
                f"{int(item.scene_col())},{int(item.scene_row())}")
        self._sync_listwidget()
        self._update_annotation_overlay()
        self.sendMsgSignalEmit(self.msg_type.index('CANVAS_MOUSE_PRESSED'))

    def _sync_listwidget(self):
        prev = self.ui_lw_img_picked_points.currentRow()
        self.ui_lw_img_picked_points.clear()
        self.ui_lw_img_picked_points.addItems(self.img_picked_points_list)
        n = len(self.img_picked_points_list)
        if n > 0:
            self.ui_lw_img_picked_points.setCurrentRow(
                prev if 0 <= prev < n else n - 1)

    def _clear_point_items(self):
        for item in self._point_items:
            self._scene.removeItem(item)
        self._point_items.clear()
        self._clear_overlay_items()
        self._clear_label_items()

    def _clear_overlay_items(self):
        for item in self._overlay_items:
            self._scene.removeItem(item)
        self._overlay_items.clear()

    def _clear_label_items(self):
        for item in self._label_items:
            self._scene.removeItem(item)
        self._label_items.clear()
        self._label_key = None

    def _rebuild_point_items(self):
        """Recreate point items from img_picked_points_list (e.g. after colour change)."""
        self._clear_point_items()
        color = self._mk_qcolor()
        for i, s in enumerate(self.img_picked_points_list):
            parts = s.split(',')
            if len(parts) >= 2:
                item = _PickedPointItem(
                    float(parts[0]), float(parts[1]), i, color,
                    on_moved=self._on_point_moved)
                self._scene.addItem(item)
                self._point_items.append(item)
        self._sync_listwidget()
        self._update_annotation_overlay()

    def _update_annotation_overlay(self):
        """Redraw overlay graphics: lines, region rect, distance/angle labels."""
        self._clear_overlay_items()
        n = len(self._point_items)
        if n < 1:
            self._clear_label_items()
            return

        color = self._mk_qcolor()
        pen   = QtGui.QPen(color)
        pen.setCosmetic(True)
        pen.setWidthF(1.5)
        mode  = self.ui_cb_img_pk_pts_mode.currentText()

        # Recreate labels only when topology (point count or mode) changes
        _new_key = (n, mode)
        _labels_dirty = _new_key != self._label_key
        if _labels_dirty:
            self._clear_label_items()
            self._label_key = _new_key

        if mode == "Lines" and n >= 2:
            for i in range(n - 1):
                p0, p1 = self._point_items[i], self._point_items[i + 1]
                li = QtWidgets.QGraphicsLineItem(
                    p0.scene_col(), p0.scene_row(),
                    p1.scene_col(), p1.scene_row())
                li.setPen(pen)
                li.setZValue(5)
                self._scene.addItem(li)
                self._overlay_items.append(li)
                dist = math.hypot(p1.scene_col() - p0.scene_col(),
                                  p1.scene_row() - p0.scene_row())
                if _labels_dirty:
                    self._label_items.append(self._make_label(
                        f"{dist:.1f}px",
                        (p0.scene_col() + p1.scene_col()) / 2,
                        (p0.scene_row() + p1.scene_row()) / 2,
                        color))

            for i in range(n - 2):
                p0 = self._point_items[i]
                p1 = self._point_items[i + 1]
                p2 = self._point_items[i + 2]
                v1  = (p0.scene_col() - p1.scene_col(),
                       p0.scene_row() - p1.scene_row())
                v2  = (p2.scene_col() - p1.scene_col(),
                       p2.scene_row() - p1.scene_row())
                dot = v1[0] * v2[0] + v1[1] * v2[1]
                mag = math.hypot(*v1) * math.hypot(*v2)
                if mag > 0:
                    ang = math.degrees(math.acos(max(-1.0, min(1.0, dot / mag))))
                    if _labels_dirty:
                        self._label_items.append(self._make_label(
                            f"{ang:.1f}°",
                            p1.scene_col(), p1.scene_row(), color))

        elif mode == "Circle" and n >= 2:
            p0, p1 = self._point_items[0], self._point_items[1]
            cx, cy = p0.scene_col(), p0.scene_row()
            radius = math.hypot(p1.scene_col() - cx, p1.scene_row() - cy)
            ci = QtWidgets.QGraphicsEllipseItem(
                cx - radius, cy - radius, 2 * radius, 2 * radius)
            ci.setPen(pen)
            ci.setBrush(QtGui.QBrush(_NO_BRUSH))
            ci.setZValue(5)
            self._scene.addItem(ci)
            self._overlay_items.append(ci)
            # radius line from centre to edge point
            li = QtWidgets.QGraphicsLineItem(cx, cy, p1.scene_col(), p1.scene_row())
            li.setPen(pen)
            li.setZValue(5)
            self._scene.addItem(li)
            self._overlay_items.append(li)
            if _labels_dirty:
                self._label_items.append(self._make_label(
                    f"r={radius:.1f}px",
                    (cx + p1.scene_col()) / 2,
                    (cy + p1.scene_row()) / 2,
                    color))

        elif mode == "Region" and n >= 2:
            p0, p1 = self._point_items[0], self._point_items[1]
            x0, y0 = p0.scene_col(), p0.scene_row()
            x1, y1 = p1.scene_col(), p1.scene_row()
            dash_pen = QtGui.QPen(color)
            dash_pen.setCosmetic(True)
            dash_pen.setWidthF(1.5)
            dash_pen.setStyle(DashLine)
            ri = QtWidgets.QGraphicsRectItem(
                min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            ri.setPen(dash_pen)
            ri.setBrush(QtGui.QBrush(_NO_BRUSH))
            ri.setZValue(5)
            self._scene.addItem(ri)
            self._overlay_items.append(ri)
            if _labels_dirty:
                self._label_items.append(self._make_label(
                    f"{abs(x1-x0):.0f}×{abs(y1-y0):.0f}px",
                    min(x0, x1), min(y0, y1), color))

    def _make_label(self, text: str, x: float, y: float,
                    color: QtGui.QColor) -> QtWidgets.QGraphicsTextItem:
        lbl = QtWidgets.QGraphicsTextItem(text)
        lbl.setDefaultTextColor(color)
        lbl.setFlag(_GIF_IGNORE,   True)
        lbl.setFlag(_GIF_MOVABLE,  True)
        lbl.setFlag(_GIF_SELECT,   True)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        lbl.setFont(font)
        lbl.setPos(x, y)
        lbl.setZValue(12)
        self._scene.addItem(lbl)
        return lbl

    # ── real-time cursor ──────────────────────────────────────────────────

    def _update_rt_cursor(self):
        if self._rt_cursor_item is not None:
            self._scene.removeItem(self._rt_cursor_item)
            self._rt_cursor_item = None
        if not self.sync_rt_points:
            return
        r    = 8
        item = QtWidgets.QGraphicsEllipseItem(
            self.selected_data_pt_x - r, self.selected_data_pt_y - r, 2 * r, 2 * r)
        pen  = QtGui.QPen(QtGui.QColor('#ff0000'))
        pen.setCosmetic(True)
        item.setPen(pen)
        item.setBrush(QtGui.QBrush(_NO_BRUSH))
        item.setZValue(20)
        self._scene.addItem(item)
        self._rt_cursor_item = item

    # ── slots ─────────────────────────────────────────────────────────────

    def sendMsgSignalEmit(self, msgTypeIndex):
        self.sendMsgSignal.emit(msgTypeIndex)

    def selectVar(self):
        self.sendMsgSignalEmit(self.msg_type.index('SELECT_USD_VARIABLE'))

    def imageDataTypeChanged(self):
        idx = self.ui_cb_image_data_type.currentIndex()
        if idx == 0:
            self.uds_variable_dataCopy = np.abs(self.uds_variable.data)
        elif idx == 1:
            data_real = np.real(self.uds_variable.data).copy()
            data_imga = np.imag(self.uds_variable.data).copy()
            threshold = abs(np.average(data_real)) + abs(np.average(data_imga))
            data_real[np.abs(data_real) < threshold] = 0
            data_imga[np.abs(data_imga) < threshold] = 0
            self.uds_variable_dataCopy = np.angle(data_real + 1j * data_imga)
        elif idx == 2:
            self.uds_variable_dataCopy = np.real(self.uds_variable.data)
        elif idx == 3:
            self.uds_variable_dataCopy = np.imag(self.uds_variable.data)
        self.uds_variable_dataAcCopy = self.uds_variable_dataCopy.copy()
        if self.uds_variable_type == 'fft':
            Ox = int((self.uds_variable.data.shape[-1] - self.uds_variable.data.shape[-1] % 2) / 2)
            Oy = int((self.uds_variable.data.shape[-2] - self.uds_variable.data.shape[-2] % 2) / 2)
            self.uds_variable_dataAcCopy[:, Oy, Ox] = np.zeros(self.uds_variable.data.shape[0])
        self.imageLayerChanged()

    def imgeScaleChanged(self):
        self.img_current_layer = self.ui_sb_image_layers.value()
        self.updateImage()

    def imageLayerChangedSlotConnect(self):
        self.c += 1
        self.ui_sb_image_layers.valueChanged.connect(self.imageLayerChanged)

    def imageLayerChangedSlotDisconnect(self):
        receivers = self.ui_sb_image_layers.receivers(self.ui_sb_image_layers.valueChanged)
        self.d += 1
        if receivers > 0:
            self.ui_sb_image_layers.valueChanged.disconnect()

    def imageLayerChanged(self):
        self.img_current_layer = self.ui_sb_image_layers.value()
        if self.uds_var_layer_value:
            self.ui_le_layer_value.setText(
                self.uds_var_layer_value[self.img_current_layer])
        if self.uds_variable_type == 'fft':
            self.ui_scale_widget.setData(
                np.ravel(self.uds_variable_dataAcCopy[self.img_current_layer, :, :]),
                'SUFFIX_FFT')
        else:
            self.ui_scale_widget.setData(
                np.ravel(self.uds_variable_dataCopy[self.img_current_layer, :, :]))
        self.updateImage()
        self.sendMsgSignalEmit(self.msg_type.index('SYNC_LAYER'))

    def imageColorMapChanged(self):
        self.set_colormap()
        self.updateImage()

    def imageIsRtCmpOnChanged(self):
        self.img_is_rt_cmp_on = self.ui_cb_img_rt_cmp.isChecked()
        self.set_colormap()
        self.updateImage()

    def imageMarkerColorChanged(self):
        self._rebuild_point_items()

    def removePickedPoint(self):
        idx = self.ui_lw_img_picked_points.currentRow()
        if idx < 0:
            return
        self.img_picked_points_list.pop(idx)
        if idx < len(self._point_items):
            self._scene.removeItem(self._point_items.pop(idx))
        for i, item in enumerate(self._point_items):
            item._idx = i
            item._refresh_label()
        self._sync_listwidget()
        self._update_annotation_overlay()
        self.sendMsgSignalEmit(self.msg_type.index('REMOVE_SYNC_PICKED_POINTS'))

    # ── public setters ────────────────────────────────────────────────────

    def setCanvasWidgetSize(self, w, h):
        self._view.setFixedWidth(w)
        self._view.setFixedHeight(h)

    def setScaleWidgetZoomFactor(self, zoom_factor):
        self.ui_scale_widget.setZoomFactor(zoom_factor)

    def setScaleWidgetSigmaDefault(self, sigma_default):
        self.ui_scale_widget.setSigmaDefault(sigma_default)

    def setScaleWidgetFFTAutoScaleFactor(self, fft_auto_scale_factor):
        self.ui_scale_widget.setFFTAutoScaleFactor(fft_auto_scale_factor)

    def setScaleWidgetDataScaleFixed(self, data_scale_fixed):
        self.ui_scale_widget.setDataScaleFixed(data_scale_fixed)

    def setImagePickedPoints(self, picked_points):
        self.img_picked_points_list = list(picked_points)
        self._rebuild_point_items()

    def setSyncRtPoint(self, sync_rt_point):
        self.sync_rt_points = sync_rt_point

    def setBiasTextShown(self, bias_text_shown):
        self.bias_text_shown = bias_text_shown
        self.updateImage()

    def setBiasTextColor(self, color_name: str):
        _color_map = {
            'Red': '#ff0000', 'Green': '#00ff00', 'Blue': '#0000ff',
            'Yellow': '#ffff00', 'Black': '#000000', 'White': '#ffffff',
        }
        self._bias_text_color = _color_map.get(color_name, '#ff0000')
        if self._bias_text_item is not None:
            self._bias_text_item.setDefaultTextColor(QtGui.QColor(self._bias_text_color))

    def getLayerValue(self):
        axes = getattr(self.uds_variable, 'axes', None)
        if axes and len(axes) > 0 and hasattr(axes[0], 'values') and len(axes[0].values) > 0:
            self._layer_unit = getattr(axes[0], 'units', '')
            self.ui_lb_layer_unit.setText(self._layer_unit)
            self.uds_var_layer_value = [
                NumberExpression.float_to_simplified_number(v)
                for v in axes[0].values
            ]

    def setUdsData(self, usd_variable):
        self.selected_var_name     = usd_variable.name
        self.uds_variable          = usd_variable
        self.uds_variable_dataCopy = np.abs(self.uds_variable.data)
        self.uds_variable_type     = usd_variable.name.split('_')[-1]

        if self.uds_variable_type == 'fft':
            Ox = int((self.uds_variable.data.shape[-1] - self.uds_variable.data.shape[-1] % 2) / 2)
            Oy = int((self.uds_variable.data.shape[-2] - self.uds_variable.data.shape[-2] % 2) / 2)
            self.uds_variable_dataAcCopy = self.uds_variable_dataCopy.copy()
            self.uds_variable_dataAcCopy[:, Oy, Ox] = np.zeros(self.uds_variable.data.shape[0])

        self.ui_le_selected_var.setText(self.selected_var_name)
        self.ui_le_layer_value.setText('')
        self.ui_lb_layer_unit.setText('')

        var_shape = np.shape(self.uds_variable.data)
        if len(var_shape) >= 3:
            self.ui_sb_image_layers.setMinimum(0)
            self.ui_sb_image_layers.setMaximum(var_shape[0] - 1)
            self.getLayerValue()

        if self.ui_sb_image_layers.value() == 0:
            self.imageLayerChanged()
        else:
            self.ui_sb_image_layers.setValue(0)

        if self.uds_variable_type != 'fft':
            if self.ui_cb_image_data_type.currentIndex() == 2:
                self.imageDataTypeChanged()
            else:
                self.ui_cb_image_data_type.setCurrentIndex(2)

        self.ui_sb_image_layers.setEnabled(True)
        self.ui_cb_image_data_type.setEnabled(True)
        self.setEnabled(True)
        self.updateDataInfo()
        QtCore.QTimer.singleShot(0, self._view.fit_scene)

    def updateDataInfo(self):
        self.ui_lw_uds_data_info.clear()
        self.ui_lw_uds_data_info.addItems(
            [f"{k} = {v}" for k, v in self.uds_variable.info.items()])

    # ── colormap helpers ──────────────────────────────────────────────────

    def set_colormap(self):
        import matplotlib
        cname = self.ui_cb_img_palette_list.currentText()
        if self.img_is_rt_cmp_on:
            self.img_color_map = self.make_colormap_from_cdict(
                self.ui_rt_cmp.get_anchors())
        else:
            self.img_color_map = (
                cname if cname in matplotlib.colormaps
                else self.make_colormap_from_txt(cname))

    def make_colormap_from_cdict(self, anchors):
        cdict = {'red': [], 'green': [], 'blue': []}
        for a in anchors:
            cdict['red'].append([a['position'], a['red'], a['red']])
            cdict['green'].append([a['position'], a['green'], a['green']])
            cdict['blue'].append([a['position'], a['blue'], a['blue']])
        return mcolors.LinearSegmentedColormap('testCmap', segmentdata=cdict, N=256)

    def make_colormap_from_txt(self, cp):
        path = self.customizedColorPalletFolder + cp + '.txt'
        d    = np.loadtxt(path, delimiter="\t", skiprows=1) / 256 / 256
        cdict = {'red': [], 'green': [], 'blue': []}
        for i in range(256):
            cdict['red'].append([i / 255.0, d[i, 0], d[i, 0]])
            cdict['green'].append([i / 255.0, d[i, 1], d[i, 1]])
            cdict['blue'].append([i / 255.0, d[i, 2], d[i, 2]])
        return mcolors.LinearSegmentedColormap('CustomMap', cdict)

    # ── image update ──────────────────────────────────────────────────────

    def updateImage(self):
        if not isinstance(self.uds_variable_dataCopy, np.ndarray):
            return
        vmin   = self.ui_scale_widget.lowerValue()
        vmax   = self.ui_scale_widget.upperValue()
        data2d = self.uds_variable_dataCopy[self.img_current_layer, :, :]

        pixmap, self._rgba_buf = _data_to_pixmap(data2d, vmin, vmax, self.img_color_map)
        self._pixmap_item.setPixmap(pixmap)
        # Give the scene rect a large margin so the user can pan freely beyond
        # the image edges (scroll bar values are clamped to the scene rect).
        w, h   = pixmap.width(), pixmap.height()
        margin = max(w, h) * 4
        self._scene.setSceneRect(-margin, -margin, w + 2 * margin, h + 2 * margin)

        if self.bias_text_shown:
            txt = self.ui_le_layer_value.text() + self.ui_lb_layer_unit.text()
            if self._bias_text_item is None:
                self._bias_text_item = QtWidgets.QGraphicsTextItem()
                self._bias_text_item.setDefaultTextColor(QtGui.QColor(self._bias_text_color))
                self._bias_text_item.setFlag(_GIF_IGNORE, True)
                self._bias_text_item.setFlag(_GIF_MOVABLE, True)
                self._bias_text_item.setFlag(_GIF_SELECT, True)
                self._bias_text_item.setZValue(15)
                self._bias_text_item.setPos(pixmap.width() / 2, pixmap.height() - 20)
                self._scene.addItem(self._bias_text_item)
            self._bias_text_item.setPlainText(txt)
        else:
            if self._bias_text_item is not None:
                self._scene.removeItem(self._bias_text_item)
                self._bias_text_item = None

    def showEvent(self, event):
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._view.fit_scene)
