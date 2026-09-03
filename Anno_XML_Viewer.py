import sys
import os
import glob
import re
import xml.etree.ElementTree as ET
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, 
                             QPushButton, QFileDialog, QLabel, QHeaderView, QTextEdit, 
                             QSplitter, QMessageBox, QTreeWidget, QTreeWidgetItem, 
                             QMenu, QDialog, QListWidget, QListWidgetItem, 
                             QDialogButtonBox, QComboBox, QTabWidget, QGroupBox,
                             QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QUrl
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QAction, QPixmap, QIcon
from PyQt6.QtGui import QDesktopServices

APP_NAME = "Anno XML Viewer by gz2k2"

DEFAULT_BUFF_FILTER_TAGS = [
    "AdditionalFunctionalEffect",
    "BoostBuffs",
    "Buffs",
    "Effects",
    "FunctionalEffects",
    "Resources",
    "TechResearchableTrigger",
    "UnlockReward",
    "MythicEffect",
]


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



################################################################################
# UI COMPONENTS
################################################################################

class XMLHighlighter(QSyntaxHighlighter):
    """
    Provides basic syntax highlighting for XML content in QTextEdit.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.styles = {}
        
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor("#4ec9b0"))  # Grün-Türkis für Tags
        tag_format.setFontWeight(QFont.Weight.Bold)
        self.styles["tag"] = tag_format

        attr_format = QTextCharFormat()
        attr_format.setForeground(QColor("#9cdcfe"))  # Hellblau für Attribute
        self.styles["attr"] = attr_format

        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#ce9178"))  # Gleiche Farbe für Attributwerte
        self.styles["value"] = value_format

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))  # Grün für Kommentare
        self.styles["comment"] = comment_format

        text_format = QTextCharFormat()
        text_format.setForeground(QColor("#dcdcdc"))  # Silbergrau für Textinhalt
        self.styles["text"] = text_format

    def highlightBlock(self, text):

        if not text:
            return

        for match in re.finditer(r"<(/?[\w:]+)", text):
            self.setFormat(match.start(), match.end() - match.start(), self.styles["tag"])
        
        for match in re.finditer(r">([^<]+)<", text):
            self.setFormat(match.start(1), match.end(1) - match.start(1), self.styles["text"])



################################################################################
# BACKGROUND WORKERS
################################################################################

class AnnoLoader(QThread):
    """
    Loads Anno 117 game data (assets, templates, texts) asynchronously in the background.
    """

    finished = pyqtSignal(dict, dict, dict, list, dict, dict) 
    status = pyqtSignal(str)
    debug_log = pyqtSignal(str)

    def __init__(self, folder_path):

        super().__init__()

        self.folder = folder_path
        self.structure_catalog = {} 
        self.template_library = {}
        self.value_catalog = {}

    def run(self):

        templates, assets, languages = {}, {}, {}

        # Recursive search for game data files in all subfolders
        asset_paths = glob.glob(os.path.join(self.folder, "**/assets.xml"), recursive=True)
        template_paths = glob.glob(os.path.join(self.folder, "**/templates.xml"), recursive=True)
        text_files = glob.glob(os.path.join(self.folder, "**/texts_*.xml"), recursive=True)
        text_files = [tf for tf in text_files if os.path.basename(tf) != "texts_metadata.xml"]

        a_path = asset_paths[0] if asset_paths else ""
        t_path = template_paths[0] if template_paths else ""

        self.debug_log.emit(f"### Loading process started: {self.folder} ###")

        if not a_path:
            self.debug_log.emit("ERROR: assets.xml not found in selected directory tree.")
            return

        self.status.emit("Loading texts...")

        try:
            for tf in text_files:
                lang_name = os.path.basename(tf).replace("texts_", "").replace(".xml", "")
                lang_dict = {}
                tex_tree = ET.parse(tf)
                for tex in tex_tree.findall(".//Text"):
                    line_id = tex.findtext("LineId")
                    content = tex.findtext("Text")

                    if line_id: lang_dict[line_id] = content

                languages[lang_name] = lang_dict
                self.debug_log.emit(f"Language loaded: {lang_name} ({len(lang_dict)} entries)")

            if t_path:
                t_tree = ET.parse(t_path)
                for t in t_tree.iter("Template"):
                    name_node = t.find("Name")
                    if name_node is not None and name_node.text:
                        templates[name_node.text.strip()] = ET.tostring(t, encoding='unicode')
                self.debug_log.emit(f"{len(templates)} templates registered from templates.xml.")

            self.status.emit("Analyzing assets & learning structures...")
            asset_count = 0

            # Iterparse für speicherschonendes Laden großer XML-Dateien
            for event, elem in ET.iterparse(a_path, events=("end",)):
                if elem.tag == "Asset":
                    template_name = elem.findtext("Template") or "NoTemplate"
                    vals = elem.find("Values")

                    if vals is not None:
                        guid = vals.findtext(".//GUID")

                        if guid:
                            text_ids = set()

                            for child in vals.iter():

                                if child.tag == "Amount":
                                    continue

                                if child.text and child.text.strip():
                                    t = child.text.strip()
                                    if t.replace("-", "").isdigit():
                                        text_ids.add(t)
                            
                            assets[guid] = {
                                "xml": ET.tostring(elem, encoding='unicode'),
                                "template_name": template_name,
                                "oasis_id": vals.findtext(".//Text/OasisId"),
                                "visible_tech_name_id": vals.findtext(".//Tech/VisibleTechName"),
                                "info_description_id": vals.findtext(".//Standard/InfoDescription"),
                                "fallback_name": vals.findtext(".//Standard/Name") or "N/A",
                                "text_ids": list(text_ids)
                            }
                            asset_count += 1

                            for category in vals:
                                self._recursive_index(category, category.tag, template_name)

                        elem.clear()

            self.debug_log.emit(f"Success: {asset_count} assets available in the editor.")
            self.finished.emit(assets, templates, languages, list(self.structure_catalog.keys()), self.template_library, self.value_catalog)

        except Exception as e: 
            self.debug_log.emit(f"CRITICAL ERROR: {str(e)}")

    def _recursive_index(self, node, current_path, template_name):

        if not isinstance(node.tag, str):
            return

        if current_path not in self.structure_catalog:
            self.structure_catalog[current_path] = True

        # Index unique text values for leaf nodes (no children)
        if len(node) == 0:
            if node.text and node.text.strip():
                val = node.text.strip()
                if current_path not in self.value_catalog:
                    self.value_catalog[current_path] = set()
                self.value_catalog[current_path].add(val)

        if len(node) > 0:
            if template_name not in self.template_library:
                self.template_library[template_name] = {}

            if current_path not in self.template_library[template_name]:
                self.template_library[template_name][current_path] = {}
            
            child_tags = tuple(sorted(list(set(c.tag for c in node))))

            if child_tags not in self.template_library[template_name][current_path]:
                clean_node = ET.Element(node.tag)
                seen_in_template = set()

                for c in node:
                    # We store only one 'Item' as a representative for list structures
                    if c.tag == "Item" and "Item" in seen_in_template:
                        continue

                    clean_node.append(ET.fromstring(ET.tostring(c)))
                    seen_in_template.add(c.tag)
                
                self.template_library[template_name][current_path][child_tags] = {
                    "xml": ET.tostring(clean_node, encoding='unicode'),
                    "label": f"[{', '.join(child_tags)}]"
                }

        for child in node:
            if isinstance(child.tag, str):
                self._recursive_index(child, f"{current_path}/{child.tag}", template_name)



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

    def _load_buff_filter_tags(self):

        saved_tags = self.settings.value("Buffs/tags", "")
        saved_tags = str(saved_tags).replace("\\n", "\n")
        tags = [tag.strip() for tag in re.split(r"[,\n]", saved_tags) if tag.strip()]

        return sorted(set(tags or DEFAULT_BUFF_FILTER_TAGS))

    def _reference_guid(self, tag, node):

        reference_fields = {
            "Effects": "EffectAsset",
            "FunctionalEffects": "FunctionalEffect",
            "TechResearchableTrigger": "TechResearchableTrigger",
            "UnlockReward": "UnlockReward",
            "Resources": "Resource",
        }

        return node.findtext(reference_fields.get(tag, "GUID"))

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
        info_lbl.setStyleSheet("font-weight: bold; color: #81c784;")
        layout.addWidget(info_lbl)

        search_lbl = QLabel("Search")
        search_lbl.setStyleSheet("font-weight: bold; color: #81c784;")
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
        info_lbl.setStyleSheet("font-weight: bold; color: #81c784;")
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

        saved_path = self.settings.value("Paths/xml_path", "")
        
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
            QTableWidget, QTreeWidget, QTextEdit, QListWidget { 
                background-color: #1e1e1e; border: 1px solid #333; gridline-color: #333; border-radius: 4px; 
            }
            QHeaderView::section { background-color: #252525; padding: 4px; border: 1px solid #333; }
            QPushButton { background-color: #333; border: 1px solid #444; padding: 6px; border-radius: 4px; }
            QPushButton:hover { background-color: #444; }
            QLineEdit, QComboBox { background-color: #1e1e1e; border: 1px solid #444; padding: 4px; color: white; }
            QTabWidget::pane { border: 1px solid #333; }
            QTabBar::tab { background: #252525; padding: 10px 20px; border: 1px solid #333; border-bottom: none; }
            QTabBar::tab:selected { background: #1e1e1e; border-bottom: 2px solid #1b5e20; }
        """)

        self.assets_db, self.templates_db, self.languages_db = {}, {}, {}
        self.template_library = {}
        self.structure_catalog_list = []
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
        self.lbl_filter.setStyleSheet("color: #81c784; font-weight: bold; padding-left: 8px;")
        self.cb_search_main_only = QCheckBox("Search only GUID Text")
        self.cb_search_main_only.setStyleSheet("""
            QCheckBox { font-size: 10px; color: white; padding-left: 8px; }
            QCheckBox::indicator { border: 1px solid #555; width: 12px; height: 12px; background: #1e1e1e; }
            QCheckBox::indicator:checked { background-color: #81c784; border: 1px solid #81c784; }
        """)
        self.cb_search_main_only.setToolTip("When checked, search is limited to GUID, Display Name, and Template.\nWhen unchecked, all text content within the asset is searched.")
        self.cb_search_main_only.setChecked(True)
        self.btn_template_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._buff_filter_tags = self._load_buff_filter_tags()
        self._buff_filter_selected = set(self._buff_filter_tags)
        self.btn_buff_filter = QPushButton("Filter…")
        self.lbl_buff_filter = QLabel("Buffs/Effects")
        self.lbl_buff_filter.setStyleSheet("color: #81c784; font-weight: bold; padding-left: 8px;")
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

        export_mod_layout.addWidget(kofi_label)

        export_columns_layout.addLayout(export_xml_layout)
        export_columns_layout.addLayout(export_mod_layout)

        nav.addWidget(self.combo_lang)

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

        # TABS #########################################################################

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # TAB 1: ASSET EDITOR ##########################################################

        self.editor_tab = QWidget()
        self.tabs.addTab(self.editor_tab, "Asset Editor")

        ed_layout = QVBoxLayout(self.editor_tab)
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)

        self.top_h_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem("GUID"))
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem("Display Name"))
        self.table.setHorizontalHeaderItem(2, QTableWidgetItem("Template"))
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
        rev_header.setStyleSheet("background-color: #252525; padding: 4px; font-weight: bold; border: 1px solid #333; color: #81c784;")
        self.reverse_search_table = QTableWidget(0, 3)
        self.reverse_search_table.setHorizontalHeaderLabels(["GUID", "Display Name", "Template"])

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

        self.reverse_search_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reverse_search_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        rev_layout.addWidget(rev_header)
        rev_layout.addWidget(self.reverse_search_table)

        self.top_h_splitter.addWidget(self.table)
        self.top_h_splitter.addWidget(rev_container)
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
        xml_header.setStyleSheet("""
            background-color: #252525; 
            padding: 4px; 
            font-weight: bold; 
            border: 1px solid #333; 
            color: #81c784;
        """)
        
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
        buff_header.setStyleSheet("background-color: #252525; padding: 4px; font-weight: bold; border: 1px solid #333; color: #81c784;")
        
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

        # TAB 3: STRUKTUR BIBLIOTHEK ###################################################

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

        # TAB 4: ENGINE LOG ############################################################

        self.debug_console = QTextEdit()
        self.debug_console.setReadOnly(True)
        self.tabs.addTab(self.debug_console, "Engine Log")

        # TAB 5: EINSTELLUNGEN #########################################################

        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        set_layout = QVBoxLayout(self.settings_tab)

        path_group = QGroupBox("Path Configuration")
        path_layout = QHBoxLayout()

        self.line_xml_path = QLineEdit(saved_path)
        self.line_xml_path.setFixedWidth(350)
        btn_browse = QPushButton("Browse...")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self.browse_path_settings)

        path_layout.addWidget(self.line_xml_path)
        path_layout.addWidget(btn_browse)
        path_layout.addStretch()

        set_layout.addWidget(QLabel("Base folder for XML files:"))
        set_layout.addLayout(path_layout)

        lang_layout = QHBoxLayout()
        self.combo_default_lang = QComboBox()
        self.combo_default_lang.setFixedWidth(140)

        lang_layout.addWidget(QLabel("Default Language:"))
        lang_layout.addWidget(self.combo_default_lang)
        lang_layout.addStretch()
        set_layout.addLayout(lang_layout)

        set_layout.addWidget(QLabel("Buff/Effect XML tags:"))
        self.list_buff_filter_tags = QListWidget()
        self.list_buff_filter_tags.setMinimumHeight(180)
        for tag in self._buff_filter_tags:
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.list_buff_filter_tags.addItem(item)
        set_layout.addWidget(self.list_buff_filter_tags)

        tag_buttons_layout = QHBoxLayout()
        self.btn_add_buff_tag = QPushButton("Add Tag")
        self.btn_remove_buff_tag = QPushButton("Remove Selected Tag")
        self.btn_add_buff_tag.clicked.connect(self.add_buff_filter_tag)
        self.btn_remove_buff_tag.clicked.connect(self.remove_buff_filter_tag)
        tag_buttons_layout.addWidget(self.btn_add_buff_tag)
        tag_buttons_layout.addWidget(self.btn_remove_buff_tag)
        tag_buttons_layout.addStretch()
        set_layout.addLayout(tag_buttons_layout)

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setFixedWidth(200)
        self.btn_save.clicked.connect(self.save_settings)

        set_layout.addWidget(self.btn_save)
        set_layout.addStretch()

        # SIGNALS ######################################################################

        self.search.textChanged.connect(self.apply_filter)
        self.cb_search_main_only.toggled.connect(self.apply_filter)
        self.combo_lang.currentIndexChanged.connect(self.on_language_changed)
        self.btn_template_filter.clicked.connect(self.open_template_filter_popup)
        self.btn_buff_filter.clicked.connect(self.open_buff_filter_popup)

        self.table.itemClicked.connect(self.load_asset_details)
        self.reverse_search_table.itemClicked.connect(self.load_asset_details)
        self.btn_export.clicked.connect(self.export_mod)

        code_font = QFont("Consolas", 10)

        if not code_font.fixedPitch():
            code_font = QFont("Monospace", 10)

        self.xml_views = [
            self.xml_editor, 
            self.lib_preview, 
            self.buff_view,
            self.debug_console
        ]

        # Highlighter müssen referenziert bleiben, um Garbage Collection zu verhindern.
        self.highlighters = []

        for view in self.xml_views:
            view.setFont(code_font)
            view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            
            # Wir setzen das Stylesheet spezifisch für dieses Objekt
            view.setStyleSheet("""
                background-color: #1e1e1e; 
                color: #d4d4d4; 
                border: 1px solid #333;
                selection-background-color: #264f78;
            """)
            
            if view != self.debug_console:
                highlighter = XMLHighlighter(view.document())
                self.highlighters.append(highlighter)

        if saved_path and os.path.exists(saved_path):
            self.start_loading(saved_path)


    # ASSET LOGIC ##################################################################

    def get_klartext(self, text):

        if not text:
            return ""

        lang = self.combo_lang.currentText()
        if not lang:
            return ""

        lang_dict = self.languages_db.get(lang, {})

        if text in self.assets_db:
            info = self.assets_db[text]
            oasis_id = info.get("oasis_id")
            v_tech_id = info.get("visible_tech_name_id")
            name = lang_dict.get(oasis_id) or lang_dict.get(v_tech_id) or info.get("fallback_name", "N/A")
            return f"({name})"

        if text in lang_dict:
            return f"(Text: {lang_dict[text]})"

        return ""

    def browse_path_settings(self):

        folder = QFileDialog.getExistingDirectory(self, "Select XML base folder")

        if folder:
            self.line_xml_path.setText(folder)

    def save_settings(self):

        folder = self.line_xml_path.text()
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

        self.settings.setValue("Paths/xml_path", folder)
        self.settings.setValue("Paths/default_lang", lang)
        self.settings.setValue("Buffs/tags", "\n".join(tags))

        if folder and os.path.exists(folder):
            self.start_loading(folder)

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

    def start_loading(self, folder):

        if not folder or not os.path.exists(folder):
            return

        self.statusBar().showMessage(f"Loading: {os.path.basename(folder)}...")

        self.worker = AnnoLoader(folder)
        self.worker.debug_log.connect(lambda m: self.debug_console.append(m))
        self.worker.status.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self.on_data_ready)
        self.worker.start()

    def init_loading(self):

        folder = QFileDialog.getExistingDirectory(self, "Select folder")

        if folder:
            self.line_xml_path.setText(folder)
            self.settings.setValue("Paths/xml_path", folder)
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

        self._template_filter_selected = set()
        self._template_filter_refresh_from_assets(a)
        self.apply_filter()

        self.statusBar().showMessage(f"Loaded: {len(a)} assets")

    def filter_library(self):

        self.lib_list.clear()
        query = self.lib_filter.text().lower()

        for path in self.structure_catalog_list:
            if query in path.lower():
                self.lib_list.addItem(path)

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
                    klartext = self.get_klartext(val)
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

    def load_asset_details(self, item):

        self.block_signals = True

        table = self.sender() if isinstance(self.sender(), QTableWidget) else self.table
        guid = table.item(item.row(), 0).text()
        
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

            # Avoid looking up plaintext for amount values to prevent false positives
            if child.tag == "Amount" or child.tag == "Elements":
                klartext = ""
            else:
                klartext = self.get_klartext(val)
            
            item = QTreeWidgetItem(parent_item or target, [child.tag, val, klartext])
            item.setData(0, Qt.ItemDataRole.UserRole, child)
            
            if has_children:
                item.setForeground(0, QColor("#81c784")) # Soft Green
                font = item.font(0)
                font.setBold(True)

                item.setFont(0, font)
                item.setExpanded(True)

                self.parse_logic_to_tree(child, item, tree_widget=target)

            else:
                item.setForeground(1, QColor("#64b5f6")) # Light blue for values
                
                if klartext:
                    item.setForeground(2, QColor("#ffd54f")) # Amber for names

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


if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = AnnoModTool()
    window.show()

    sys.exit(app.exec())