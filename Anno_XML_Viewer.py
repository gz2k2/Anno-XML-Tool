import sys
import os
import re
import multiprocessing
from queue import Empty
from urllib.request import urlopen
from rda_extractor import (NET_CONSOLE_EXIT_CODE, extract_gamefiles as run_rda_extract,
                           extract_anno1800_gamefiles)
from guid_compare import GuidCompareLoader
from guid_diff_view import (DiffPane, SyncScrollGroup, set_diff_texts,
                            format_stats)
import guid_diff_view
import theme_manager
import anno_game
from anno_loader import AnnoLoader
from datetime import datetime
import xml.etree.ElementTree as ET
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, 
                             QPushButton, QFileDialog, QLabel, QMessageBox, QHeaderView, QTextEdit, 
                             QSplitter, QMessageBox, QTreeWidget, QTreeWidgetItem, 
                             QMenu, QDialog, QListWidget, QListWidgetItem, 
                             QDialogButtonBox, QComboBox, QTabWidget, QGroupBox,
                             QCheckBox, QProgressDialog, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QUrl, QTimer
from PyQt6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QAction,
                         QPixmap, QIcon, QTextCursor)
from PyQt6.QtGui import QDesktopServices

APP_NAME = "Anno XML Viewer by gz2k2"
GITHUB_PROJECT_URL = "https://github.com/gz2k2/Anno-XML-Tool"
GITHUB_VERSION_URL = GITHUB_PROJECT_URL + "/blob/main/version.txt"
GITHUB_VERSION_RAW_URL = "https://raw.githubusercontent.com/gz2k2/Anno-XML-Tool/main/version.txt"
GITHUB_URL_RELEASE = "https://github.com/gz2k2/Anno-XML-Tool/releases"

# XML base folders are kept per game. The games themselves live in
# anno117.py / anno1800.py, so adding a title does not touch this file.
XML_PATH_GROUPS = anno_game.path_groups()

# Union of the buff/effect tags all games care about. The per-game lists
# live in the anno_* modules.
DEFAULT_BUFF_FILTER_TAGS = sorted(
    {tag for game in anno_game.all_games() for tag in game.default_buff_tags}
)


################################################################################
# UTILITY FUNCTIONS
################################################################################

def resource_path(relative_path: str) -> str:

    """
    Resolve paths both in dev (source tree) and in PyInstaller onefile bundles.
    """

    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)


def indent(elem, level=0):

    i = "\n" + level * "  "

    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "

        if not elem.tail or not elem.tail.strip():
            elem.tail = i

        for child in elem:
            indent(child, level + 1)

        if not child.tail or not child.tail.strip():
            child.tail = i

    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def rda_extraction_worker(result_queue, app_dir, game_name, game_folder, output_folder):
    """Run archive extraction outside the UI process and report its state."""
    try:
        if game_name == "Anno 1800":
            def report(message, current, total):
                result_queue.put(("progress", message, current, total))

            args, returncode, output = extract_anno1800_gamefiles(
                app_dir, game_folder, output_folder, progress_callback=report
            )
        else:
            archive = os.path.join(game_folder, "maindata", "config.rda")
            if not os.path.isfile(archive):
                raise FileNotFoundError(archive)
            result_queue.put(("progress", "Extracting config.rda...", 0, 0))
            args, returncode, output = run_rda_extract(app_dir, archive, output_folder)
        result_queue.put(("finished", args, returncode, output))
    except Exception as exc:
        result_queue.put(("error", type(exc).__name__, str(exc)))


def version_key(version):
    """Convert release versions such as 0.11.3-beta into comparable tuples."""
    numbers = [int(part) for part in re.findall(r"\d+", version)]
    numbers.extend([0] * (3 - len(numbers)))
    # A prerelease is older than the matching final release.
    return tuple(numbers[:3]) + (0 if "-" not in version else -1,)



################################################################################
# UI COMPONENTS
################################################################################

class XMLHighlighter(QSyntaxHighlighter):
    """Basic XML syntax highlighting that follows the active theme.

    The colours used to be hard-coded for a dark editor. On a light theme the
    body text (#dcdcdc) was practically invisible against a white background,
    so the palette is now supplied by the theme manager.
    """

    def __init__(self, parent=None, colors=None):

        super().__init__(parent)

        self.styles = {}
        self.set_colors(colors or theme_manager.xml_highlight_colors(
            theme_manager.ANNO_DARK))

    def set_colors(self, colors, rehighlight=False):
        """Install a colour palette produced by ``xml_highlight_colors``."""

        tag_format = QTextCharFormat()
        tag_format.setForeground(colors["tag"])
        tag_format.setFontWeight(QFont.Weight.Bold)
        self.styles["tag"] = tag_format

        attr_format = QTextCharFormat()
        attr_format.setForeground(colors["attr"])
        self.styles["attr"] = attr_format

        value_format = QTextCharFormat()
        value_format.setForeground(colors["value"])
        self.styles["value"] = value_format

        comment_format = QTextCharFormat()
        comment_format.setForeground(colors["comment"])
        self.styles["comment"] = comment_format

        text_format = QTextCharFormat()
        text_format.setForeground(colors["text"])
        self.styles["text"] = text_format

        if rehighlight:
            self.rehighlight()

    def highlightBlock(self, text):

        if not text:
            return

        for match in re.finditer(r"<!--.*?-->", text):
            self.setFormat(match.start(), match.end() - match.start(),
                           self.styles["comment"])
            return

        for match in re.finditer(r"<(/?[\w:]+)", text):
            self.setFormat(match.start(), match.end() - match.start(),
                           self.styles["tag"])

        for match in re.finditer(r">([^<]+)<", text):
            self.setFormat(match.start(1), match.end(1) - match.start(1),
                           self.styles["text"])


class VersionCheckWorker(QThread):
    """Fetch the published version without blocking application startup."""

    update_available = pyqtSignal(str)

    def __init__(self, current_version, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        try:
            with urlopen(GITHUB_VERSION_RAW_URL, timeout=5) as response:
                latest_version = response.read().decode("utf-8").strip()
            if latest_version and version_key(latest_version) > version_key(self.current_version):
                self.update_available.emit(latest_version)
        except Exception:
            # An unavailable network connection must never prevent startup.
            pass



################################################################################
# BACKGROUND WORKERS
################################################################################

# AnnoLoader lives in anno_loader.py and delegates every game-specific rule
# to anno117.py / anno1800.py.


################################################################################
# MAIN APPLICATION
################################################################################

class _KofiLinkLabel(QLabel):
    
    def __init__(self, pixmap: QPixmap, url: str, parent=None):
        
        super().__init__(parent)

        self._url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setPixmap(pixmap)
        self.setScaledContents(False)

    def mousePressEvent(self, event):
        QDesktopServices.openUrl(QUrl(self._url))
        super().mousePressEvent(event)


class AnnoModTool(QMainWindow):

    def append_debug_log(self, message):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.debug_console.append(f"[{timestamp}] {message}")

    def _load_xml_paths(self):

        saved_paths = self.settings.value("Paths/xml_paths", [])
        if isinstance(saved_paths, str):
            saved_paths = [saved_paths] if saved_paths else []
        elif saved_paths is None:
            saved_paths = []

        legacy_path = str(self.settings.value("Paths/xml_path", "") or "").strip()
        if legacy_path and legacy_path not in saved_paths:
            saved_paths.append(legacy_path)

        return list(dict.fromkeys(str(path) for path in saved_paths if str(path).strip()))

    def _load_xml_path_groups(self):
        """Read the per-game XML folder lists, migrating the old flat list."""
        groups = {key: [] for key, _label, _settings_key in XML_PATH_GROUPS}
        stored_anything = False

        for key, _label, settings_key in XML_PATH_GROUPS:
            stored = self.settings.value(settings_key, [])
            if isinstance(stored, str):
                stored = [stored] if stored else []
            elif stored is None:
                stored = []
            cleaned = [str(path).strip() for path in stored if str(path).strip()]
            if cleaned:
                stored_anything = True
            groups[key] = list(dict.fromkeys(cleaned))

        if not stored_anything:
            # Migration from the single "Paths/xml_paths" list. Anything that
            # mentions 1800 goes to Anno 1800, everything else to Anno 117.
            for path in self._load_xml_paths():
                key = "anno1800" if "1800" in path.lower() else "anno117"
                groups[key].append(path)
            for key in groups:
                groups[key] = list(dict.fromkeys(groups[key]))

        return groups

    def _flat_xml_paths(self):
        """All configured folders, Anno 117 first, without duplicates."""
        paths = [path
                 for key, _label, _settings_key in XML_PATH_GROUPS
                 for path in self.xml_path_groups.get(key, [])]
        return list(dict.fromkeys(paths))

    def _current_xml_path_groups(self):
        """Read the folder lists back from their list widgets."""
        groups = {}
        for key, _label, _settings_key in XML_PATH_GROUPS:
            widget = self.list_xml_paths_by_group.get(key)
            if widget is None:
                groups[key] = list(self.xml_path_groups.get(key, []))
                continue
            paths = [widget.item(row).text().strip()
                     for row in range(widget.count())
                     if widget.item(row).text().strip()]
            groups[key] = list(dict.fromkeys(paths))
        return groups

    @staticmethod
    def _first_selectable_index(selector):
        """First real path entry, skipping group headers and separators."""
        model = selector.model()
        for index in range(selector.count()):
            item = model.item(index) if hasattr(model, "item") else None
            if item is not None and not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
                continue
            if selector.itemText(index).strip():
                return index
        return -1

    def _populate_path_selector(self, selector):
        """Fill a path combo box, grouped by game with readable headers."""
        selected_path = selector.currentText()
        selector.blockSignals(True)
        selector.clear()

        theme_key = getattr(self, "current_theme", theme_manager.ANNO_DARK)
        header_text = theme_manager.combo_header_color(theme_key)
        header_band = theme_manager.header_background(theme_key)

        for key, label, _settings_key in XML_PATH_GROUPS:
            paths = self.xml_path_groups.get(key, [])
            if not paths:
                continue

            selector.addItem(label)
            header = selector.model().item(selector.count() - 1)
            if header is not None:
                # The header must stay ENABLED. A disabled item is painted by
                # Qt with the QPalette.Disabled colour group, which ignores
                # any foreground brush set here and produces the washed-out
                # grey text. Dropping ItemIsSelectable keeps it unclickable
                # and skips it during keyboard navigation, while the normal
                # colour group - and therefore our brushes - stay in effect.
                header.setFlags(Qt.ItemFlag.ItemIsEnabled)
                header.setForeground(header_text)
                header.setBackground(header_band)
                header_font = header.font()
                header_font.setBold(True)
                header.setFont(header_font)
                header.setToolTip(f"{label} - configured under Settings > XML Settings")

            selector.addItems(paths)

        index = selector.findText(selected_path) if selected_path else -1
        selector.setCurrentIndex(index if index >= 0
                                 else self._first_selectable_index(selector))
        selector.blockSignals(False)

    def _save_xml_paths(self):

        self.xml_path_groups = self._current_xml_path_groups()
        self.xml_paths = self._flat_xml_paths()
        self._populate_path_selector(self.combo_xml_path)

        for key, _label, settings_key in XML_PATH_GROUPS:
            self.settings.setValue(settings_key, self.xml_path_groups[key])
        self.settings.setValue("Paths/xml_path", self.combo_xml_path.currentText())
        self._sync_guid_compare_paths()

    def _sync_guid_compare_paths(self):
        """Keep GUID Compare path selectors identical to the main XML selector."""
        if not hasattr(self, "compare_left_path"):
            return

        for selector in (self.compare_left_path, self.compare_right_path):
            self._populate_path_selector(selector)

    def on_xml_path_changed(self, index):

        if self.block_signals or index < 0:
            return

        folder = self.combo_xml_path.itemText(index)
        if folder and os.path.exists(folder):
            self.start_loading(folder)

    def remove_xml_path(self, group_key):
        """Remove the selected folder from one game's XML folder list."""
        widget = self.list_xml_paths_by_group.get(group_key)
        if widget is None:
            return

        row = widget.currentRow()
        if row < 0:
            return

        widget.takeItem(row)
        self._save_xml_paths()

    def _load_buff_filter_tags(self):

        saved_tags = self.settings.value("Buffs/tags", "")
        saved_tags = str(saved_tags).replace("\\n", "\n")
        tags = [tag.strip() for tag in re.split(r"[,\n]", saved_tags) if tag.strip()]

        return sorted(set(tags or DEFAULT_BUFF_FILTER_TAGS))

    @staticmethod
    def _watchlist_settings_key(game_key):
        return f"Watchlist/guids_{game_key}"

    def _read_guid_list(self, settings_key):
        stored = self.settings.value(settings_key, "")
        if isinstance(stored, list):
            guids = stored
        else:
            guids = str(stored).replace("\\n", "\n").splitlines()
        return list(dict.fromkeys(guid.strip() for guid in guids if guid.strip()))

    def _load_watchlist_groups(self):
        """Read the per-game watchlists, migrating the old shared list."""
        groups = {}
        stored_anything = False

        for game_key, _label, _settings_key in XML_PATH_GROUPS:
            guids = self._read_guid_list(self._watchlist_settings_key(game_key))
            if guids:
                stored_anything = True
            groups[game_key] = guids

        if not stored_anything:
            # Migration: the old shared "Watchlist/guids" belonged to whichever
            # folder was active back then.
            legacy = self._read_guid_list("Watchlist/guids")
            if legacy:
                saved_path = str(self.settings.value("Paths/xml_path", "") or "")
                groups[self._game_key_for_path(saved_path)] = legacy

        return groups

    def _active_watchlist_key(self):
        """Game key whose watchlist is currently shown."""
        game = getattr(self, "_active_game", None)
        if game is not None and getattr(game, "key", ""):
            return game.key
        combo = getattr(self, "combo_xml_path", None)
        return self._game_key_for_path(combo.currentText() if combo else "")

    @property
    def watchlist_guids(self):
        """Watchlist of the currently active game."""
        return self.watchlist_groups.setdefault(self._active_watchlist_key(), [])

    @watchlist_guids.setter
    def watchlist_guids(self, guids):
        self.watchlist_groups[self._active_watchlist_key()] = list(guids)

    def _save_watchlist_guids(self):
        key = self._active_watchlist_key()
        self.settings.setValue(self._watchlist_settings_key(key),
                               "\n".join(self.watchlist_groups.get(key, [])))
        self.settings.sync()

    def _reference_guid(self, tag, node):
        """Resolve a buff/effect reference using the active game's rules."""
        return self.active_game.reference_guid(tag, node)

    def _template_filter_refresh_from_assets(self, assets_db):

        if not assets_db:
            self._template_filter_selected = set()
            return

        self._all_template_names = sorted(list(set(info.get("template_name") for info in assets_db.values())))
        if "" in self._all_template_names:
            self._all_template_names = [t for t in self._all_template_names if t]

        # Start: alle ausgewählt
        self._template_filter_selected = set(self._all_template_names)

    def open_template_filter_popup(self):

        dlg = QDialog(self)
        dlg.setWindowTitle("Template Filter")
        dlg.resize(520, 520)

        layout = QVBoxLayout(dlg)

        info_lbl = QLabel("Select/Deselect Templates")
        info_lbl.setProperty("accentText", True)
        layout.addWidget(info_lbl)

        search_lbl = QLabel("Search")
        search_lbl.setProperty("accentText", True)
        layout.addWidget(search_lbl)

        search_input = QLineEdit()
        search_input.setPlaceholderText("Search templates...")
        layout.addWidget(search_input)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["", "Template"])
        table.setColumnWidth(0, 50)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)

        # Qt checkboxes need a direct widget per row
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(table)


        # Footer Buttons
        btn_row = QHBoxLayout()

        def set_all(checked: bool):

            for r in range(table.rowCount()):
                cb = table.cellWidget(r, 0)
                if cb is not None:
                    cb.setChecked(checked)

        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Deselect All")

        btn_all.clicked.connect(lambda: set_all(True))
        btn_none.clicked.connect(lambda: set_all(False))

        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addStretch()

        layout.addLayout(btn_row)

        dlg_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(dlg_buttons)

        current_selection = set(getattr(self, "_template_filter_selected", set()))

        def sync_selection():
            """Transfers the checkbox status of visible rows into the global selection."""
            for r in range(table.rowCount()):
                cb = table.cellWidget(r, 0)
                name_item = table.item(r, 1)
                if cb and name_item:
                    name = name_item.text()
                    if cb.isChecked():
                        current_selection.add(name)
                    else:
                        current_selection.discard(name)

        from PyQt6.QtWidgets import QCheckBox

        def rebuild_table():
            """Updates the table view based on the search term."""
            sync_selection()
            table.setRowCount(0)

            all_names = getattr(self, "_all_template_names", sorted(list(getattr(self, "_template_filter_selected", set()))))
            filter_text = (search_input.text() or "").strip().lower()

            if filter_text:
                visible_names = [n for n in all_names if filter_text in (n or "").lower()]
            else:
                visible_names = list(all_names)

            for t_name in visible_names:
                row = table.rowCount()
                table.insertRow(row)

                cb = QCheckBox()
                cb.setChecked(t_name in current_selection)
                table.setCellWidget(row, 0, cb)

                item = QTableWidgetItem(t_name)
                table.setItem(row, 1, item)

        search_input.textChanged.connect(lambda _t: rebuild_table())
        rebuild_table()

        def accept():
            sync_selection()
            self._template_filter_selected = set(current_selection)
            dlg.accept()


        dlg_buttons.accepted.connect(accept)
        dlg_buttons.rejected.connect(dlg.reject)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.apply_filter()

    def open_buff_filter_popup(self):

        dlg = QDialog(self)
        dlg.setWindowTitle("Buff / Effect Filter")
        dlg.resize(450, 400)

        layout = QVBoxLayout(dlg)

        info_lbl = QLabel("Select/Deselect categories")
        info_lbl.setProperty("accentText", True)
        layout.addWidget(info_lbl)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["", "Category"])
        table.setColumnWidth(0, 50)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(table)

        # Footer Buttons
        btn_row = QHBoxLayout()

        def set_all(checked: bool):
            for r in range(table.rowCount()):
                cb = table.cellWidget(r, 0)
                if cb is not None:
                    cb.setChecked(checked)

        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Deselect All")

        btn_all.clicked.connect(lambda: set_all(True))
        btn_none.clicked.connect(lambda: set_all(False))

        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addStretch()

        layout.addLayout(btn_row)

        dlg_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(dlg_buttons)

        current_selection = set(getattr(self, "_buff_filter_selected", set()))

        from PyQt6.QtWidgets import QCheckBox

        for tag in self._buff_filter_tags:
            row = table.rowCount()
            table.insertRow(row)

            cb = QCheckBox()
            cb.setChecked(tag in current_selection)
            table.setCellWidget(row, 0, cb)

            item = QTableWidgetItem(tag)
            table.setItem(row, 1, item)

        def accept():
            new_selection = {table.item(r, 1).text() for r in range(table.rowCount()) if table.cellWidget(r, 0).isChecked()}
            self._buff_filter_selected = new_selection
            dlg.accept()

        dlg_buttons.accepted.connect(accept)
        dlg_buttons.rejected.connect(dlg.reject)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.update_buffs_preview()

    def __init__(self):

        super().__init__()

        app_version = "0.0.0"

        try:
            with open(resource_path("version.txt"), "r", encoding="utf-8") as v_file:
                app_version = v_file.read().strip()
        except Exception:
            pass

        self.app_version = app_version
        self.setWindowTitle(f"{APP_NAME} v{app_version}")
        self.setWindowIcon(QIcon(resource_path("data/ui/AnnoXMLTool.ico")))
        self.resize(1280, 850)

        # Determine the path to config.ini in the program directory.
        # Requires sys.executable for persistent data in a onefile EXE.
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        config_path = os.path.join(base_dir, "config.ini")
        self.settings = QSettings(config_path, QSettings.Format.IniFormat)

        self.list_xml_paths_by_group = {}
        self.xml_path_groups = self._load_xml_path_groups()
        self.xml_paths = self._flat_xml_paths()
        saved_path = self.settings.value("Paths/xml_path", "")
        
        self.current_theme = str(
            self.settings.value("UI/theme", theme_manager.ANNO_DARK) or theme_manager.ANNO_DARK
        )
        self.current_theme = self.apply_theme(self.current_theme)

        self._active_game = None
        self.assets_db, self.templates_db, self.languages_db = {}, {}, {}
        self.template_library = {}
        self.structure_catalog_list = []
        self.watchlist_groups = self._load_watchlist_groups()
        self.current_xml_root = None
        self.block_signals = False

        self.statusBar().showMessage("Ready")

        container = QWidget()
        self.setCentralWidget(container)

        main_layout = QVBoxLayout(container)

        # NAV BAR ######################################################################

        nav = QHBoxLayout()

        self.combo_lang = QComboBox()
        self.combo_lang.setFixedWidth(140)
        self.search = QLineEdit()
        self.search.setPlaceholderText("enter one or more terms, use '-' prefix for exclusion (e.g. 'tech civic -gate')")

        # Template-Filter (statt Combobox: Button + Popup)
        self.btn_template_filter = QPushButton("Template Filter...")
        self.lbl_filter = QLabel("Search-Filter")
        self.lbl_filter.setProperty("accentText", True)
        self.cb_search_main_only = QCheckBox("Search only GUID Text")
        # Colours come from the theme; only the geometry is fixed here.
        self.cb_search_main_only.setStyleSheet("""
            QCheckBox { font-size: 10px; padding-left: 8px; }
            QCheckBox::indicator { width: 12px; height: 12px; }
        """)
        self.cb_search_main_only.setToolTip("When checked, search is limited to GUID, Display Name, and Template.\nWhen unchecked, all text content within the asset is searched.")
        self.cb_search_main_only.setChecked(True)
        self.btn_template_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._buff_filter_tags = self._load_buff_filter_tags()
        self._buff_filter_selected = set(self._buff_filter_tags)
        self.btn_buff_filter = QPushButton("Filter…")
        self.lbl_buff_filter = QLabel("Buffs/Effects")
        self.lbl_buff_filter.setProperty("accentText", True)
        self.btn_buff_filter.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_export = QPushButton("EXPORT XML")
        self.btn_export.setStyleSheet("background-color: #1b5e20; color: white; font-weight: bold; padding: 4px 15px;")
        
        export_columns_layout = QHBoxLayout()

        export_xml_layout = QVBoxLayout()
        export_xml_layout.addWidget(self.btn_export)

        export_mod_layout = QVBoxLayout()

        # Ko-fi image link (below "EXPORT MOD")
        btn_size = self.btn_export.sizeHint()
        btn_w = max(1, btn_size.width())
        btn_h = max(1, btn_size.height())

        kofi_label = _KofiLinkLabel(
            pixmap=QPixmap(),
            url="https://ko-fi.com/gz2k2",
            parent=self,
        )
        kofi_label.setFixedSize(btn_w, btn_h)

        kofi_path = resource_path("data/ui/kofi5.webp")
        if os.path.exists(kofi_path):
            pix = QPixmap(kofi_path)
            if not pix.isNull():
                kofi_label.setPixmap(
                    pix.scaled(
                        btn_w,
                        btn_h,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

        github_button = QPushButton("GitHub")
        github_button.setFixedSize(btn_w, btn_h)
        github_button.setToolTip("Open the Anno XML Tool project on GitHub")
        github_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_PROJECT_URL)))
        support_buttons_layout = QHBoxLayout()
        support_buttons_layout.setSpacing(4)
        support_buttons_layout.addWidget(kofi_label)
        support_buttons_layout.addWidget(github_button)
        export_mod_layout.addLayout(support_buttons_layout)

        export_columns_layout.addLayout(export_xml_layout)
        export_columns_layout.addLayout(export_mod_layout)

        nav.addWidget(self.combo_lang)

        self.combo_xml_path = QComboBox()
        self.combo_xml_path.setFixedWidth(300)
        self._populate_path_selector(self.combo_xml_path)
        saved_path_index = self.combo_xml_path.findText(str(saved_path).strip())
        if saved_path_index >= 0:
            self.combo_xml_path.setCurrentIndex(saved_path_index)
        self.combo_xml_path.setToolTip("Select the XML data folder to use")

        nav.addWidget(self.search)

        filter_vbox = QVBoxLayout()
        filter_vbox.setSpacing(0)
        filter_vbox.addWidget(self.lbl_filter)
        filter_vbox.addWidget(self.cb_search_main_only)
        nav.addLayout(filter_vbox)

        nav.addWidget(self.btn_template_filter)
        nav.addWidget(self.lbl_buff_filter)
        nav.addWidget(self.btn_buff_filter)
        nav.addLayout(export_columns_layout)

        main_layout.addLayout(nav)

        language_row = QHBoxLayout()
        language_row.addWidget(self.combo_xml_path)
        language_row.addStretch()
        main_layout.addLayout(language_row)

        # TABS #########################################################################

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # TAB 1: ASSET VIEWER ##########################################################

        self.editor_tab = QWidget()
        self.tabs.addTab(self.editor_tab, "Asset Viewer")

        ed_layout = QVBoxLayout(self.editor_tab)
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)

        self.top_h_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem("GUID"))
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem("Display Name"))
        self.table.setHorizontalHeaderItem(2, QTableWidgetItem("Template"))
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self.update_header_styling)
        self.table.horizontalHeader().setSortIndicator(1, Qt.SortOrder.AscendingOrder)
        self.update_header_styling(1, Qt.SortOrder.AscendingOrder)

       # Column split 1:3:2 (GUID : Name : Template)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        
        # Initiale Breiten setzen
        self.table.setColumnWidth(0, 80 )
        self.table.setColumnWidth(1, 500)
        self.table.setColumnWidth(2, 150)

        # Rückwärtssuche Pane
        rev_container = QWidget()
        rev_layout = QVBoxLayout(rev_container)
        rev_layout.setContentsMargins(0, 0, 0, 0)
        rev_layout.setSpacing(0)
        rev_header = QLabel(" REFERENCES")
        rev_header.setProperty("sectionHeader", True)
        self.reverse_search_table = QTableWidget(0, 3)
        self.reverse_search_table.setHorizontalHeaderLabels(["GUID", "Display Name", "Template"])
        self.reverse_search_table.verticalHeader().setVisible(False)

        # Column split 1:3:2 (GUID : Name : Template)
        rev_header_view = self.reverse_search_table.horizontalHeader()
        rev_header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        rev_header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        rev_header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)

        self.reverse_search_table.setColumnWidth(0, 80)
        self.reverse_search_table.setColumnWidth(1, 500)
        self.reverse_search_table.setColumnWidth(2, 150)

        self.reverse_search_table.horizontalHeader().sortIndicatorChanged.connect(self.update_header_styling)
        self.reverse_search_table.horizontalHeader().setSortIndicator(1, Qt.SortOrder.AscendingOrder)
        self.update_header_styling(1, Qt.SortOrder.AscendingOrder, target_table=self.reverse_search_table)

        self.reverse_search_table.setSortingEnabled(True)
        self.reverse_search_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reverse_search_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        rev_layout.addWidget(rev_header)
        rev_layout.addWidget(self.reverse_search_table)

        watch_container = QWidget()
        watch_layout = QVBoxLayout(watch_container)
        watch_layout.setContentsMargins(0, 0, 0, 0)
        watch_layout.setSpacing(0)

        watch_header_layout = QHBoxLayout()
        watch_header_layout.setContentsMargins(0, 0, 0, 0)
        watch_header_layout.setSpacing(4)

        self.watch_header = QLabel(" WATCHLIST")
        watch_header = self.watch_header
        watch_header.setProperty("sectionHeader", True)

        self.btn_watch_add = QPushButton("+")
        self.btn_watch_add.setFixedWidth(32)
        self.btn_watch_add.setToolTip("Add selected asset to watchlist")

        self.btn_watch_remove = QPushButton("-")
        self.btn_watch_remove.setFixedWidth(32)
        self.btn_watch_remove.setToolTip("Remove selected watchlist entry")

        watch_header_layout.addWidget(watch_header)
        watch_header_layout.addWidget(self.btn_watch_add)
        watch_header_layout.addWidget(self.btn_watch_remove)

        self.watchlist_table = QTableWidget(0, 2)
        self.watchlist_table.setHorizontalHeaderLabels(["GUID", "Display Name"])
        self.watchlist_table.verticalHeader().setVisible(False)
        self.watchlist_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.watchlist_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.watchlist_table.setColumnWidth(0, 80)
        watch_header_view = self.watchlist_table.horizontalHeader()
        watch_header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        watch_header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        watch_layout.addLayout(watch_header_layout)
        watch_layout.addWidget(self.watchlist_table)

        self.top_h_splitter.addWidget(self.table)
        self.top_h_splitter.addWidget(rev_container)
        self.top_h_splitter.addWidget(watch_container)
        self.top_h_splitter.setSizes([700, 400, 260])
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.prop_tree = QTreeWidget()
        self.prop_tree.setHeaderLabels(["Property", "Value", "Text"])

        # Spaltenbreiten definieren
        self.prop_tree.setColumnWidth(0, 200)
        self.prop_tree.setColumnWidth(1, 220)
        self.prop_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # XML Pane (Mitte)
        xml_container = QWidget()
        xml_layout = QVBoxLayout(xml_container)

        xml_layout.setContentsMargins(0, 0, 0, 0)
        xml_layout.setSpacing(0)

        xml_header = QLabel(" XML")
        xml_header.setProperty("sectionHeader", True)
        
        self.xml_editor = QTextEdit()
        self.xml_editor.setReadOnly(True)
        
        xml_layout.addWidget(xml_header)
        xml_layout.addWidget(self.xml_editor)

        # BUFFS Pane (Rechts)
        buff_container = QWidget()
        buff_layout = QVBoxLayout(buff_container)

        buff_layout.setContentsMargins(0, 0, 0, 0)
        buff_layout.setSpacing(0)

        buff_header = QLabel(" BUFFS / EFFECTS")
        buff_header.setProperty("sectionHeader", True)
        
        self.buff_view = QTextEdit()
        self.buff_view.setReadOnly(True)
        
        buff_layout.addWidget(buff_header)
        buff_layout.addWidget(self.buff_view)

        self.h_splitter.addWidget(self.prop_tree)
        self.h_splitter.addWidget(xml_container)
        self.h_splitter.addWidget(buff_container)

        self.h_splitter.setSizes([400, 200, 200])
        
        self.v_splitter.addWidget(self.top_h_splitter)
        self.v_splitter.addWidget(self.h_splitter)

        ed_layout.addWidget(self.v_splitter)
        self.v_splitter.setSizes([200, 600])

        # TAB 3: TEMPLATES ###########################################################

        self.templates_tab = QWidget()
        self.tabs.addTab(self.templates_tab, "Templates")
        templates_layout = QVBoxLayout(self.templates_tab)

        self.templates_filter = QLineEdit()
        self.templates_filter.setPlaceholderText("Search templates...")
        templates_layout.addWidget(self.templates_filter)

        self.templates_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.templates_list = QListWidget()
        self.templates_preview = QTextEdit()
        self.templates_preview.setReadOnly(True)

        self.templates_splitter.addWidget(self.templates_list)
        self.templates_splitter.addWidget(self.templates_preview)

        templates_layout.addWidget(self.templates_splitter)
        self.templates_filter.textChanged.connect(self.filter_templates)
        self.templates_list.itemClicked.connect(self.preview_template)

        # TAB 4: GUID COMPARE #########################################################

        self.guid_compare_tab = QWidget()
        self.tabs.addTab(self.guid_compare_tab, "GUID Compare")
        compare_layout = QVBoxLayout(self.guid_compare_tab)
        compare_layout.setContentsMargins(6, 6, 6, 6)
        compare_layout.setSpacing(6)

        # The toolbar lives in its own container so it can be pinned to the top
        # with a fixed height. Every remaining pixel then goes to the panes.
        compare_toolbar = QWidget()
        compare_search_row = QHBoxLayout(compare_toolbar)
        compare_search_row.setContentsMargins(0, 0, 0, 0)
        compare_search_row.setSpacing(6)
        self.compare_watchlist = QComboBox()
        self.compare_watchlist.setMinimumWidth(260)
        self.compare_watchlist.setToolTip("Select a GUID from the watchlist")
        self.compare_guid_input = QLineEdit()
        self.compare_guid_input.setPlaceholderText("Enter a GUID to compare...")
        self.btn_compare_guid = QPushButton("Compare GUID")
        compare_search_row.addWidget(QLabel("Watchlist:"))
        compare_search_row.addWidget(self.compare_watchlist)
        compare_search_row.addWidget(self.compare_guid_input)
        compare_search_row.addWidget(self.btn_compare_guid)

        # Diff navigation + summary
        self.btn_diff_prev = QPushButton("\u25c0 Prev diff")
        self.btn_diff_next = QPushButton("Next diff \u25b6")
        self.btn_diff_prev.setToolTip("Jump to the previous block of differences")
        self.btn_diff_next.setToolTip("Jump to the next block of differences")
        self.btn_diff_prev.setEnabled(False)
        self.btn_diff_next.setEnabled(False)
        self.cb_diff_ignore_ws = QCheckBox("Ignore whitespace")
        self.cb_diff_ignore_ws.setChecked(True)
        self.cb_diff_ignore_ws.setToolTip(
            "Compare lines without leading/trailing whitespace, so pure\n"
            "indentation changes are not reported as differences."
        )
        self.lbl_diff_stats = QLabel("")
        self.lbl_diff_stats.setProperty("accentText", True)
        compare_search_row.addWidget(self.btn_diff_prev)
        compare_search_row.addWidget(self.btn_diff_next)
        compare_search_row.addWidget(self.cb_diff_ignore_ws)
        compare_search_row.addWidget(self.lbl_diff_stats)
        compare_search_row.addStretch()

        compare_toolbar.setSizePolicy(QSizePolicy.Policy.Preferred,
                                      QSizePolicy.Policy.Fixed)
        # Stretch 0: the row never grows beyond its own size hint.
        compare_layout.addWidget(compare_toolbar, 0)

        compare_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.compare_left_path = QComboBox()
        self.compare_right_path = QComboBox()
        for selector in (self.compare_left_path, self.compare_right_path):
            self._populate_path_selector(selector)
            selector.setCurrentText(self.combo_xml_path.currentText())
        for selector in (self.compare_left_path, self.compare_right_path):
            selector.setSizePolicy(QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Fixed)

        left_compare_panel = QWidget()
        left_compare_layout = QVBoxLayout(left_compare_panel)
        left_compare_layout.setContentsMargins(0, 0, 0, 0)
        left_compare_layout.setSpacing(2)
        left_compare_layout.addWidget(self.compare_left_path, 0)
        self.compare_left_xml = DiffPane()
        self.compare_left_xml.set_message("Enter a GUID to compare.")
        left_compare_layout.addWidget(self.compare_left_xml, 1)

        right_compare_panel = QWidget()
        right_compare_layout = QVBoxLayout(right_compare_panel)
        right_compare_layout.setContentsMargins(0, 0, 0, 0)
        right_compare_layout.setSpacing(2)
        right_compare_layout.addWidget(self.compare_right_path, 0)
        self.compare_right_xml = DiffPane()
        self.compare_right_xml.set_message("Enter a GUID to compare.")
        right_compare_layout.addWidget(self.compare_right_xml, 1)

        compare_splitter.addWidget(left_compare_panel)
        compare_splitter.addWidget(right_compare_panel)
        compare_splitter.setChildrenCollapsible(False)
        compare_splitter.setHandleWidth(6)
        # Keep both halves equal when the window is resized.
        compare_splitter.setStretchFactor(0, 1)
        compare_splitter.setStretchFactor(1, 1)
        compare_splitter.setSizes([600, 600])
        # Stretch 1: the splitter absorbs the whole remaining tab height.
        compare_layout.addWidget(compare_splitter, 1)

        # Both panes always hold the same number of rows, so a 1:1 scroll
        # mapping keeps them aligned.
        self._compare_sync = SyncScrollGroup(self.compare_left_xml,
                                             self.compare_right_xml)

        self._guid_compare_request_id = 0
        self._guid_compare_workers = []
        self._guid_compare_results = {}
        self._diff_blocks = []
        self._diff_cursor = -1
        self._refresh_compare_watchlist()
        self.compare_watchlist.currentIndexChanged.connect(self._select_compare_watchlist_guid)
        self.compare_guid_input.returnPressed.connect(self.compare_guid)
        self.btn_compare_guid.clicked.connect(self.compare_guid)
        self.compare_left_path.currentIndexChanged.connect(lambda _index: self.compare_guid())
        self.compare_right_path.currentIndexChanged.connect(lambda _index: self.compare_guid())
        self.btn_diff_prev.clicked.connect(lambda: self._step_diff(-1))
        self.btn_diff_next.clicked.connect(lambda: self._step_diff(1))
        self.cb_diff_ignore_ws.toggled.connect(self._rerender_guid_compare)

        # TAB 5: STRUKTUR BIBLIOTHEK ###################################################

        self.lib_tab = QWidget()
        self.tabs.addTab(self.lib_tab, "Structure Library")   
        lib_layout = QVBoxLayout(self.lib_tab)

        self.lib_filter = QLineEdit()
        self.lib_filter.setPlaceholderText("Search in paths...")
        lib_layout.addWidget(self.lib_filter)

        self.lib_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.lib_list = QListWidget()
        self.lib_preview = QTextEdit()
        self.lib_preview.setReadOnly(True)

        self.lib_splitter.addWidget(self.lib_list)
        self.lib_splitter.addWidget(self.lib_preview)

        lib_layout.addWidget(self.lib_splitter)
        self.lib_filter.textChanged.connect(self.filter_library)
        self.lib_list.itemClicked.connect(self.preview_library_item)

        # TAB 5: ENGINE LOG ############################################################

        self.debug_console = QTextEdit()
        self.debug_console.setReadOnly(True)
        self.tabs.addTab(self.debug_console, "Engine Log")

        # TAB 6: EINSTELLUNGEN #########################################################

        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        set_layout = QVBoxLayout(self.settings_tab)
        set_layout.setContentsMargins(6, 6, 6, 6)

        # Settings are split into sub-tabs so each page stays short enough to
        # be read without scrolling.
        self.settings_tabs = QTabWidget()
        # Flatter tabs than the main bar so the nesting is visually obvious.
        # Flatter than the main tab bar; the accent is set by apply_theme().
        self.settings_tabs.setStyleSheet(
            "QTabBar::tab { padding: 6px 16px; font-weight: normal; }"
        )
        set_layout.addWidget(self.settings_tabs)

        # --- SETTINGS > GENERAL ---------------------------------------------
        self.settings_general_tab = QWidget()
        self.settings_tabs.addTab(self.settings_general_tab, "General")
        general_layout = QVBoxLayout(self.settings_general_tab)
        general_layout.setContentsMargins(10, 10, 10, 10)
        general_layout.setSpacing(10)

        appearance_group = QGroupBox("Appearance")
        appearance_layout = QHBoxLayout(appearance_group)
        self.combo_theme = QComboBox()
        self.combo_theme.setMinimumWidth(220)
        for theme_key, theme_label in theme_manager.list_themes():
            self.combo_theme.addItem(theme_label, theme_key)
        theme_index = self.combo_theme.findData(self.current_theme)
        if theme_index >= 0:
            self.combo_theme.setCurrentIndex(theme_index)
        self.combo_theme.setToolTip(
            "Colour scheme of the application.\n"
            "Additional themes require the optional 'qt-themes' package."
        )
        self.combo_theme.currentIndexChanged.connect(self._on_theme_selected)
        appearance_layout.addWidget(QLabel("Theme:"))
        appearance_layout.addWidget(self.combo_theme)
        if not theme_manager.qt_themes_available():
            hint = QLabel(theme_manager.unavailable_reason())
            hint.setEnabled(False)
            hint.setWordWrap(True)
            appearance_layout.addWidget(hint, 1)
        appearance_layout.addStretch()

        language_group = QGroupBox("Default Language")
        language_group_layout = QHBoxLayout(language_group)
        self.combo_default_lang = QComboBox()
        self.combo_default_lang.setFixedWidth(140)
        self.combo_default_lang.setToolTip(
            "Language preselected in the toolbar when the application starts"
        )
        language_group_layout.addWidget(QLabel("Default Language:"))
        language_group_layout.addWidget(self.combo_default_lang)
        language_group_layout.addStretch()
        general_layout.addWidget(language_group)
        general_layout.addWidget(appearance_group)

        game_folders_group = QGroupBox("Game Folders")
        game_folders_layout = QVBoxLayout(game_folders_group)
        self.edit_anno117_folder = self._create_folder_setting_row(
            game_folders_layout, "Anno 117 Folder:", "Paths/anno117_folder",
            "Select Anno 117 root folder")
        self._add_extract_button(game_folders_layout, "Anno 117", self.edit_anno117_folder)
        self.edit_anno1800_folder = self._create_folder_setting_row(
            game_folders_layout, "Anno 1800 Folder:", "Paths/anno1800_folder",
            "Select Anno 1800 root folder")
        self._add_extract_button(game_folders_layout, "Anno 1800", self.edit_anno1800_folder)
        general_layout.addWidget(game_folders_group)

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setFixedWidth(200)
        self.btn_save.setToolTip("Save all settings from every tab")
        self.btn_save.clicked.connect(self.save_settings)
        general_layout.addWidget(self.btn_save)
        general_layout.addStretch()

        # --- SETTINGS > XML SETTINGS ----------------------------------------
        self.settings_xml_tab = QWidget()
        self.settings_tabs.addTab(self.settings_xml_tab, "XML Settings")
        xml_settings_layout = QVBoxLayout(self.settings_xml_tab)
        xml_settings_layout.setContentsMargins(10, 10, 10, 10)
        xml_settings_layout.setSpacing(10)

        # One folder list per game, each with its own Browse/Remove buttons.
        self.list_xml_paths_by_group = {}
        for group_key, group_label, _settings_key in XML_PATH_GROUPS:
            path_group = QGroupBox(group_label)
            path_layout = QVBoxLayout(path_group)

            path_list = QListWidget()
            path_list.addItems(self.xml_path_groups.get(group_key, []))
            path_list.setMinimumHeight(90)
            path_list.setToolTip(
                f"Extracted XML folders used as {group_label}.\n"
                "They appear grouped in the folder selector of the toolbar."
            )
            path_layout.addWidget(path_list)

            path_buttons_layout = QHBoxLayout()
            btn_browse = QPushButton("Browse...")
            btn_browse.setFixedWidth(80)
            btn_browse.clicked.connect(
                lambda _checked=False, key=group_key: self.browse_path_settings(key)
            )
            btn_remove = QPushButton("Remove Selected")
            btn_remove.clicked.connect(
                lambda _checked=False, key=group_key: self.remove_xml_path(key)
            )
            path_buttons_layout.addWidget(btn_browse)
            path_buttons_layout.addWidget(btn_remove)
            path_buttons_layout.addStretch()
            path_layout.addLayout(path_buttons_layout)

            self.list_xml_paths_by_group[group_key] = path_list
            xml_settings_layout.addWidget(path_group)

        buff_tags_group = QGroupBox("Buff/Effect XML tags")
        buff_tags_layout = QVBoxLayout(buff_tags_group)
        self.list_buff_filter_tags = QListWidget()
        self.list_buff_filter_tags.setMinimumHeight(180)
        self.list_buff_filter_tags.setToolTip(
            "XML tags scanned for linked assets in the Buffs/Effects pane.\n"
            "Double-click an entry to rename it."
        )
        for tag in self._buff_filter_tags:
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.list_buff_filter_tags.addItem(item)
        buff_tags_layout.addWidget(self.list_buff_filter_tags)

        tag_buttons_layout = QHBoxLayout()
        self.btn_add_buff_tag = QPushButton("Add Tag")
        self.btn_remove_buff_tag = QPushButton("Remove Selected Tag")
        self.btn_add_buff_tag.clicked.connect(self.add_buff_filter_tag)
        self.btn_remove_buff_tag.clicked.connect(self.remove_buff_filter_tag)
        tag_buttons_layout.addWidget(self.btn_add_buff_tag)
        tag_buttons_layout.addWidget(self.btn_remove_buff_tag)
        tag_buttons_layout.addStretch()
        buff_tags_layout.addLayout(tag_buttons_layout)
        xml_settings_layout.addWidget(buff_tags_group)

        # A second save button so the XML page does not force a tab switch.
        self.btn_save_xml = QPushButton("Save Settings")
        self.btn_save_xml.setFixedWidth(200)
        self.btn_save_xml.setToolTip("Save all settings from every tab")
        self.btn_save_xml.clicked.connect(self.save_settings)
        xml_settings_layout.addWidget(self.btn_save_xml)
        xml_settings_layout.addStretch()

        # SIGNALS ######################################################################

        self.search.textChanged.connect(self.apply_filter)
        self.cb_search_main_only.toggled.connect(self.apply_filter)
        self.combo_lang.currentIndexChanged.connect(self.on_language_changed)
        self.combo_xml_path.currentIndexChanged.connect(self.on_xml_path_changed)
        self.btn_template_filter.clicked.connect(self.open_template_filter_popup)
        self.btn_buff_filter.clicked.connect(self.open_buff_filter_popup)

        self.table.itemClicked.connect(self.load_asset_details)
        self.reverse_search_table.itemClicked.connect(self.load_asset_details)
        self.watchlist_table.itemClicked.connect(self.load_asset_details)
        self.btn_watch_add.clicked.connect(self.add_selected_to_watchlist)
        self.btn_watch_remove.clicked.connect(self.remove_selected_from_watchlist)
        self.btn_export.clicked.connect(self.export_mod)

        code_font = QFont("Consolas", 10)

        if not code_font.fixedPitch():
            code_font = QFont("Monospace", 10)

        self.xml_views = [
            self.xml_editor, 
            self.lib_preview, 
            self.templates_preview,
            self.buff_view,
            self.debug_console
        ]

        # Highlighter müssen referenziert bleiben, um Garbage Collection zu verhindern.
        self.highlighters = []
        xml_colors = theme_manager.xml_highlight_colors(self.current_theme)

        # DiffPane instances style themselves but still want XML highlighting.
        for view in (self.compare_left_xml, self.compare_right_xml):
            self.highlighters.append(XMLHighlighter(view.document(), xml_colors))

        for view in self.xml_views:
            view.setFont(code_font)
            view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            
            # Wir setzen das Stylesheet spezifisch für dieses Objekt
            view.setStyleSheet(self._code_view_stylesheet())
            
            if view != self.debug_console:
                highlighter = XMLHighlighter(view.document(), xml_colors)
                self.highlighters.append(highlighter)

        self.append_debug_log(f"[theme] {theme_manager.diagnostics()}")

        active_path = self.combo_xml_path.currentText()
        if active_path and os.path.exists(active_path):
            self.start_loading(active_path)

        QTimer.singleShot(0, self._start_version_check)


    # ASSET LOGIC ##################################################################

    def compare_guid(self):
        guid = self.compare_guid_input.text().strip()
        self._guid_compare_request_id += 1
        request_id = self._guid_compare_request_id
        self._guid_compare_results = {}
        self._diff_blocks = []
        self._diff_cursor = -1
        self.lbl_diff_stats.setText("")
        self.btn_diff_prev.setEnabled(False)
        self.btn_diff_next.setEnabled(False)

        # Ask searches from a previous request to stop so they do not keep
        # scanning large XML files in the background.
        for running in self._guid_compare_workers:
            running.requestInterruption()

        if not guid:
            self.compare_left_xml.set_message("Enter a GUID to compare.")
            self.compare_right_xml.set_message("Enter a GUID to compare.")
            return

        for side, folder, preview in (
            ("left", self.compare_left_path.currentText(), self.compare_left_xml),
            ("right", self.compare_right_path.currentText(), self.compare_right_xml),
        ):
            preview.set_message(f"Searching for GUID {guid}...")
            worker = GuidCompareLoader(request_id, folder, guid, self)

            # The search result arrives on `result`. `finished` is QThread's own
            # signal and is emitted only after run() has returned, so cleanup
            # must be tied to it - otherwise the thread object is destroyed
            # while it is still running.
            worker.result.connect(
                lambda result_id, _folder, content, compare_side=side, target=preview:
                self._show_guid_compare_result(result_id, compare_side, content, target)
            )
            worker.log.connect(lambda _id, message: self.append_debug_log(message))
            worker.finished.connect(
                lambda worker=worker: self._retire_guid_compare_worker(worker)
            )
            self._guid_compare_workers.append(worker)
            worker.start()

    def _retire_guid_compare_worker(self, worker):
        """Drop a finished worker. Only ever called from QThread.finished,
        i.e. after run() has returned, so deleteLater() is safe here."""
        if worker in self._guid_compare_workers:
            self._guid_compare_workers.remove(worker)
        worker.deleteLater()

    def _show_guid_compare_result(self, request_id, side, content, preview):
        """Collect one side of the comparison; render once both have arrived."""
        if request_id != self._guid_compare_request_id:
            return

        self._guid_compare_results[side] = content
        if len(self._guid_compare_results) == 2:
            self._highlight_guid_compare_differences()
        else:
            # Show the finished side right away; the diff replaces it later.
            preview.set_message(content)

    def _rerender_guid_compare(self):
        """Re-run the diff, e.g. after the whitespace option was toggled."""
        if len(self._guid_compare_results) == 2:
            self._highlight_guid_compare_differences()

    def _highlight_guid_compare_differences(self):
        stats = set_diff_texts(
            self.compare_left_xml,
            self.compare_right_xml,
            self._guid_compare_results["left"],
            self._guid_compare_results["right"],
            ignore_whitespace=self.cb_diff_ignore_ws.isChecked(),
        )
        self.lbl_diff_stats.setText(format_stats(stats))
        self._diff_blocks = self._collect_diff_blocks()
        self._diff_cursor = -1
        self.btn_diff_prev.setEnabled(bool(self._diff_blocks))
        self.btn_diff_next.setEnabled(bool(self._diff_blocks))

    def _collect_diff_blocks(self):
        """Group consecutive changed rows so navigation jumps block by block."""
        changed = sorted(set(self.compare_left_xml.change_rows())
                         | set(self.compare_right_xml.change_rows()))
        if not changed:
            return []
        blocks = [changed[0]]
        blocks.extend(current for previous, current in zip(changed, changed[1:])
                      if current != previous + 1)
        return blocks

    def _step_diff(self, direction):
        """Scroll both panes to the previous/next block of differences."""
        if not self._diff_blocks:
            self.statusBar().showMessage("No differences to navigate", 2000)
            return
        self._diff_cursor = (self._diff_cursor + direction) % len(self._diff_blocks)
        row = self._diff_blocks[self._diff_cursor]
        self.compare_left_xml.goto_row(row)
        self.compare_right_xml.goto_row(row)
        self.statusBar().showMessage(
            f"Difference {self._diff_cursor + 1} of {len(self._diff_blocks)}", 3000
        )

    def _code_view_stylesheet(self):
        """Stylesheet for the read-only XML views, derived from the theme."""
        colors = theme_manager.editor_colors(self.current_theme)
        background = colors["background"]
        foreground = colors["text"]
        border = QColor(
            (background.red() + foreground.red()) // 4 + background.red() // 2,
            (background.green() + foreground.green()) // 4 + background.green() // 2,
            (background.blue() + foreground.blue()) // 4 + background.blue() // 2,
        )
        return (f"background-color: {background.name()};"
                f" color: {foreground.name()};"
                f" border: 1px solid {border.name()};"
                f" selection-background-color: #264f78;")

    def _tree_colors(self):
        """Property-tree colours, darkened on light themes for readability."""
        cached = getattr(self, "_tree_color_cache", None)
        if cached and cached[0] == self.current_theme:
            return cached[1]

        background = theme_manager.editor_colors(self.current_theme)["background"]
        if theme_manager.is_dark(background):
            colors = {"group": QColor("#81c784"), "value": QColor("#64b5f6"),
                      "name": QColor("#ffd54f")}
        else:
            colors = {"group": QColor("#2e7d32"), "value": QColor("#1565c0"),
                      "name": QColor("#b26a00")}
        self._tree_color_cache = (self.current_theme, colors)
        return colors

    def apply_theme(self, theme_key):
        """Apply a theme to the window, the code views and the diff panes."""
        applied = theme_manager.apply_theme(self, theme_key)
        self.current_theme = applied

        colors = theme_manager.editor_colors(applied)
        guid_diff_view.apply_theme_colors(colors["background"], colors["text"])

        for pane in (getattr(self, "compare_left_xml", None),
                     getattr(self, "compare_right_xml", None)):
            if pane is not None:
                pane.refresh_theme()

        stylesheet = self._code_view_stylesheet()
        for view in getattr(self, "xml_views", []):
            view.setStyleSheet(stylesheet)

        self._tree_color_cache = None
        # XML syntax colours are baked into the highlighters.
        xml_colors = theme_manager.xml_highlight_colors(applied)
        for highlighter in getattr(self, "highlighters", []):
            highlighter.set_colors(xml_colors, rehighlight=True)
        # Group headers carry explicit brushes, so they must be rebuilt.
        if hasattr(self, "combo_xml_path"):
            self._populate_path_selector(self.combo_xml_path)
            self._sync_guid_compare_paths()
        if getattr(self, "settings_tabs", None) is not None:
            self.settings_tabs.setStyleSheet(
                "QTabBar::tab { padding: 6px 16px; font-weight: normal; }"
                f"QTabBar::tab:selected {{ border-bottom: 2px solid {colors['accent'].name()}; }}"
            )
        if getattr(self, "current_xml_root", None) is not None:
            self.refresh_ui_from_xml()

        # Re-rendering picks up the new diff colours.
        if len(getattr(self, "_guid_compare_results", {})) == 2:
            self._highlight_guid_compare_differences()

        return applied

    def _on_theme_selected(self, index):
        """Live-switch the theme when the user picks one in the settings."""
        if self.block_signals or index < 0:
            return
        theme_key = self.combo_theme.itemData(index)
        if not theme_key:
            return
        self.apply_theme(theme_key)
        self.settings.setValue("UI/theme", self.current_theme)
        self.settings.sync()
        self.statusBar().showMessage(
            f"Theme applied: {self.combo_theme.currentText()}", 3000
        )

    def _start_version_check(self):
        self._version_check_worker = VersionCheckWorker(self.app_version, self)
        self._version_check_worker.update_available.connect(self._show_update_available)
        self._version_check_worker.finished.connect(self._version_check_worker.deleteLater)
        self._version_check_worker.start()

    def _show_update_available(self, latest_version):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("Update available")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        box.setText(
            f"A newer version of Anno XML Viewer is available:<br><br> "
            f"<b>v{latest_version}</b><br><br>(you are using v{self.app_version}).<br><br>"
            f"<a href='{GITHUB_URL_RELEASE}'>View the latest version on GitHub</a>"
        )
        box.exec()

    def get_klartext(self, text, tag=None):
        """Resolve a value to a readable name.

        *tag* is the XML element the value came from and decides what the
        value may be resolved against:

        * quantity tags (<Amount>, <MaximumHitPoints>, <LineID>) reference
          nothing and are never resolved,
        * other tags may point at another asset,
        * only tags the game lists in ``text_id_tags`` are looked up in
          texts_*.xml.

        Without the tag check, <Amount>500</Amount> matched the asset with
        the GUID 500 and displayed its name.
        """
        if not text:
            return ""

        lang = self.combo_lang.currentText()
        if not lang:
            return ""

        lang_dict = self.languages_db.get(lang, {})

        # A pure quantity never references anything - stop before any lookup.
        if tag is not None and self._is_value_only(tag):
            return ""

        # A reference to another asset.
        if text in self.assets_db and (tag is None or self._is_asset_reference(tag)):
            info = self.assets_db[text]
            oasis_id = info.get("oasis_id")
            v_tech_id = info.get("visible_tech_name_id")
            name = lang_dict.get(oasis_id) or lang_dict.get(v_tech_id) or info.get("fallback_name", "N/A")
            return f"({name})"

        if tag is not None and not self._is_text_reference(tag, text):
            return ""

        if text in lang_dict:
            return f"(Text: {lang_dict[text]})"

        return ""

    def _is_value_only(self, tag):
        """True when *tag* holds a plain quantity that references nothing."""
        checker = getattr(self.active_game, "is_value_only", None)
        return bool(checker(tag)) if checker else False

    def _is_asset_reference(self, tag):
        """True when *tag* may point at another asset."""
        checker = getattr(self.active_game, "is_asset_reference", None)
        return checker(tag) if checker else True

    def _is_text_reference(self, tag, value):
        """True when *tag* really points at an entry in texts_*.xml."""
        checker = getattr(self.active_game, "is_text_reference", None)
        return checker(tag, value) if checker else True

    def browse_path_settings(self, group_key):
        """Add an XML base folder to one game's folder list."""
        widget = self.list_xml_paths_by_group.get(group_key)
        if widget is None:
            return

        label = next((group_label for key, group_label, _settings_key in XML_PATH_GROUPS
                      if key == group_key), "XML")
        folder = QFileDialog.getExistingDirectory(self, f"Select base folder for {label}")
        if not folder:
            return

        existing = [widget.item(row).text() for row in range(widget.count())]
        if folder not in existing:
            widget.addItem(folder)

        self._save_xml_paths()
        index = self.combo_xml_path.findText(folder)
        if index >= 0:
            self.combo_xml_path.setCurrentIndex(index)

    def _create_folder_setting_row(self, parent_layout, label_text, settings_key, dialog_title):
        row=QHBoxLayout()
        path_edit=QLineEdit(str(self.settings.value(settings_key, "") or ""))
        path_edit.setReadOnly(True)
        path_edit.setPlaceholderText("Not configured")
        path_edit.setToolTip(path_edit.text())
        browse_button=QPushButton("Browse...")
        browse_button.setFixedWidth(80)
        def browse_folder():
            folder=QFileDialog.getExistingDirectory(self, dialog_title, path_edit.text() if os.path.isdir(path_edit.text()) else "")
            if folder:
                path_edit.setText(folder)
                path_edit.setToolTip(folder)
                self.settings.setValue(settings_key, folder)
                self.settings.sync()
        browse_button.clicked.connect(browse_folder)
        row.addWidget(QLabel(label_text))
        row.addWidget(path_edit, 1)
        row.addWidget(browse_button)
        parent_layout.addLayout(row)
        return path_edit

    def _add_extract_button(self, parent_layout, game_name, folder_edit):
        row = QHBoxLayout()
        row.addStretch()
        button = QPushButton(f"Extract {game_name} gamefiles")
        button.clicked.connect(lambda: self.extract_gamefiles(game_name, folder_edit))
        row.addWidget(button)
        parent_layout.addLayout(row)

    def extract_gamefiles(self, game_name, folder_edit):
        game_folder = folder_edit.text().strip()
        if not os.path.isdir(game_folder):
            QMessageBox.warning(self, "Extract gamefiles", f"Game folder not found:\n{game_folder}")
            return
        output_folder = QFileDialog.getExistingDirectory(self, f"Select output folder for {game_name}")
        if not output_folder:
            return
        app_dir = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
        rda_path = os.path.join(app_dir, "RdaConsole.exe")
        if not os.path.isfile(rda_path):
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("RdaConsole.exe not found")
            box.setTextFormat(Qt.TextFormat.RichText)
            box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            box.setText(
                "RdaConsole.exe was not found.<br><br>"
                "Please download RdaConsole here:<br>"
                "<a href='https://github.com/anno-mods/RdaConsole/releases'>"
                "RdaConsole GitHub</a><br><br>"
                f"Then place RdaConsole.exe in the application directory:<br>{app_dir}"
            )
            box.exec()
            return

        self._rda_queue = multiprocessing.Queue()
        self._rda_process = multiprocessing.Process(
            target=rda_extraction_worker,
            args=(self._rda_queue, app_dir, game_name, game_folder, output_folder),
        )
        self._rda_process.start()
        self._rda_game_name = game_name
        self._rda_progress = QProgressDialog("Starting extraction...", None, 0, 0, self)
        self._rda_progress.setWindowTitle("Extract gamefiles")
        self._rda_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._rda_progress.setAutoClose(False)
        self._rda_progress.setMinimumDuration(0)
        self._rda_progress.show()
        self._rda_timer = QTimer(self)
        self._rda_timer.timeout.connect(self._check_rda_extraction)
        self._rda_timer.start(100)

    def _check_rda_extraction(self):
        try:
            while True:
                message = self._rda_queue.get_nowait()
                kind = message[0]
                if kind == "progress":
                    _kind, label, current, total = message
                    self._rda_progress.setLabelText(label)
                    if total:
                        self._rda_progress.setRange(0, total)
                        self._rda_progress.setValue(current)
                    else:
                        self._rda_progress.setRange(0, 0)
                elif kind == "finished":
                    self._finish_rda_extraction(*message[1:])
                    return
                else:
                    self._finish_rda_extraction_error(message[1], message[2])
                    return
        except Empty:
            if not self._rda_process.is_alive():
                self._finish_rda_extraction_error(
                    "ProcessError", "The extraction process ended unexpectedly."
                )

    def _cleanup_rda_extraction(self):
        self._rda_timer.stop()
        self._rda_progress.close()
        self._rda_process.join()
        self._rda_process = None

    def _finish_rda_extraction(self, args, returncode, output):
        self._cleanup_rda_extraction()
        self.append_debug_log("[rda] Running: " + " ".join(f'\"{arg}\"' for arg in args))
        self.append_debug_log(f"[rda] Exit code: {returncode}\n{output.strip()}")
        if returncode not in (0, NET_CONSOLE_EXIT_CODE):
            QMessageBox.critical(self, "Extract gamefiles failed",
                                 f"RdaConsole exit code: {returncode}\n\n{output[-4000:]}")
            return
        self.statusBar().showMessage(f"Extraction finished for {self._rda_game_name}", 5000)

    def _finish_rda_extraction_error(self, error_type, error_message):
        self._cleanup_rda_extraction()
        if error_type == "TimeoutExpired":
            error_message = "RdaConsole timed out after 300 seconds."
        QMessageBox.critical(self, "Extract gamefiles", error_message)

    def save_settings(self):

        self.xml_path_groups = self._current_xml_path_groups()
        self.xml_paths = self._flat_xml_paths()
        self._populate_path_selector(self.combo_xml_path)
        self._sync_guid_compare_paths()
        lang = self.combo_default_lang.currentText()
        tags = sorted(set(
            self.list_buff_filter_tags.item(row).text().strip()
            for row in range(self.list_buff_filter_tags.count())
            if self.list_buff_filter_tags.item(row).text().strip()
        ))

        if not tags:
            tags = sorted(DEFAULT_BUFF_FILTER_TAGS)
            self.list_buff_filter_tags.clear()
            for tag in tags:
                item = QListWidgetItem(tag)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.list_buff_filter_tags.addItem(item)

        self._buff_filter_tags = tags
        self._buff_filter_selected = set(tags)

        for group_key, _group_label, group_settings_key in XML_PATH_GROUPS:
            self.settings.setValue(group_settings_key, self.xml_path_groups[group_key])
        self.settings.setValue("Paths/xml_path", self.combo_xml_path.currentText())
        self.settings.setValue("Paths/default_lang", lang)
        self.settings.setValue("UI/theme", self.current_theme)
        self.settings.setValue("Paths/anno117_folder", self.edit_anno117_folder.text().strip())
        self.settings.setValue("Paths/anno1800_folder", self.edit_anno1800_folder.text().strip())
        self.settings.setValue("Buffs/tags", "\n".join(tags))
        self.settings.sync()

        active_path = self.combo_xml_path.currentText()
        if active_path and os.path.exists(active_path):
            self.start_loading(active_path)

        self.statusBar().showMessage("Settings saved", 3000)

    def add_buff_filter_tag(self):

        item = QListWidgetItem("NewTag")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_buff_filter_tags.addItem(item)
        self.list_buff_filter_tags.setCurrentItem(item)
        self.list_buff_filter_tags.editItem(item)

    def remove_buff_filter_tag(self):

        row = self.list_buff_filter_tags.currentRow()
        if row >= 0:
            self.list_buff_filter_tags.takeItem(row)

    def _game_key_for_path(self, folder):
        """Game key of a folder, taken from the configured folder lists."""
        normalised = os.path.normcase(os.path.abspath(folder or ""))
        for group_key, paths in self.xml_path_groups.items():
            for path in paths:
                if os.path.normcase(os.path.abspath(path)) == normalised:
                    return group_key
        detected = anno_game.detect_game(folder)
        if detected is not None:
            return detected.key
        return XML_PATH_GROUPS[0][0] if XML_PATH_GROUPS else ""

    def game_for_folder(self, folder):
        """Game profile of a data folder."""
        return anno_game.get_game(self._game_key_for_path(folder))

    @property
    def active_game(self):
        """Game profile of the currently loaded folder."""
        cached = getattr(self, "_active_game", None)
        if cached is not None:
            return cached
        combo = getattr(self, "combo_xml_path", None)
        return self.game_for_folder(combo.currentText() if combo else "")

    def start_loading(self, folder):

        if not folder or not os.path.exists(folder):
            return

        game = self.game_for_folder(folder)
        self._active_game = game
        self.statusBar().showMessage(
            f"Loading {game.label}: {os.path.basename(folder)}..."
        )
        # The watchlist follows the game of the folder being loaded.
        self.refresh_watchlist()

        self.worker = AnnoLoader(folder, game)
        self.worker.debug_log.connect(self.append_debug_log)
        self.worker.status.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self.on_data_ready)
        self.worker.start()

    def init_loading(self):

        folder = QFileDialog.getExistingDirectory(self, "Select folder")

        if folder:
            # Folders must belong to a game group, otherwise _save_xml_paths()
            # would rebuild the selector without them.
            group_key = "anno1800" if "1800" in folder.lower() else "anno117"
            widget = self.list_xml_paths_by_group.get(group_key)
            if widget is not None:
                existing = [widget.item(row).text() for row in range(widget.count())]
                if folder not in existing:
                    widget.addItem(folder)
            self._save_xml_paths()
            index = self.combo_xml_path.findText(folder)
            if index >= 0:
                self.combo_xml_path.setCurrentIndex(index)
            self.start_loading(folder)

    def on_data_ready(self, a, t, langs, cat_list, t_lib, v_cat):

        self.block_signals = True

        self.assets_db, self.templates_db, self.languages_db = a, t, langs
        self.structure_catalog_list = sorted(list(cat_list)) 
        self.template_library = t_lib
        self.value_catalog = v_cat

        self.combo_lang.clear()
        self.combo_lang.addItems(sorted(langs.keys()))

        self.combo_default_lang.clear()
        self.combo_default_lang.addItems(sorted(langs.keys()))

        saved_lang = self.settings.value("Paths/default_lang", "english")
        idx = self.combo_lang.findText(saved_lang)

        if idx != -1:
            self.combo_lang.setCurrentIndex(idx)
            self.combo_default_lang.setCurrentText(saved_lang)

        self.block_signals = False

        self.filter_library()
        self.filter_templates()

        self._template_filter_selected = set()
        self._template_filter_refresh_from_assets(a)
        self.apply_filter()
        self.refresh_watchlist()

        self.statusBar().showMessage(f"Loaded: {len(a)} assets")

    def filter_library(self):

        self.lib_list.clear()
        query = self.lib_filter.text().lower()

        for path in self.structure_catalog_list:
            if query in path.lower():
                self.lib_list.addItem(path)

    def filter_templates(self):

        self.templates_list.clear()
        query = self.templates_filter.text().strip().lower()

        for name in sorted(self.templates_db):
            if query in name.lower():
                self.templates_list.addItem(name)

    def preview_template(self, item):

        template_xml = self.templates_db.get(item.text())

        if not template_xml:
            self.templates_preview.clear()
            return

        element = ET.fromstring(template_xml)
        indent(element)
        self.templates_preview.setPlainText(
            ET.tostring(element, encoding="unicode")
        )

    def preview_library_item(self, item):

        path = item.text()
        content_lines = []

        # 1. Display unique values collected for this path (e.g. for <EffectScope>)
        if hasattr(self, 'value_catalog') and path in self.value_catalog:
            values = sorted(list(self.value_catalog[path]))
            if values:
                tag_name = path.split('/')[-1]
                content_lines.append(f"<!-- Unique values found for <{tag_name}> ({len(values)} entries) -->")
                for val in values:
                    # Resolve GUIDs/TextIDs to names for better readability
                    klartext = self.get_klartext(val, tag_name)
                    if klartext:
                        content_lines.append(f"{val} {klartext}")
                    else:
                        content_lines.append(val)
                
                content_lines.append("") # Spacer

        # 2. Display structural XML snippet if available
        found_xml = ""
        for t_name in self.template_library:
            if path in self.template_library[t_name]:
                variants = self.template_library[t_name][path]
                if variants:
                    first_key = list(variants.keys())[0]
                    found_xml = variants[first_key]["xml"]
                    break

        if found_xml:
            elem = ET.fromstring(found_xml)
            indent(elem)
            content_lines.append(f"<!-- Structure preview from Templates -->")
            content_lines.append(ET.tostring(elem, encoding='unicode'))

        if content_lines:
            self.lib_preview.setPlainText("\n".join(content_lines))
        else:
            self.lib_preview.clear()
    
    def update_header_styling(self, logicalIndex, order, target_table=None):

        table = target_table
        header = self.sender()

        if not table and isinstance(header, QHeaderView):
            table = header.parentWidget()

        if not table:
            table = self.table

        sort_col = logicalIndex

        for i in range(table.columnCount()):
            item = table.horizontalHeaderItem(i)
            if item:
                is_active = (i == sort_col)

                item.setForeground(QColor("#64b5f6") if is_active else QColor("#e0e0e0"))
                f = item.font(); f.setBold(is_active)
                item.setFont(f)

    def on_language_changed(self):

        if self.block_signals:
            return

        # Save current selection to restore it after rebuilding the table
        selected_guid = None
        current_row = self.table.currentRow()

        if current_row >= 0:
            selected_guid = self.table.item(current_row, 0).text()

        self.apply_filter()
        self.refresh_watchlist()

        # Re-select the asset and refresh all detail panes with the new language
        if selected_guid:
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0).text() == selected_guid:
                    self.table.selectRow(row)
                    self.load_asset_details(self.table.item(row, 0))
                    break

    def apply_filter(self):

        query_text = self.search.text().lower()
        parts = query_text.split()

        template_filter = None

        if getattr(self, "_template_filter_selected", None):
            template_filter = self._template_filter_selected

        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)

        current_lang = self.combo_lang.currentText()
        if not current_lang: return
        lang_dict = self.languages_db.get(current_lang, {})
        
        for guid, info in self.assets_db.items():
            if template_filter is not None and info["template_name"] not in template_filter:
                continue

            display_name = lang_dict.get(info['oasis_id']) or lang_dict.get(info.get('visible_tech_name_id')) or info['fallback_name']
            
            # Initialize searchable_content with core elements that are always searched
            searchable_content = [
                guid.lower(),
                info['template_name'].lower(),
                display_name.lower() # This is the primary display name (translated or fallback)
            ]

            # Always include the raw content of the <Name> tag for search,
            # as it's a direct identifier for the asset.
            # Avoid adding "n/a" if fallback_name is not set.
            name = display_name.lower()
            template = info['template_name'].lower()
            
            if info['fallback_name'] != "N/A":
                fallback_name_lower = info['fallback_name'].lower()
                if fallback_name_lower not in searchable_content: # Prevent duplicates if display_name was already fallback_name
                    searchable_content.append(fallback_name_lower)

            # If the "Search only GUID Text" checkbox is unchecked,
            # add all other text references (like InfoDescription).
            if not self.cb_search_main_only.isChecked():
                for tid in info.get('text_ids', []):
                    text_from_tid = lang_dict.get(tid, "").lower()
                    if text_from_tid and text_from_tid not in searchable_content:
                        searchable_content.append(text_from_tid)

            asset_match = True

            for part in parts:
                is_exclude = part.startswith('-')
                term = part[1:] if (is_exclude or part.startswith('+')) else part

                if not term: continue
                
                found = any(term in text for text in searchable_content)
                if (is_exclude and found) or (not is_exclude and not found):
                    asset_match = False
                    break

            if asset_match:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                guid_item = QTableWidgetItem()

                if guid.isdigit():
                    guid_item.setData(Qt.ItemDataRole.DisplayRole, int(guid))
                else:
                    guid_item.setText(guid)

                self.table.setItem(row, 0, guid_item)
                self.table.setItem(row, 1, QTableWidgetItem(display_name))
                self.table.setItem(row, 2, QTableWidgetItem(info['template_name']))

        self.table.setSortingEnabled(True)

    def _display_name_for_guid(self, guid):

        info = self.assets_db.get(guid)
        if not info:
            return "Missing asset"

        lang_dict = self.languages_db.get(self.combo_lang.currentText(), {})
        return lang_dict.get(info['oasis_id']) or lang_dict.get(info.get('visible_tech_name_id')) or info['fallback_name']

    def _update_watchlist_header(self):
        """Show which game's watchlist is currently displayed."""
        if not hasattr(self, "watch_header"):
            return
        key = self._active_watchlist_key()
        label = next((group_label for group_key, group_label, _settings_key
                      in XML_PATH_GROUPS if group_key == key), "")
        label = label.replace(" XML Files", "").strip()
        self.watch_header.setText(
            f" WATCHLIST \u2014 {label}" if label else " WATCHLIST"
        )
        self.watch_header.setToolTip(
            "Anno 117 and Anno 1800 keep separate watchlists.\n"
            "The list follows the game of the loaded XML folder."
        )

    def refresh_watchlist(self):

        self._update_watchlist_header()
        self.watchlist_table.setRowCount(0)
        self.watchlist_table.setSortingEnabled(False)

        for guid in self.watchlist_guids:
            row = self.watchlist_table.rowCount()
            self.watchlist_table.insertRow(row)

            guid_item = QTableWidgetItem()
            if guid.isdigit():
                guid_item.setData(Qt.ItemDataRole.DisplayRole, int(guid))
            else:
                guid_item.setText(guid)

            self.watchlist_table.setItem(row, 0, guid_item)
            self.watchlist_table.setItem(row, 1, QTableWidgetItem(self._display_name_for_guid(guid)))

        self.watchlist_table.setSortingEnabled(True)
        self._refresh_compare_watchlist()

    def _refresh_compare_watchlist(self):
        """Mirror watchlist entries into the GUID Compare selector."""
        if not hasattr(self, "compare_watchlist"):
            return

        selected_guid = self.compare_watchlist.currentData()
        self.compare_watchlist.blockSignals(True)
        self.compare_watchlist.clear()
        self.compare_watchlist.addItem("Select watchlist entry...", None)
        for guid in self.watchlist_guids:
            self.compare_watchlist.addItem(
                f"{guid} — {self._display_name_for_guid(guid)}", guid
            )

        selected_index = self.compare_watchlist.findData(selected_guid)
        self.compare_watchlist.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.compare_watchlist.blockSignals(False)

    def _select_compare_watchlist_guid(self, index):
        guid = self.compare_watchlist.itemData(index)
        if guid:
            self.compare_guid_input.setText(str(guid))
            self.compare_guid()

    def add_selected_to_watchlist(self):

        guid = getattr(self, "current_asset_guid", "")
        if not guid:
            row = self.table.currentRow()
            if row >= 0:
                guid = self.table.item(row, 0).text()

        if not guid or guid in self.watchlist_guids:
            return

        self.watchlist_guids.append(guid)
        self._save_watchlist_guids()
        self.refresh_watchlist()
        self.statusBar().showMessage(f"Added GUID {guid} to watchlist", 3000)

    def remove_selected_from_watchlist(self):

        row = self.watchlist_table.currentRow()
        if row < 0:
            return

        guid = self.watchlist_table.item(row, 0).text()
        self.watchlist_guids = [saved_guid for saved_guid in self.watchlist_guids if saved_guid != guid]
        self._save_watchlist_guids()
        self.refresh_watchlist()
        self.statusBar().showMessage(f"Removed GUID {guid} from watchlist", 3000)

    def load_asset_details(self, item):

        self.block_signals = True

        table = self.sender() if isinstance(self.sender(), QTableWidget) else self.table
        guid = table.item(item.row(), 0).text()
        self.current_asset_guid = guid
        
        if guid not in self.assets_db:
            self.statusBar().showMessage(f"GUID {guid} is not available in the loaded data", 3000)
            self.block_signals = False
            return

        asset = self.assets_db[guid]
        self.current_asset_template = asset['template_name']

        try:
            self.current_xml_root = ET.fromstring(asset['xml'])
            self.refresh_ui_from_xml()
            self.update_buffs_preview()
            self.update_reverse_search(guid)
        except:
            pass

        self.block_signals = False

    def update_reverse_search(self, guid):
        """Searches for all assets that reference the specified GUID."""

        self.reverse_search_table.setRowCount(0)
        self.reverse_search_table.setSortingEnabled(False)

        search_pattern = f">{guid}<"
        lang_dict = self.languages_db.get(self.combo_lang.currentText(), {})

        for other_guid, info in self.assets_db.items():
            # Ignore the asset itself
            if other_guid == guid:
                continue

            if search_pattern in info['xml']:
                row = self.reverse_search_table.rowCount()
                self.reverse_search_table.insertRow(row)

                name = lang_dict.get(info['oasis_id']) or lang_dict.get(info.get('visible_tech_name_id')) or info['fallback_name']

                guid_item = QTableWidgetItem()
                # Prefer numerical sorting for GUIDs if they are digits
                if other_guid.isdigit():
                    guid_item.setData(Qt.ItemDataRole.DisplayRole, int(other_guid))
                else:
                    guid_item.setText(other_guid)
                self.reverse_search_table.setItem(row, 0, guid_item)
                self.reverse_search_table.setItem(row, 1, QTableWidgetItem(name))
                self.reverse_search_table.setItem(row, 2, QTableWidgetItem(info['template_name']))

        self.reverse_search_table.setSortingEnabled(True)

    def update_buffs_preview(self):

        if self.current_xml_root is None:
            self.buff_view.clear()
            return
            
        buff_content = []
        seen_guids = set()

        def collect_recursive(xml_node):

            def add_to_preview(guid, source_tag):
                """Helper function to process and add an asset to the preview."""
                if guid and guid in self.assets_db and guid not in seen_guids:
                    seen_guids.add(guid) #
                    
                    b_xml = ET.fromstring(self.assets_db[guid]["xml"])
                    indent(b_xml)
                    
                    buff_content.append(f"<!-- ### {source_tag.upper()}: {guid} ### -->")
                    buff_content.append(ET.tostring(b_xml, encoding='unicode'))
                    buff_content.append("")
                    
                    collect_recursive(b_xml)

            # Examine both list containers and direct fields
            tags = self._buff_filter_tags
            selected_tags = getattr(self, "_buff_filter_selected", set(tags))
            
            for tag in tags:
                if tag not in selected_tags:
                    continue

                for node in xml_node.findall(f".//{tag}"):
                    
                    items = node.findall("Item")
                    if items:
                        # Case A: List structure (container with <Item>s)
                        for item in items:
                            b_guid = None
                            b_guid = self._reference_guid(tag, item)
                            add_to_preview(b_guid, tag)
                    
                    elif node.text and node.text.strip():
                        # Case B: Direct value (as in tech nodes)
                        add_to_preview(node.text.strip(), tag)

        collect_recursive(self.current_xml_root)
        
        self.buff_view.setPlainText("\n".join(buff_content) if buff_content else "No Buffs/BoostBuffs/Effects found.")

    def refresh_ui_from_xml(self):

        self.block_signals = True

        if self.current_xml_root is not None:
            indent(self.current_xml_root)
            self.xml_editor.setPlainText(ET.tostring(self.current_xml_root, encoding='unicode'))

            self.prop_tree.clear()
            vals = self.current_xml_root.find("Values")

            if vals is not None:
                self.parse_logic_to_tree(vals)

        self.block_signals = False

    def parse_logic_to_tree(self, element, parent_item=None, tree_widget=None):

        target = tree_widget if tree_widget else self.prop_tree

        for child in element:
            has_children = len(child) > 0
            val = (child.text or "").strip() if not has_children else ""

            # The tag decides whether the value is a text reference at all.
            klartext = self.get_klartext(val, child.tag)
            
            item = QTreeWidgetItem(parent_item or target, [child.tag, val, klartext])
            item.setData(0, Qt.ItemDataRole.UserRole, child)
            
            if has_children:
                item.setForeground(0, self._tree_colors()["group"])
                font = item.font(0)
                font.setBold(True)

                item.setFont(0, font)
                item.setExpanded(True)

                self.parse_logic_to_tree(child, item, tree_widget=target)

            else:
                item.setForeground(1, self._tree_colors()["value"])
                
                if klartext:
                    item.setForeground(2, self._tree_colors()["name"])

    def export_mod(self):

        row = self.table.currentRow()

        if row < 0 or self.current_xml_root is None:
            return

        guid = self.table.item(row, 0).text()
        default_name = f"ASSETS_GUID_{guid}.xml"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save XML File", default_name, "XML Files (*.xml)")

        if file_path:
            exported_guids = {guid}

            with open(file_path, "w", encoding="utf-8") as f:
                a_copy = ET.fromstring(ET.tostring(self.current_xml_root))
                indent(a_copy, level=0)
                f.write(ET.tostring(a_copy, encoding="unicode"))
                f.write('\n')

                def export_recursive(node):

                    def process_guid(b_guid, source_tag):
                        if b_guid and b_guid in self.assets_db and b_guid not in exported_guids:
                            b_xml = ET.fromstring(self.assets_db[b_guid]["xml"])
                            exported_guids.add(b_guid)
                            
                            indent(b_xml, level=0)
                            f.write(f'\n<!-- {source_tag} GUID: {b_guid} -->\n')
                            f.write(ET.tostring(b_xml, encoding="unicode"))
                            f.write('\n')
                            b_vals = b_xml.find("Values")

                            if b_vals is not None:
                                export_recursive(b_vals)

                    for tag in self._buff_filter_tags:
                        for found_node in node.findall(f".//{tag}"):
                            items = found_node.findall("Item")
                            if items:
                                for item in items:
                                    b_guid = None
                                    b_guid = self._reference_guid(tag, item)
                                    process_guid(b_guid, tag)
                            elif found_node.text and found_node.text.strip():
                                process_guid(found_node.text.strip(), tag)

                vals = self.current_xml_root.find("Values")

                if vals is not None:
                    export_recursive(vals)
                
            QMessageBox.information(self, "Info", f"Asset (GUID {guid}) including linked Buffs/Effects exported successfully!")


    def closeEvent(self, event):
        """Let background GUID searches finish before the window is destroyed."""
        for worker in list(self._guid_compare_workers):
            worker.requestInterruption()
        for worker in list(self._guid_compare_workers):
            worker.wait(3000)
        super().closeEvent(event)


if __name__ == "__main__":

    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    window = AnnoModTool()
    window.show()

    sys.exit(app.exec())
