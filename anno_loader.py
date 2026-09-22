"""Background loader that parses one Anno data folder.

The loader itself is game agnostic: everything that differs between Anno 117
and Anno 1800 is delegated to an :class:`anno_game.AnnoGame` implementation.
"""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET

from PyQt6.QtCore import QThread, pyqtSignal

import anno_game


# A GUID reference is an element whose whole content is a number, e.g.
# <EffectAsset>1010371</EffectAsset>. Matching the serialised asset is the
# same test the reverse search used to run per click, only now once per load.
_GUID_REFERENCE = re.compile(r">(\d+)<")


class AnnoLoader(QThread):
    """Load assets, templates and texts of one folder in the background."""

    # The last dict is the reverse-reference index: referenced GUID -> list of
    # GUIDs pointing at it.
    finished = pyqtSignal(dict, dict, dict, list, dict, dict, dict)
    status = pyqtSignal(str)
    debug_log = pyqtSignal(str)

    def __init__(self, folder_path: str, game=None, parent=None):
        super().__init__(parent)
        self.folder = folder_path
        # Fall back to sniffing the folder when no game was supplied.
        self.game = game or anno_game.detect_game(folder_path) or anno_game.get_game("anno117")

        self.structure_catalog = {}
        self.template_library = {}
        self.value_catalog = {}

    # -- main ------------------------------------------------------------
    def run(self):
        templates, assets, languages = {}, {}, {}

        self.debug_log.emit(f"### Loading process started: {self.folder} ###")
        self.debug_log.emit(f"Game profile: {self.game.label} ({self.game.key})")

        files = self.game.find_files(self.folder)
        if not files["assets"]:
            self.debug_log.emit(
                f"ERROR: {self.game.asset_file} not found in selected directory tree."
            )
            return

        try:
            self.status.emit("Loading texts...")
            languages = self._load_texts(files["texts"])

            if files["templates"]:
                templates = self._load_templates(files["templates"])

            if files.get("properties"):
                self.debug_log.emit("properties.xml found (Anno 1800 data set).")

            self.status.emit("Analyzing assets & learning structures...")
            assets = self._load_assets(files["assets"])

            self.status.emit("Indexing asset references...")
            reverse_index = self._build_reverse_index(assets)
            self.debug_log.emit(
                f"Reverse index built: {len(reverse_index)} referenced GUIDs."
            )

            self.debug_log.emit(f"Success: {len(assets)} assets available in the editor.")
            self.finished.emit(
                assets, templates, languages,
                list(self.structure_catalog.keys()),
                self.template_library, self.value_catalog,
                reverse_index,
            )
        except Exception as exc:
            self.debug_log.emit(f"CRITICAL ERROR: {exc}")

    # -- stages ----------------------------------------------------------
    def _load_texts(self, text_files) -> dict:
        languages = {}
        for path in text_files:
            try:
                root = ET.parse(path).getroot()
            except (ET.ParseError, OSError) as exc:
                self.debug_log.emit(f"WARNING: skipped {path}: {exc}")
                continue

            language = self.game.language_from_path(path)
            entries = dict(self.game.text_entries(root))
            languages[language] = entries
            self.debug_log.emit(f"Language loaded: {language} ({len(entries)} entries)")

            if not entries:
                self.debug_log.emit(
                    f"WARNING: no <{self.game.text_key_tag}> keys in {language}. "
                    f"Is this folder listed under the right game?"
                )
        return languages

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

            values = element.find("Values")
            if values is not None:
                built = self.game.build_asset(element, values)
                if built is not None:
                    guid, record = built
                    assets[guid] = record
                    for category in values:
                        self._recursive_index(category, category.tag,
                                              record["template_name"])

            element.clear()
            if root is not None and len(root) > 1:
                del root[:-1]
        return assets

    # -- reference indexing ----------------------------------------------
    def _build_reverse_index(self, assets: dict) -> dict:
        """Map every referenced GUID to the assets pointing at it.

        Built once per load so the References pane no longer has to scan the
        serialised XML of every asset on each click.
        """
        reverse: dict[str, list[str]] = {}
        for guid, record in assets.items():
            for referenced in set(_GUID_REFERENCE.findall(record["xml"])):
                # Self-references and numbers that are no asset at all (plain
                # quantities) are of no use to the References pane.
                if referenced == guid or referenced not in assets:
                    continue
                reverse.setdefault(referenced, []).append(guid)
        return reverse

    # -- structure indexing ----------------------------------------------
    def _recursive_index(self, node, current_path, template_name):
        if not isinstance(node.tag, str):
            return

        self.structure_catalog.setdefault(current_path, True)

        if len(node) == 0:
            text = (node.text or "").strip()
            if text:
                self.value_catalog.setdefault(current_path, set()).add(text)
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
                self._recursive_index(child, f"{current_path}/{child.tag}", template_name)
