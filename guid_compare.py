"""Background GUID lookup and line-based XML comparison helpers."""

import glob
import os
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

from PyQt6.QtCore import QThread, pyqtSignal


def _indent(element, level=0):
    padding = "\n" + level * "  "
    if len(element):
        if not element.text or not element.text.strip():
            element.text = padding + "  "
        for child in element:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = padding
    elif level and (not element.tail or not element.tail.strip()):
        element.tail = padding


def differing_line_numbers(left_text, right_text):
    """Return zero-based line numbers that differ in each text."""
    left_lines = left_text.splitlines()
    right_lines = right_text.splitlines()
    left_differences, right_differences = set(), set()

    matcher = SequenceMatcher(None, left_lines, right_lines, autojunk=False)
    for tag, left_start, left_end, right_start, right_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        left_differences.update(range(left_start, left_end))
        right_differences.update(range(right_start, right_end))

    return left_differences, right_differences


class GuidCompareLoader(QThread):
    """Find one asset by GUID without loading an entire XML data set."""

    finished = pyqtSignal(int, str, str)

    def __init__(self, request_id, folder, guid, parent=None):
        super().__init__(parent)
        self.request_id = request_id
        self.folder = folder
        self.guid = guid

    def run(self):
        if not self.folder or not os.path.exists(self.folder) or not self.guid:
            self.finished.emit(self.request_id, self.folder, f"GUID {self.guid} nicht gefunden.")
            return

        try:
            asset_paths = glob.glob(os.path.join(self.folder, "**/assets.xml"), recursive=True)
            if not asset_paths:
                self.finished.emit(self.request_id, self.folder, "Keine assets.xml gefunden.")
                return

            for a_path in asset_paths:
                for event, elem in ET.iterparse(a_path, events=("end",)):
                    if elem.tag == "Asset":
                        vals = elem.find("Values")
                        if vals is not None and vals.findtext(".//GUID") == self.guid:
                            _indent(elem)
                            xml_str = ET.tostring(elem, encoding="unicode")
                            elem.clear()
                            self.finished.emit(self.request_id, self.folder, xml_str)
                            return
                        elem.clear()

            self.finished.emit(self.request_id, self.folder, f"GUID {self.guid} nicht gefunden.")
        except Exception as e:
            self.finished.emit(self.request_id, self.folder, f"Fehler beim Suchen der GUID: {str(e)}")
