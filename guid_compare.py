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
    left_lines = (left_text or "").splitlines()
    right_lines = (right_text or "").splitlines()
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
        try:
            if not self.folder or not os.path.exists(self.folder):
                self.finished.emit(self.request_id, self.folder, f"Ordner nicht gefunden: {self.folder}")
                return

            target_guid = str(self.guid).strip()
            if not target_guid:
                self.finished.emit(self.request_id, self.folder, "Keine GUID angegeben.")
                return

            xml_files = glob.glob(os.path.join(self.folder, "**/*.xml"), recursive=True)
            found_element = None

            for filepath in xml_files:
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    for asset in root.iter("Asset"):
                        vals = asset.find("Values")
                        if vals is not None:
                            guid_elem = vals.find(".//GUID")
                            if guid_elem is not None and guid_elem.text and guid_elem.text.strip() == target_guid:
                                found_element = asset
                                break
                    if found_element is not None:
                        break
                except Exception:
                    continue

            if found_element is not None:
                _indent(found_element)
                content = ET.tostring(found_element, encoding="unicode")
                self.finished.emit(self.request_id, self.folder, content)
            else:
                self.finished.emit(self.request_id, self.folder, f"GUID {target_guid} nicht gefunden in {self.folder}")
        except Exception as exc:
            self.finished.emit(self.request_id, self.folder, f"Fehler bei der Suche: {str(exc)}")