"""Lazy translation catalog for the texts_*.xml files of one data folder.

Loading every language up front is the single most expensive part of a cold
start: Anno 1800 ships sixteen texts_*.xml files and the old loader parsed
each of them into a full DOM with ``ET.parse`` before touching a single
asset. Fifteen of those languages are never looked at in a typical session.

This module keeps the *names* of all languages available immediately (the UI
only needs them to fill the language combo box) and parses a file the first
time somebody actually reads an entry from it. Parsing itself streams with
``iterparse`` and discards each <Text> element right away, so the DOM never
exists as a whole.

The class behaves like ``dict[str, dict[str, str]]`` for every read access the
viewer performs, so ``languages_db.get(lang, {})`` keeps working unchanged.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from collections.abc import Mapping


class LanguageCatalog(Mapping):
    """``language -> {text_id: translation}`` with per-language lazy loading."""

    def __init__(self, game, text_files, log=None):
        self._game = game
        self._log = log
        #: Messages produced while no usable sink is attached. The catalog
        #: outlives the loader, so a language parsed later would otherwise
        #: log into a dead object - see set_log().
        self._buffered: list[str] = []
        #: language -> file path, in the order find_files reported them.
        self._paths: dict[str, str] = {}
        #: language -> parsed entries, filled on first access.
        self._entries: dict[str, dict] = {}

        for path in text_files:
            language = game.language_from_path(path)
            # A language present twice (two folders merged) keeps the first
            # file, exactly like the old dict-overwrite order did.
            self._paths.setdefault(language, path)

    # -- Mapping protocol -------------------------------------------------
    def __getitem__(self, language):
        if language in self._entries:
            return self._entries[language]
        if language not in self._paths:
            raise KeyError(language)
        return self._load(language)

    def __iter__(self):
        return iter(self._paths)

    def __len__(self):
        return len(self._paths)

    def __contains__(self, language):
        return language in self._paths

    def keys(self):
        return self._paths.keys()

    # -- loading ----------------------------------------------------------
    def preload(self, languages) -> None:
        """Parse the given languages now, e.g. inside the loader thread."""
        for language in languages:
            if language in self._paths and language not in self._entries:
                self._load(language)

    def is_loaded(self, language) -> bool:
        return language in self._entries

    def set_log(self, log) -> None:
        """Point the log at a new sink and flush what was buffered.

        The catalog is created inside the loader thread and initially logs
        through ``AnnoLoader.debug_log.emit``. That bound signal belongs to
        the QThread, which is deleteLater()'d as soon as the load is done -
        while the catalog lives on in the main window. Loading a language
        later then emitted into an already destroyed C++ object and took the
        whole application down. The window therefore re-points the log at
        itself the moment it takes the catalog over.
        """
        self._log = log
        if log is None:
            return
        pending, self._buffered = self._buffered, []
        for message in pending:
            self._safe_log(message)

    def detach_log(self) -> None:
        """Drop the current sink; later messages are buffered instead."""
        self._log = None

    def _safe_log(self, message: str) -> bool:
        try:
            self._log(message)
            return True
        except RuntimeError:
            # The sink went away (deleted QObject). Keep the message and
            # stop using this sink rather than letting the exception escape
            # into a Qt slot, where it aborts the process.
            self._log = None
            return False

    def _emit(self, message: str) -> None:
        if self._log is not None and self._safe_log(message):
            return
        self._buffered.append(message)
        # A runaway buffer is worse than a lost debug line.
        if len(self._buffered) > 200:
            del self._buffered[:-200]

    def _load(self, language) -> dict:
        path = self._paths[language]
        entries: dict[str, str] = {}
        key_tag = self._game.text_key_tag

        try:
            # iterparse + clear(): the old ET.parse() kept the complete
            # document alive just to read two child elements per <Text>.
            #
            # Watch out for the nesting: an entry element is itself called
            # <Text> and contains another <Text> holding the translation, so
            # the inner element must be left untouched - clearing it would
            # wipe the string before the outer element is even seen.
            root = None
            for event, element in ET.iterparse(path, events=("start", "end")):
                if root is None and event == "start":
                    root = element
                    continue
                if event != "end" or element.tag != "Text":
                    continue

                key = element.findtext(key_tag)
                if key is None:
                    # The inner <Text> of an entry; the outer one follows.
                    continue

                content = element.findtext("Text")
                if key.strip() and content is not None:
                    entries[key.strip()] = content

                element.clear()
                if root is not None and len(root) > 1:
                    del root[:-1]
        except (ET.ParseError, OSError) as exc:
            self._emit(f"WARNING: skipped {path}: {exc}")
            self._entries[language] = entries
            return entries

        self._entries[language] = entries
        self._emit(f"Language loaded: {language} ({len(entries)} entries)")
        if not entries:
            self._emit(
                f"WARNING: no <{key_tag}> keys in {language}. "
                f"Is this folder listed under the right game?"
            )
        return entries

    # -- cache support ----------------------------------------------------
    def fingerprint(self) -> tuple:
        """(path, mtime, size) of every text file, for the on-disk index."""
        marks = []
        for language in sorted(self._paths):
            path = self._paths[language]
            try:
                stat = os.stat(path)
                marks.append((language, path, int(stat.st_mtime), stat.st_size))
            except OSError:
                marks.append((language, path, 0, 0))
        return tuple(marks)
