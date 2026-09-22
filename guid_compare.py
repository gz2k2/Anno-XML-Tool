"""Background GUID lookup and line-based XML comparison helpers."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from typing import Callable, Iterator

from PyQt6.QtCore import QThread, pyqtSignal

# Files are scanned in this order; the most likely hit comes first.
PREFERRED_FILENAMES = ("assets.xml", "templates.xml")
# How often the worker checks for an interruption request while scanning.
INTERRUPT_CHECK_INTERVAL = 250


def _indent(element: ET.Element, level: int = 0) -> None:
    """Pretty-print an element tree in place.

    Thin wrapper around the standard library. The hand-written recursive
    version this used to be existed in two copies (here and in the viewer)
    and did the same job as ``ET.indent`` since Python 3.9, only slower and
    without tail handling for the root element.
    """
    ET.indent(element, space="  ", level=level)


def differing_line_numbers(left_text: str, right_text: str,
                           ignore_whitespace: bool = True):
    """Return zero-based line numbers that differ in each text.

    Kept for backwards compatibility; the side-by-side view in
    ``guid_diff_view`` uses :func:`align_lines` instead.
    """
    left_lines = (left_text or "").splitlines()
    right_lines = (right_text or "").splitlines()

    if ignore_whitespace:
        left_keys = [line.strip() for line in left_lines]
        right_keys = [line.strip() for line in right_lines]
    else:
        left_keys, right_keys = left_lines, right_lines

    left_differences, right_differences = set(), set()
    matcher = SequenceMatcher(None, left_keys, right_keys, autojunk=False)
    for tag, left_start, left_end, right_start, right_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        left_differences.update(range(left_start, left_end))
        right_differences.update(range(right_start, right_end))
    return left_differences, right_differences


def iter_xml_files(folder: str) -> Iterator[str]:
    """Yield all XML files below *folder*, most relevant ones first."""
    collected: list[str] = []
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(".xml"):
                collected.append(os.path.join(root, name))

    def sort_key(path: str):
        name = os.path.basename(path).lower()
        rank = (PREFERRED_FILENAMES.index(name) if name in PREFERRED_FILENAMES
                else len(PREFERRED_FILENAMES))
        return rank, path.lower()

    return iter(sorted(collected, key=sort_key))


def _asset_guid(asset: ET.Element) -> str | None:
    """Return the own GUID of an asset, never a referenced one."""
    values = asset.find("Values")
    if values is None:
        return None
    # Direct child first; a deep search can otherwise pick up GUIDs that the
    # asset merely references (e.g. inside Item lists).
    guid = values.findtext("Standard/GUID") or values.findtext("GUID")
    if guid is None:
        for candidate in values.iterfind(".//GUID"):
            guid = candidate.text
            break
    return guid.strip() if guid else None


def find_asset_by_guid(folder: str, guid: str,
                       should_stop: Callable[[], bool] | None = None,
                       on_error: Callable[[str, Exception], None] | None = None):
    """Stream all XML files in *folder*; return (element, source_path).

    Uses iterparse so a multi-hundred-MB assets.xml never has to be held in
    memory as a full DOM.
    """
    target = str(guid).strip()
    checked = 0

    for filepath in iter_xml_files(folder):
        if should_stop and should_stop():
            return None, None
        try:
            root = None
            for event, elem in ET.iterparse(filepath, events=("start", "end")):
                if root is None and event == "start":
                    root = elem
                    continue
                if event != "end" or elem.tag != "Asset":
                    continue

                checked += 1
                if (should_stop and checked % INTERRUPT_CHECK_INTERVAL == 0
                        and should_stop()):
                    return None, None

                if _asset_guid(elem) == target:
                    return elem, filepath

                # Release the finished asset and detach it from the root.
                elem.clear()
                if root is not None and len(root) > 1:
                    del root[:-1]
        except (ET.ParseError, OSError) as exc:
            if on_error:
                on_error(filepath, exc)

    return None, None


class GuidCompareLoader(QThread):
    """Find one asset by GUID without loading an entire XML data set."""

    # IMPORTANT: this must NOT be called `finished`. QThread already defines
    # `finished`, which is emitted after run() has returned. Shadowing it means
    # slots like deleteLater() fire from inside run() while the thread is still
    # running -> "QThread: Destroyed while thread is still running".
    result = pyqtSignal(int, str, str)   # (request_id, folder, content)
    log = pyqtSignal(int, str)           # (request_id, message)

    def __init__(self, request_id: int, folder: str, guid: str, parent=None):
        super().__init__(parent)
        self.request_id = request_id
        self.folder = folder
        self.guid = guid

    def _stop_requested(self) -> bool:
        return self.isInterruptionRequested()

    def run(self):
        try:
            if not self.folder or not os.path.isdir(self.folder):
                self._emit(f"Folder not found: {self.folder}")
                return

            target_guid = str(self.guid).strip()
            if not target_guid:
                self._emit("No GUID entered.")
                return

            def report_error(path: str, exc: Exception) -> None:
                self.log.emit(self.request_id, f"[guid-compare] Skipped {path}: {exc}")

            element, source = find_asset_by_guid(
                self.folder, target_guid,
                should_stop=self._stop_requested,
                on_error=report_error,
            )

            if self._stop_requested():
                return

            if element is None:
                self._emit(f"GUID {target_guid} not found in {self.folder}")
                return

            _indent(element)
            header = f"<!-- source: {os.path.relpath(source, self.folder)} -->\n"
            self._emit(header + ET.tostring(element, encoding="unicode"))
        except Exception as exc:  # last-resort guard: the UI must get a result
            self._emit(f"Search failed: {exc}")

    def _emit(self, content: str) -> None:
        self.result.emit(self.request_id, self.folder, content)
