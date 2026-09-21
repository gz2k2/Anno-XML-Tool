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
        try:
            asset_paths = glob.glob(os.path.join(self.folder, "**/assets.xml"), recursive=True)
            if not asset_paths:
                self.finished.emit(self.request_id, self.folder, "assets.xml was not found in this folder.")
                return

            for _event, element in ET.iterparse(asset_paths[0], events=("end",)):
                if element.tag != "Asset":
                    continue
                if (element.findtext(".//GUID") or "").strip() == self.guid:
                    _indent(element)
                    self.finished.emit(
                        self.request_id, self.folder, ET.tostring(element, encoding="unicode")
                    )
                    return
                element.clear()

            self.finished.emit(self.request_id, self.folder, f"GUID {self.guid} was not found.")
        except Exception as exc:
            self.finished.emit(self.request_id, self.folder, f"Unable to read XML: {exc}")
