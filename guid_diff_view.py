"""Side-by-side XML diff view with line numbers, synced scrolling and markers.

Drop-in replacement for the two plain QTextEdit panes in the GUID Compare tab.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from PyQt6.QtCore import QRect, QRectF, QSize, Qt
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

# Base hues the row backgrounds are derived from. They get blended towards the
# editor background so the same code works on dark and on light themes.
_HUE_ADDED = QColor("#22c55e")
_HUE_REMOVED = QColor("#ef4444")
_HUE_CHANGED = QColor("#3b82f6")

# Editor colours the current diff palette was built for.
_EDITOR_BG = QColor("#1e1e1e")
_EDITOR_TEXT = QColor("#d4d4d4")


def _mix(color: QColor, background: QColor, weight: float) -> QColor:
    """Blend *color* over *background*; weight 0 -> background, 1 -> color."""
    return QColor(
        round(background.red() + (color.red() - background.red()) * weight),
        round(background.green() + (color.green() - background.green()) * weight),
        round(background.blue() + (color.blue() - background.blue()) * weight),
    )


def _is_dark(color: QColor) -> bool:
    return (0.2126 * color.redF() + 0.7152 * color.greenF()
            + 0.0722 * color.blueF()) < 0.5


def apply_theme_colors(background: QColor, text: QColor) -> None:
    """Rebuild the diff palette for the given editor background/text colour.

    Called by the theme manager whenever the application theme changes.
    """
    global COLOR_ADDED, COLOR_REMOVED, COLOR_CHANGED, COLOR_INLINE, COLOR_FILLER
    global COLOR_GUTTER_BG, COLOR_GUTTER_FG, COLOR_GUTTER_ACTIVE, MARKER_COLORS
    global _EDITOR_BG, _EDITOR_TEXT

    _EDITOR_BG, _EDITOR_TEXT = QColor(background), QColor(text)
    dark = _is_dark(background)

    # Light backgrounds need a gentler tint to keep the text readable.
    row_weight = 0.50 if dark else 0.26
    inline_weight = 0.62 if dark else 0.42
    marker_weight = 1.0 if dark else 0.85

    COLOR_ADDED = _mix(_HUE_ADDED, background, row_weight)
    COLOR_REMOVED = _mix(_HUE_REMOVED, background, row_weight)
    COLOR_CHANGED = _mix(_HUE_CHANGED, background, row_weight)
    COLOR_INLINE = _mix(_HUE_CHANGED, background, inline_weight)
    COLOR_FILLER = background.darker(115) if dark else background.darker(104)

    COLOR_GUTTER_BG = background.lighter(135) if dark else background.darker(106)
    COLOR_GUTTER_FG = _mix(text, background, 0.55)
    COLOR_GUTTER_ACTIVE = _mix(_HUE_ADDED, background, 0.85)

    MARKER_COLORS = {
        "added": _mix(_HUE_ADDED, background, marker_weight),
        "removed": _mix(_HUE_REMOVED, background, marker_weight),
        "changed": _mix(_HUE_CHANGED, background, marker_weight),
    }


# --------------------------------------------------------------------------
# Line pairing inside a replace block
# --------------------------------------------------------------------------
#: Minimum similarity before two untagged lines are shown as ONE modified
#: row. Anything below is a removal plus an unrelated insertion. Only
#: reached by lines without an XML tag - tagged lines are paired by element
#: name, see :func:`_best_anchor`.
PAIR_CUTOFF = 0.5

#: Upper bound on character-level line comparisons for ONE diff. That search
#: is quadratic, and difflib happily reports dozens of replace blocks, so a
#: per-block limit is not enough - the budget has to span the whole document.
MAX_COMPARISONS = 20000

_TAG_PATTERN = re.compile(r"^\s*<\s*(/?)\s*([\w:.\-]+)")


def _line_key(line: str):
    """Element name of an XML line, or None for a line without a tag.

    ``</Foo>`` and ``<Foo>`` deliberately produce different keys: a closing
    tag is not a modified version of an opening one.
    """
    match = _TAG_PATTERN.match(line)
    if match is None:
        return None
    return match.group(1) + match.group(2).lower()


def _score(matcher: SequenceMatcher, left_line: str, right_line: str,
           left_key, right_key) -> float:
    """Similarity of two already stripped lines with known element names.

    *matcher* must already carry *left_line* as its second sequence: difflib
    indexes seq2 and reuses that index for every seq1, so keeping the outer
    line in seq2 turns the inner loop into a cheap scan.
    """
    if not left_line and not right_line:
        return 1.0
    if not left_line or not right_line:
        return 0.0
    if left_key != right_key:
        return 0.0

    matcher.set_seq1(right_line)
    # Two cheap upper bounds prune most candidates before the real work.
    if matcher.real_quick_ratio() < PAIR_CUTOFF:
        return 0.0
    if matcher.quick_ratio() < PAIR_CUTOFF:
        return 0.0
    ratio = matcher.ratio()
    return ratio if ratio >= PAIR_CUTOFF else 0.0


def similarity(left_line: str, right_line: str) -> float:
    """How strongly two lines look like one edited line (0.0 - 1.0).

    Lines carrying different XML element names score 0: they describe
    different properties, so ``<ProductStorageList>3415</...>`` opposite
    ``<CanStoreAllNormalProducts>1</...>`` is a deletion next to an
    insertion, never a modification - even though a plain character diff
    finds the angle brackets and digits they have in common.
    """
    left_line, right_line = left_line.strip(), right_line.strip()
    matcher = SequenceMatcher(autojunk=False)
    matcher.set_seq2(left_line)
    return _score(matcher, left_line, right_line,
                  _line_key(left_line), _line_key(right_line))


def _best_anchor(left_text, right_text, left_tags, right_tags,
                 a1, a2, b1, b2, matcher, budget):
    """Best (left_index, right_index) to pair inside one window, or (-1, -1).

    For XML the element name decides, not the characters: two lines describe
    the same property exactly when their tag is the same. Comparing whole
    lines with difflib was both slower - it dominated the profile at ~125 us
    per pair - and less accurate, because ``<ProductStorageList>3415</...>``
    and ``<CanStoreAllNormalProducts>1</...>`` share enough angle brackets
    and digits to pass a character-level cutoff.

    When a tag occurs several times in the window, the candidate closest to
    the same relative position wins, which keeps repeated <Item> blocks in
    order. Lines without a tag - a status message, plain text - are the only
    ones still compared character by character.
    """
    # Tagged lines first: a dict lookup instead of a scan over the window.
    candidates: dict = {}
    for right_index in range(b1, b2):
        tag = right_tags[right_index]
        if tag is not None:
            candidates.setdefault(tag, []).append(right_index)

    best_distance, best_left, best_right = None, -1, -1
    if candidates:
        for left_index in range(a1, a2):
            tag = left_tags[left_index]
            if tag is None:
                continue
            for right_index in candidates.get(tag, ()):
                distance = abs((left_index - a1) - (right_index - b1))
                if best_distance is None or distance < best_distance:
                    best_distance, best_left, best_right = (
                        distance, left_index, right_index)
                    if distance == 0:
                        break
            if best_distance == 0:
                break

    if best_left >= 0:
        return best_left, best_right

    # No tag matched anywhere: fall back to a character comparison, which
    # only untagged lines can reach. Guarded by the shared budget.
    combinations = (a2 - a1) * (b2 - b1)
    if combinations > budget[0]:
        budget[0] = 0
        return -1, -1
    budget[0] -= combinations

    best_score = 0.0
    for left_index in range(a1, a2):
        if left_tags[left_index] is not None:
            continue
        left_line = left_text[left_index]
        matcher.set_seq2(left_line)
        for right_index in range(b1, b2):
            if right_tags[right_index] is not None:
                continue
            score = _score(matcher, left_line, right_text[right_index],
                           None, None)
            if score > best_score:
                best_score, best_left, best_right = score, left_index, right_index
                if score == 1.0:
                    break
        if best_score == 1.0:
            break

    return best_left, best_right


def pair_replace_block(left_lines, right_lines, i1, i2, j1, j2, budget=None):
    """Pair up the lines of one replace block.

    Returns ``[(left_index | None, right_index | None), ...]`` in display
    order. A pair means "this line was modified", a half-empty entry means
    "removed" or "added".

    difflib reports a replace block as "these n lines became those m lines"
    and says nothing about which line turned into which. Zipping them
    positionally - what this used to do - therefore claims a modification
    between whatever happens to sit at the same offset. The best-matching
    pair is located instead, and the regions before and after it are then
    treated the same way, so the order of the lines is preserved.

    *budget* is a one-element list carrying the remaining comparisons; it is
    shared across all blocks of one diff.
    """
    if budget is None:
        budget = [MAX_COMPARISONS]

    # Stripped text and element name of every line, computed once. Both used
    # to be recomputed inside the comparison, i.e. twice per candidate pair.
    left_text = [line.strip() for line in left_lines]
    right_text = [line.strip() for line in right_lines]
    left_tags = [_line_key(line) for line in left_text]
    right_tags = [_line_key(line) for line in right_text]
    matcher = SequenceMatcher(autojunk=False)

    pairs: list[tuple] = []
    # An explicit stack rather than recursion: a long block of alternating
    # changes would otherwise nest one level per pair.
    segments = [("split", i1, i2, j1, j2)]

    while segments:
        entry = segments.pop()

        if entry[0] == "pair":
            pairs.append((entry[1], entry[2]))
            continue

        _kind, a1, a2, b1, b2 = entry
        if a1 >= a2 and b1 >= b2:
            continue
        if a1 >= a2:
            pairs.extend((None, index) for index in range(b1, b2))
            continue
        if b1 >= b2:
            pairs.extend((index, None) for index in range(a1, a2))
            continue

        best_left, best_right = _best_anchor(
            left_text, right_text, left_tags, right_tags, a1, a2, b1, b2,
            matcher, budget)

        if best_left < 0:
            # Nothing in this window resembles anything else: the whole
            # block is a removal followed by an insertion.
            pairs.extend((index, None) for index in range(a1, a2))
            pairs.extend((None, index) for index in range(b1, b2))
            continue

        # Pushed back to front, so popping yields display order.
        segments.append(("split", best_left + 1, a2, best_right + 1, b2))
        segments.append(("pair", best_left, best_right))
        segments.append(("split", a1, best_left, b1, best_right))

    return pairs


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

    # Shared across all replace blocks of this diff, see MAX_COMPARISONS.
    budget = [MAX_COMPARISONS]

    matcher = SequenceMatcher(None, left_keys, right_keys, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                push(left_rows, left_lines, i1 + offset, "equal")
                push(right_rows, right_lines, j1 + offset, "equal")
            continue

        if tag == "replace":
            # Only lines that actually resemble each other become a single
            # "changed" row; the rest is reported as a removal and an
            # insertion, each against a filler on the opposite side.
            for left_index, right_index in pair_replace_block(
                    left_keys, right_keys, i1, i2, j1, j2, budget):
                if left_index is not None and right_index is not None:
                    push(left_rows, left_lines, left_index, "changed")
                    push(right_rows, right_lines, right_index, "changed")
                    stats["changed"] += 1
                elif left_index is not None:
                    push(left_rows, left_lines, left_index, "removed")
                    push_filler(right_rows)
                    stats["removed"] += 1
                else:
                    push_filler(left_rows)
                    push(right_rows, right_lines, right_index, "added")
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

        # The gutter needs a plain and a bold variant on every repaint.
        # Deriving them from painter.font() per visible line allocated two
        # QFont objects for each row of the viewport, on every scroll step.
        self._gutter_font = QFont(font)
        self._gutter_font_bold = QFont(font)
        self._gutter_font_bold.setBold(True)

        self.refresh_theme()

        self._rows: list[dict] = []
        self._gutter = _GutterArea(self)
        self.refresh_theme()

        self.blockCountChanged.connect(lambda _count: self._update_gutter_width())
        self.updateRequest.connect(self._on_update_request)
        self.cursorPositionChanged.connect(self._gutter.update)
        self._update_gutter_width()

    def refresh_theme(self) -> None:
        """Re-apply the editor colours after the application theme changed."""
        selection = _mix(_HUE_CHANGED, _EDITOR_BG, 0.45)
        self.setStyleSheet(
            "QPlainTextEdit {{ background-color: {bg}; color: {fg};"
            " border: 1px solid {border};"
            " selection-background-color: {sel}; }}".format(
                bg=_EDITOR_BG.name(), fg=_EDITOR_TEXT.name(),
                border=_mix(_EDITOR_TEXT, _EDITOR_BG, 0.25).name(),
                sel=selection.name(),
            )
        )
        # May run from __init__ before the gutter exists.
        gutter = getattr(self, "_gutter", None)
        if gutter is not None:
            gutter.update()

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
                    painter.setFont(self._gutter_font_bold)
                    painter.setPen(MARKER_COLORS[kind])
                    painter.drawText(
                        QRect(2, int(top), 12, height),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        marker,
                    )

                if number is not None:
                    is_current = block_number == current
                    painter.setFont(self._gutter_font_bold if is_current
                                    else self._gutter_font)
                    painter.setPen(COLOR_GUTTER_ACTIVE if is_current
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

    def paintEvent(self, event):
        """Draw the alignment padding of the currently visible rows.

        Filler rows have no text, so an opaque rectangle painted after the
        normal text rendering is enough. Doing it here costs one fill per
        visible line instead of one ExtraSelection per line of the document.
        """
        super().paintEvent(event)
        if not self._rows:
            return

        painter = None
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        width = self.viewport().width()

        while block.isValid() and top <= event.rect().bottom():
            height = self.blockBoundingRect(block).height()
            if block.isVisible() and top + height >= event.rect().top():
                row = (self._rows[block_number]
                       if block_number < len(self._rows) else None)
                if row is not None and row["kind"] == "filler":
                    if painter is None:
                        painter = QPainter(self.viewport())
                    painter.fillRect(QRectF(0, top, width, height), COLOR_FILLER)
            block = block.next()
            top += height
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

    # Filler rows are deliberately absent: they carry no text and are painted
    # directly by DiffPane.paintEvent. Building an ExtraSelection for them
    # meant one QTextEdit.ExtraSelection object per padding line, i.e. for
    # every single line of a one-sided asset.
    row_colors = {
        "added": COLOR_ADDED,
        "removed": COLOR_REMOVED,
        "changed": COLOR_CHANGED,
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

        # Word-level marks only make sense when both sides really are the
        # two versions of one line. A "changed" row always has a "changed"
        # counterpart, but the check keeps a malformed row list harmless.
        if left_row["kind"] == "changed" and right_row["kind"] == "changed":
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
