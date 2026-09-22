"""Background loader that parses one Anno data folder.

The loader itself is game agnostic: everything that differs between Anno 117
and Anno 1800 is delegated to an :class:`anno_game.AnnoGame` implementation.

Three things happen here that used to cost a full extra pass over the data:

* Translations are no longer parsed eagerly. :class:`anno_texts.LanguageCatalog`
  only reports the available languages and parses a file on first access.
* The reverse-reference index is built while the assets are parsed. It used to
  run a regular expression over the serialised XML of every asset afterwards.
* The finished result is written to an on-disk index (:mod:`anno_index`), so
  selecting a known folder again skips XML parsing entirely.
"""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET

from PyQt6.QtCore import QThread, pyqtSignal

import anno_game
import anno_index
from anno_texts import LanguageCatalog

#: Languages parsed inside the loader thread so the first repaint of the
#: asset table never has to wait for a text file. Everything else is loaded
#: on demand when the user switches the language.
PRELOAD_LANGUAGES = ("english",)

#: How often the asset loop checks whether another folder was selected.
INTERRUPT_CHECK_INTERVAL = 2000


class AnnoLoader(QThread):
    """Load assets, templates and texts of one folder in the background."""

    # IMPORTANT: the result signal must NOT be called `finished`. QThread
    # already defines `finished`, which it emits after run() has returned.
    # Shadowing it means slots like deleteLater() fire from inside run()
    # while the thread is still alive -> "QThread: Destroyed while thread is
    # still running".
    #
    # The last dict is the reverse-reference index: referenced GUID -> list of
    # GUIDs pointing at it.
    loaded = pyqtSignal(dict, dict, object, list, dict, dict, dict)
    status = pyqtSignal(str)
    debug_log = pyqtSignal(str)

    def __init__(self, folder_path: str, game=None, cache_dir: str = "",
                 preferred_language: str = "", parent=None):
        super().__init__(parent)
        self.folder = folder_path
        # Fall back to sniffing the folder when no game was supplied.
        self.game = game or anno_game.detect_game(folder_path) or anno_game.get_game("anno117")
        self.cache_dir = cache_dir
        self.preferred_language = preferred_language

        self.structure_catalog = {}
        self.template_library = {}
        self.value_catalog = {}

        #: guid -> set of GUIDs it references, collected during parsing and
        #: resolved against the asset table once everything is known.
        self._pending_references: dict[str, set] = {}
        self._store = anno_index.AssetStore()

    # -- main ------------------------------------------------------------
    def run(self):
        self.debug_log.emit(f"### Loading process started: {self.folder} ###")
        self.debug_log.emit(f"Game profile: {self.game.label} ({self.game.key})")

        files = self.game.find_files(self.folder)
        if not files["assets"]:
            self.debug_log.emit(
                f"ERROR: {self.game.asset_file} not found in selected directory tree."
            )
            return

        try:
            languages = LanguageCatalog(self.game, files["texts"],
                                        log=self.debug_log.emit)
            expected = anno_index.fingerprint(files, languages.fingerprint())

            if self._emit_from_cache(languages, expected):
                return

            if files.get("properties"):
                self.debug_log.emit("properties.xml found (Anno 1800 data set).")

            templates = {}
            if files["templates"]:
                templates = self._load_templates(files["templates"])

            self.status.emit("Analyzing assets & learning structures...")
            assets = self._load_assets(files["assets"])
            if self.isInterruptionRequested():
                self.debug_log.emit("Loading aborted: another folder was selected.")
                return

            self.status.emit("Indexing asset references...")
            reverse_index = self._resolve_references(assets)
            self.debug_log.emit(
                f"Reverse index built: {len(reverse_index)} referenced GUIDs."
            )

            self.status.emit("Loading texts...")
            languages.preload(self._languages_to_preload(languages))

            self._write_cache(expected, assets, templates, reverse_index)

            self.debug_log.emit(f"Success: {len(assets)} assets available in the editor.")
            self.loaded.emit(
                assets, templates, languages,
                list(self.structure_catalog.keys()),
                self.template_library, self.value_catalog,
                reverse_index,
            )
        except Exception as exc:
            self.debug_log.emit(f"CRITICAL ERROR: {exc}")

    # -- cache -----------------------------------------------------------
    def _languages_to_preload(self, languages) -> list:
        wanted = [self.preferred_language] if self.preferred_language else []
        wanted.extend(PRELOAD_LANGUAGES)
        available = [name for name in wanted if name in languages]
        # Nothing matched (a data set without english): take the first one so
        # the table is not empty.
        if not available and len(languages):
            available = [sorted(languages.keys())[0]]
        return list(dict.fromkeys(available))

    def _emit_from_cache(self, languages, expected) -> bool:
        """Serve the folder from the on-disk index; True when it was used."""
        self.status.emit("Checking index...")
        payload = anno_index.load(self.cache_dir, self.folder,
                                  self.game.key, expected)
        if payload is None:
            return False

        assets = payload["assets"]
        self.structure_catalog = dict.fromkeys(payload["structure_catalog"], True)
        self.template_library = payload["template_library"]
        self.value_catalog = payload["value_catalog"]
        self._store = payload["store"]

        self.status.emit("Loading texts...")
        languages.preload(self._languages_to_preload(languages))

        self.debug_log.emit(
            f"Index hit: {len(assets)} assets restored without parsing XML."
        )
        self.loaded.emit(
            assets, payload.get("templates", {}), languages,
            payload["structure_catalog"],
            self.template_library, self.value_catalog,
            payload["reverse_index"],
        )
        return True

    def _write_cache(self, expected, assets, templates, reverse_index) -> None:
        if not self.cache_dir:
            return
        written = anno_index.save(
            self.cache_dir, self.folder, self.game.key, expected,
            assets, self._store, templates, reverse_index,
            self.structure_catalog.keys(), self.template_library,
            self.value_catalog,
        )
        if written:
            self.debug_log.emit(f"Index written: {written}")
        else:
            self.debug_log.emit("WARNING: index could not be written.")

    # -- stages ----------------------------------------------------------
    def _load_templates(self, path: str) -> dict:
        templates = {}
        try:
            tree = ET.parse(path)
        except (ET.ParseError, OSError) as exc:
            self.debug_log.emit(f"WARNING: could not read {path}: {exc}")
            return templates

        for template in tree.iter("Template"):
            name = template.findtext("Name")
            if name and name.strip():
                templates[name.strip()] = ET.tostring(template, encoding="unicode")

        self.debug_log.emit(f"{len(templates)} templates registered from {self.game.template_file}.")
        return templates

    def _load_assets(self, path: str) -> dict:
        assets = {}
        root = None
        checked = 0
        build_asset = self.game.build_asset

        # iterparse alone is not enough: a cleared element stays attached to
        # the root, so the whole document still ends up in memory. The root is
        # therefore captured on the first "start" event and every finished
        # asset is detached from it.
        for event, element in ET.iterparse(path, events=("start", "end")):
            if root is None and event == "start":
                root = element
                continue
            if event != "end" or element.tag != "Asset":
                continue

            checked += 1
            if checked % INTERRUPT_CHECK_INTERVAL == 0 and self.isInterruptionRequested():
                return assets

            values = element.find("Values")
            if values is not None:
                built = build_asset(element, values)
                if built is not None:
                    guid, record = built
                    # The serialised XML goes into one flat buffer instead of
                    # a separate str object per asset.
                    offset, length = self._store.add(record.pop("xml", ""))
                    references: set = set()
                    for category in values:
                        self._recursive_index(category, category.tag,
                                              record["template_name"],
                                              references)
                    references.discard(guid)
                    if references:
                        self._pending_references[guid] = references

                    assets[guid] = anno_index.AssetRecord(
                        self._store, offset, length,
                        record["template_name"], record["oasis_id"],
                        record["visible_tech_name_id"],
                        record["info_description_id"],
                        record["fallback_name"], record["text_ids"],
                    )

            element.clear()
            if root is not None and len(root) > 1:
                del root[:-1]
        return assets

    # -- reference indexing ----------------------------------------------
    def _resolve_references(self, assets: dict) -> dict:
        """Map every referenced GUID to the assets pointing at it.

        The candidates were collected while parsing; here they are only
        checked against the finished asset table. The previous implementation
        ran a regular expression over the serialised XML of every asset, which
        was a second full pass over all the data.
        """
        reverse: dict[str, list[str]] = {}
        for guid, references in self._pending_references.items():
            for referenced in references:
                # Numbers that are no asset at all (plain quantities) are of
                # no use to the References pane.
                if referenced in assets:
                    reverse.setdefault(referenced, []).append(guid)
        self._pending_references = {}
        return reverse

    # -- structure indexing ----------------------------------------------
    def _recursive_index(self, node, current_path, template_name, references):
        if not isinstance(node.tag, str):
            return

        self.structure_catalog.setdefault(current_path, True)

        if len(node) == 0:
            text = (node.text or "").strip()
            if text:
                self.value_catalog.setdefault(current_path, set()).add(text)
                # Reference candidates are collected right here: the leaves
                # are walked anyway, and the game rules tell us which tags may
                # point at another asset at all.
                if text.isdigit() and self.game.is_asset_reference(node.tag):
                    references.add(text)
        else:
            paths = self.template_library.setdefault(template_name, {})
            variants = paths.setdefault(current_path, {})
            child_tags = tuple(sorted({child.tag for child in node}))

            if child_tags not in variants:
                clean_node = ET.Element(node.tag)
                seen = set()
                for child in node:
                    # Keep a single <Item> as representative for list structures.
                    if child.tag == "Item" and "Item" in seen:
                        continue
                    # deepcopy instead of tostring/fromstring: the round trip
                    # serialised and re-parsed every single structure element.
                    clean_node.append(copy.deepcopy(child))
                    seen.add(child.tag)

                variants[child_tags] = {
                    "xml": ET.tostring(clean_node, encoding="unicode"),
                    "label": f"[{', '.join(child_tags)}]",
                }

        for child in node:
            if isinstance(child.tag, str):
                self._recursive_index(child, f"{current_path}/{child.tag}",
                                      template_name, references)
