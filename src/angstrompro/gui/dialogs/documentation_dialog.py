"""Offline HTML documentation viewer for AngstromPro."""
from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from angstrompro.app.user_data_folder import get_qsettings
from angstrompro.utils.qt_compat import IS_QT6, QtCore, QtGui, QtWidgets


class DocumentationDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, start_page: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AngstromPro Documentation")
        self.setWindowModality(
            QtCore.Qt.WindowModality.NonModal if IS_QT6 else QtCore.Qt.NonModal
        )
        self._docs_root = self._resolve_docs_root()
        self._navigation = self._load_navigation()
        self._home = self._docs_root / self._navigation.get("home", "index.html")
        self._build_ui()
        self._populate_navigation()

        qs = get_qsettings()
        self.resize(qs.value("documentation/size", QtCore.QSize(1100, 720)))
        self.finished.connect(
            lambda: get_qsettings().setValue("documentation/size", self.size())
        )
        self.open_page(start_page or str(self._home))

    @staticmethod
    def _resolve_docs_root() -> Path:
        root = resources.files("angstrompro.resources").joinpath("docs")
        path = Path(str(root))
        if not (path / "navigation.json").is_file():
            raise FileNotFoundError(
                "Bundled documentation is unavailable. Reinstall AngstromPro "
                "or rebuild it with tools/build_docs.py."
            )
        return path

    def _load_navigation(self) -> dict:
        return json.loads(
            (self._docs_root / "navigation.json").read_text(encoding="utf-8")
        )

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        toolbar = QtWidgets.QHBoxLayout()
        self._back = QtWidgets.QPushButton("Back")
        self._forward = QtWidgets.QPushButton("Forward")
        self._home_btn = QtWidgets.QPushButton("Home")
        self._external = QtWidgets.QPushButton("Open in browser")
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Find on page...")
        self._search.setClearButtonEnabled(True)
        find_btn = QtWidgets.QPushButton("Find")

        self._back.clicked.connect(self._go_back)
        self._forward.clicked.connect(self._go_forward)
        self._home_btn.clicked.connect(lambda: self.open_page(str(self._home)))
        self._external.clicked.connect(self._open_external)
        self._search.returnPressed.connect(self._find)
        find_btn.clicked.connect(self._find)

        for widget in (self._back, self._forward, self._home_btn):
            toolbar.addWidget(widget)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(find_btn)
        toolbar.addWidget(self._external)
        root.addLayout(toolbar)

        splitter = QtWidgets.QSplitter()
        orientation = (
            QtCore.Qt.Orientation.Horizontal if IS_QT6 else QtCore.Qt.Horizontal
        )
        splitter.setOrientation(orientation)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setMinimumWidth(230)
        self._tree.itemActivated.connect(self._on_tree_item)
        self._tree.itemClicked.connect(self._on_tree_item)
        splitter.addWidget(self._tree)

        self._browser = QtWidgets.QTextBrowser()
        # Keep the document itself paper-like and readable under either the
        # application light/dark theme.  QTextBrowser does not consistently
        # honour body foreground/background rules from embedded HTML across
        # Qt 5, Qt 6, and macOS.
        self._browser.setStyleSheet(
            "QTextBrowser { color: #25313b; background: #ffffff; }"
        )
        self._browser.document().setDefaultStyleSheet(
            "body { color: #25313b; background: #ffffff; }"
        )
        self._browser.setOpenLinks(False)
        self._browser.setOpenExternalLinks(False)
        self._browser.anchorClicked.connect(self._on_anchor)
        self._browser.backwardAvailable.connect(self._back.setEnabled)
        self._browser.forwardAvailable.connect(self._forward.setEnabled)
        splitter.addWidget(self._browser)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 850])
        root.addWidget(splitter, stretch=1)

    def _populate_navigation(self) -> None:
        home = QtWidgets.QTreeWidgetItem(["Documentation home"])
        home.setData(0, self._user_role(), str(self._home))
        self._tree.addTopLevelItem(home)
        for section in self._navigation.get("sections", []):
            parent = QtWidgets.QTreeWidgetItem([section["title"]])
            self._tree.addTopLevelItem(parent)
            for page in section.get("pages", []):
                item = QtWidgets.QTreeWidgetItem([page["title"]])
                item.setData(
                    0,
                    self._user_role(),
                    str(self._docs_root / page["path"]),
                )
                parent.addChild(item)
            parent.setExpanded(True)

    @staticmethod
    def _user_role():
        return QtCore.Qt.ItemDataRole.UserRole if IS_QT6 else QtCore.Qt.UserRole

    def _on_tree_item(self, item, _column=0) -> None:
        path = item.data(0, self._user_role())
        if path:
            self.open_page(path)

    def open_page(self, page: str) -> None:
        path = Path(page)
        if not path.is_absolute():
            path = self._docs_root / path
        self._browser.setSource(QtCore.QUrl.fromLocalFile(str(path.resolve())))

    def _on_anchor(self, url: QtCore.QUrl) -> None:
        if url.scheme().lower() in {"http", "https", "mailto"}:
            QtGui.QDesktopServices.openUrl(url)
        else:
            self._browser.setSource(url)

    def _go_back(self) -> None:
        self._browser.backward()

    def _go_forward(self) -> None:
        self._browser.forward()

    def _find(self) -> None:
        text = self._search.text().strip()
        if not text:
            return
        if not self._browser.find(text):
            cursor = self._browser.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start
                                if IS_QT6 else QtGui.QTextCursor.Start)
            self._browser.setTextCursor(cursor)
            self._browser.find(text)

    def _open_external(self) -> None:
        url = self._browser.source()
        if url.isValid():
            QtGui.QDesktopServices.openUrl(url)
