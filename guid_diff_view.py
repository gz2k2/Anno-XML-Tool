"""Side-by-side XML diff view with line numbers, synced scrolling and markers.

Drop-in replacement for the two plain QTextEdit panes in the GUID Compare tab.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QTextCharFormat, QTextCursor, QTextFormat
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

# Colours tuned for the #1e1e1e editor background of the main window.
#
# Each row background is a trade-off: bright enough to stand out against the
# background, dark enough that the #d4d4d4 body text and the syntax highlighter
# colours stay readable on top of it. The values below sit at roughly 2-2.5x
# contrast against the background while keeping text above 4.4x.
COLOR_ADDED = QColor("#186b38")     # line exists only on this side
COLOR_REMOVED = QColor("#962c2c")   # line removed on this side
COLOR_CHANGED = QColor("#2a5190")   # line modified
COLOR_INLINE = QColor("#2d72c0")    # changed words inside a changed line
COLOR_FILLER = QColor("#141414")    # alignment padding, no counterpart

COLOR_GUTTER_BG = QColor("#252525")
COLOR_GUTTER_FG = QColor("#8a8a8a")
COLOR_GUTTER_ACTIVE = QColor("#a5d6a7")

MARKERS = {"added": "+", "removed": "-", "changed": "~", "filler": " ", "equal": " "}
# Gutter markers are thin glyphs, so they are noticeably brighter than the
# row backgrounds to stay visible.
MARKER_COLORS = {
    "added": QColor("#4ade80"),
    "removed": QColor("#ff6b6b"),
    "changed": QColor("#60a5fa"),
}
FILLER_TEXT = ""
_WORD_SPLIT = re.compile(r"(\W)")


# --------------------------------------------------------------------------
# Alignment logic (pure, unit-testable)
# --------------------------------------------------------------------------
def align_lines(left_text: str, right_text: str, ignore_whitespace: bool = True):
    """Build row-aligned line lists for a side-by-side diff.

    Returns (left_rows, right_rows, stats); each row is a dict with
    ``text``, ``number`` (1-based, or None for filler) and ``kind``.
    """
    left_lines = (left_text or "").splitlines()
    right_lines = (right_text or "").splitlines()

    if ignore_whitespace:
        left_keys = [line.strip() for line in left_lines]
        right_keys = [line.strip() for line in right_lines]
    else:
        left_keys, right_keys = left_lines, right_lines

    left_rows: list[dict] = []
    right_rows: list[dict] = []
    stats = {"added": 0, "removed": 0, "changed": 0}

    def push(rows, lines, index, kind):
        rows.append({"text": lines[index], "number": index + 1, "kind": kind})

    def push_filler(rows):
        rows.append({"text": FILLER_TEXT, "number": None, "kind": "filler"})

    matcher = SequenceMatcher(None, left_keys, right_keys, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                push(left_rows, left_lines, i1 + offset, "equal")
                push(right_rows, right_lines, j1 + offset, "equal")
            continue

        if tag == "replace":
            # Pair changed lines 1:1 as far as possible, pad the remainder.
            paired = min(i2 - i1, j2 - j1)
            for offset in range(paired):
                push(left_rows, left_lines, i1 + offset, "changed")
                push(right_rows, right_lines, j1 + offset, "changed")
                stats["changed"] += 1
            for index in range(i1 + paired, i2):
                push(left_rows, left_lines, index, "removed")
                push_filler(right_rows)
                stats["removed"] += 1
            for index in range(j1 + paired, j2):
                push_filler(left_rows)
                push(right_rows, right_lines, index, "added")
                stats["added"] += 1
            continue

        if tag == "delete":
            for index in range(i1, i2):
                push(left_rows, left_lines, index, "removed")
                push_filler(right_rows)
                stats["removed"] += 1
            continue

        if tag == "insert":
            for index in range(j1, j2):
                push_filler(left_rows)
                push(right_rows, right_lines, index, "added")
                stats["added"] += 1

    return left_rows, right_rows, stats


def inline_ranges(left_line: str, right_line: str):
    """Return ((start, length), ...) of differing words on each side."""
    left_parts = [part for part in _WORD_SPLIT.split(left_line) if part != ""]
    right_parts = [part for part in _WORD_SPLIT.split(right_line) if part != ""]

    left_offsets, offset = [], 0
    for part in left_parts:
        left_offsets.append(offset)
        offset += len(part)
    right_offsets, offset = [], 0
    for part in right_parts:
        right_offsets.append(offset)
        offset += len(part)

    left_spans, right_spans = [], []
    matcher = SequenceMatcher(None, left_parts, right_parts, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if i2 > i1:
            start = left_offsets[i1]
            end = left_offsets[i2 - 1] + len(left_parts[i2 - 1])
            left_spans.append((start, end - start))
        if j2 > j1:
            start = right_offsets[j1]
            end = right_offsets[j2 - 1] + len(right_parts[j2 - 1])
            right_spans.append((start, end - start))
    return left_spans, right_spans


# --------------------------------------------------------------------------
# Gutter
# --------------------------------------------------------------------------
class _GutterArea(QWidget):
    """Line-number column painted by its owning DiffPane."""

    def __init__(self, editor: "DiffPane"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.gutter_width(), 0)

    def paintEvent(self, event):
        self._editor.paint_gutter(event)


# --------------------------------------------------------------------------
# Diff pane
# --------------------------------------------------------------------------
class DiffPane(QPlainTextEdit):
    """Read-only code view with a line-number gutter and diff row metadata."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        font = QFont("Consolas", 10)
        if not font.fixedPitch():
            font = QFont("Monospace", 10)
        self.setFont(font)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4;"
            " border: 1px solid #333; selection-background-color: #264f78; }"
        )

        self._rows: list[dict] = []
        self._gutter = _GutterArea(self)

        self.blockCountChanged.connect(lambda _count: self._update_gutter_width())
        self.updateRequest.connect(self._on_update_request)
        self.cursorPositionChanged.connect(self._gutter.update)
        self._update_gutter_width()

    # -- content ---------------------------------------------------------
    def set_rows(self, rows: list[dict]) -> None:
        """Fill the pane from aligned rows produced by :func:`align_lines`."""
        self._rows = rows
        self.setPlainText("\n".join(row["text"] for row in rows))
        self._update_gutter_width()
        self._gutter.update()

    def set_message(self, message: str) -> None:
        """Show a status text without any diff decoration."""
        self._rows = []
        self.setExtraSelections([])
        self.setPlainText(message)
        self._update_gutter_width()
        self._gutter.update()

    def rows(self) -> list[dict]:
        return self._rows

    def change_rows(self) -> list[int]:
        """Row indices that are part of a change, for prev/next navigation."""
        return [index for index, row in enumerate(self._rows)
                if row["kind"] not in ("equal", "filler")]

    # -- gutter ----------------------------------------------------------
    def gutter_width(self) -> int:
        digits = max(3, len(str(max(self.blockCount(), 1))))
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_gutter_width(self) -> None:
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _on_update_request(self, rect: QRect, dy: int) -> None:
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        contents = self.contentsRect()
        self._gutter.setGeometry(
            QRect(contents.left(), contents.top(),
                  self.gutter_width(), contents.height())
        )

    def paint_gutter(self, event) -> None:
        painter = QPainter(self._gutter)
        painter.fillRect(event.rect(), COLOR_GUTTER_BG)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        current = self.textCursor().blockNumber()
        width = self._gutter.width()
        height = self.fontMetrics().height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                row = self._rows[block_number] if block_number < len(self._rows) else None
                kind = row["kind"] if row else "equal"
                number = row["number"] if row else block_number + 1

                marker = MARKERS.get(kind, " ")
                if marker.strip():
                    marker_font = painter.font()
                    marker_font.setBold(True)
                    painter.setFont(marker_font)
                    painter.setPen(MARKER_COLORS[kind])
                    painter.drawText(
                        QRect(2, int(top), 12, height),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        marker,
                    )

                if number is not None:
                    number_font = painter.font()
                    number_font.setBold(block_number == current)
                    painter.setFont(number_font)
                    painter.setPen(COLOR_GUTTER_ACTIVE if block_number == current
                                   else COLOR_GUTTER_FG)
                    painter.drawText(
                        QRect(0, int(top), width - 6, height),
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        str(number),
                    )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    # -- navigation ------------------------------------------------------
    def goto_row(self, row_index: int) -> None:
        block = self.document().findBlockByNumber(row_index)
        if not block.isValid():
            return
        self.setTextCursor(QTextCursor(block))
        self.centerCursor()


# --------------------------------------------------------------------------
# Scroll synchronisation
# --------------------------------------------------------------------------
class SyncScrollGroup:
    """Keep the scroll position of several panes in sync.

    Because :func:`align_lines` pads both sides to the same row count, a plain
    1:1 value mapping is enough - no heuristics required.
    """

    def __init__(self, *panes: QPlainTextEdit, horizontal: bool = True):
        self._panes = list(panes)
        self._syncing = False
        for pane in self._panes:
            pane.verticalScrollBar().valueChanged.connect(
                lambda value, source=pane: self._sync(source, value, True)
            )
            if horizontal:
                pane.horizontalScrollBar().valueChanged.connect(
                    lambda value, source=pane: self._sync(source, value, False)
                )

    def _sync(self, source, value: int, vertical: bool) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            for pane in self._panes:
                if pane is source:
                    continue
                bar = pane.verticalScrollBar() if vertical else pane.horizontalScrollBar()
                if bar.value() != value:
                    bar.setValue(value)
        finally:
            self._syncing = False


# --------------------------------------------------------------------------
# High-level entry point
# --------------------------------------------------------------------------
def _line_selection(pane: DiffPane, row_index: int, color: QColor):
    block = pane.document().findBlockByNumber(row_index)
    if not block.isValid():
        return None
    selection = QTextEdit.ExtraSelection()
    cursor = QTextCursor(block)
    cursor.clearSelection()
    selection.cursor = cursor
    selection.format.setBackground(color)
    selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
    return selection


def _inline_selection(pane: DiffPane, row_index: int, start: int, length: int):
    block = pane.document().findBlockByNumber(row_index)
    if not block.isValid():
        return None
    cursor = QTextCursor(block)
    cursor.setPosition(block.position() + start)
    cursor.setPosition(block.position() + start + length,
                       QTextCursor.MoveMode.KeepAnchor)
    selection = QTextEdit.ExtraSelection()
    selection.cursor = cursor
    fmt = QTextCharFormat()
    fmt.setBackground(COLOR_INLINE)
    selection.format = fmt
    return selection


def set_diff_texts(left_pane: DiffPane, right_pane: DiffPane,
                   left_text: str, right_text: str,
                   ignore_whitespace: bool = True) -> dict:
    """Render a side-by-side diff into both panes; return the change stats."""
    left_rows, right_rows, stats = align_lines(left_text, right_text, ignore_whitespace)

    left_pane.set_rows(left_rows)
    right_pane.set_rows(right_rows)

    row_colors = {
        "added": COLOR_ADDED,
        "removed": COLOR_REMOVED,
        "changed": COLOR_CHANGED,
        "filler": COLOR_FILLER,
    }

    left_selections, right_selections = [], []
    for index, (left_row, right_row) in enumerate(zip(left_rows, right_rows)):
        for pane, row, selections in (
            (left_pane, left_row, left_selections),
            (right_pane, right_row, right_selections),
        ):
            color = row_colors.get(row["kind"])
            if color is None:
                continue
            selection = _line_selection(pane, index, color)
            if selection is not None:
                selections.append(selection)

        if left_row["kind"] == "changed":
            left_spans, right_spans = inline_ranges(left_row["text"], right_row["text"])
            for start, length in left_spans:
                selection = _inline_selection(left_pane, index, start, length)
                if selection is not None:
                    left_selections.append(selection)
            for start, length in right_spans:
                selection = _inline_selection(right_pane, index, start, length)
                if selection is not None:
                    right_selections.append(selection)

    left_pane.setExtraSelections(left_selections)
    right_pane.setExtraSelections(right_selections)
    return stats


def format_stats(stats: dict) -> str:
    """Human readable summary, e.g. '12 changed, 3 only left, 1 only right'."""
    if not any(stats.values()):
        return "No differences"
    return (f"{stats['changed']} changed, "
            f"{stats['removed']} only left, "
            f"{stats['added']} only right")
