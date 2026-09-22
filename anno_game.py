"""Game-specific XML handling for the Anno series.

Anno 117 and Anno 1800 use the same file names (assets.xml, templates.xml,
texts_*.xml) but map their contents differently. Previously those differences
lived as chained ``or`` fallbacks inside a single loader, which silently made
every rule apply to both games - a tag that only exists in Anno 1800 was still
searched for in Anno 117 data and vice versa.

This module defines the interface; ``anno117`` and ``anno1800`` implement it.

Known differences
-----------------

=========================  ===========================  ===========================
Aspect                     Anno 117                     Anno 1800
=========================  ===========================  ===========================
Text key in texts_*.xml    ``<Text><LineId>``           ``<Text><GUID>``
Display text reference     ``Text/OasisId``             the asset's own GUID
Inline display text        -                            ``LocaText/English/Text``
Extra data file            -                            ``properties.xml``
=========================  ===========================  ===========================

Asset records
-------------
Every implementation produces the same record per asset so the UI does not
need to know which game is loaded::

    {
        "xml":                  str,   # serialised <Asset> element
        "template_name":        str,
        "oasis_id":             str | None,  # display-name text id
        "visible_tech_name_id": str | None,
        "info_description_id":  str | None,
        "fallback_name":        str,   # used when no translation is found
        "text_ids":             list[str],
    }
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

# Text ids used to be detected as "any numeric leaf value", which wrongly
# turned plain numbers into text lookups - <MaximumHitPoints>2500</...> would
# resolve against texts_*.xml and show an unrelated string. Each game now
# declares an explicit allowlist of tags that really reference a text entry.


class AnnoGame:
    """Base class describing how one Anno title stores its XML data."""

    #: Stable identifier used in config.ini and in the folder groups.
    key: str = ""
    #: Human readable name shown in the UI.
    label: str = ""
    #: QSettings key holding the XML folder list for this game.
    settings_key: str = ""

    #: File names searched recursively inside a data folder.
    asset_file: str = "assets.xml"
    template_file: str = "templates.xml"
    text_glob: str = "texts_*.xml"
    #: Text files that are metadata rather than translations.
    ignored_text_files: tuple[str, ...] = ("texts_metadata.xml",)

    #: Candidate paths for the asset's own GUID, tried in order.
    guid_paths: tuple[str, ...] = ("Standard/GUID", "GUID")
    #: Candidate paths for the display-name text id, tried in order.
    display_text_paths: tuple[str, ...] = ()
    #: Candidate paths for the technology name text id.
    tech_name_paths: tuple[str, ...] = ("Tech/VisibleTechName",)
    #: Candidate paths for the description text id.
    description_paths: tuple[str, ...] = ("Standard/InfoDescription",)
    #: Candidate paths for a literal name used when no translation exists.
    fallback_name_paths: tuple[str, ...] = ("Standard/Name",)

    #: Tags whose numeric content references an entry in texts_*.xml.
    #: Deliberately an allowlist: every other number in an asset is a plain
    #: value (hit points, rotation, probabilities) and must never be linked.
    text_id_tags: frozenset = frozenset()

    #: Numbers below this are never text keys; they are ordinary values.
    min_text_id_value: int = 1000

    #: Tag -> child element holding the referenced GUID.
    reference_fields: dict[str, str] = {}

    #: Buff/effect container tags that make sense for this game.
    default_buff_tags: tuple[str, ...] = ()

    # -- discovery -------------------------------------------------------
    def find_files(self, folder: str) -> dict:
        """Locate the data files of this game below *folder*."""
        assets, templates, texts = "", "", []

        for root, _dirs, files in os.walk(folder):
            for name in files:
                path = os.path.join(root, name)
                lowered = name.lower()
                if lowered == self.asset_file and not assets:
                    assets = path
                elif lowered == self.template_file and not templates:
                    templates = path
                elif (lowered.startswith("texts_") and lowered.endswith(".xml")
                      and lowered not in self.ignored_text_files):
                    texts.append(path)

        return {"assets": assets, "templates": templates, "texts": sorted(texts)}

    @staticmethod
    def language_from_path(path: str) -> str:
        """`.../texts_german.xml` -> `german`."""
        name = os.path.basename(path)
        return name[len("texts_"):-len(".xml")] if name.lower().startswith("texts_") else name

    # -- texts -----------------------------------------------------------
    #: Element holding the text key inside a <Text> entry.
    text_key_tag: str = "LineId"

    def text_entries(self, text_root: ET.Element):
        """Yield ``(text_id, translation)`` pairs from one texts_*.xml."""
        for entry in text_root.iter("Text"):
            key = entry.findtext(self.text_key_tag)
            content = entry.findtext("Text")
            if key and content is not None:
                yield key.strip(), content

    # -- assets ----------------------------------------------------------
    @staticmethod
    def _first(values: ET.Element, paths) -> str | None:
        for path in paths:
            found = values.findtext(path)
            if found and found.strip():
                return found.strip()
        return None

    def asset_guid(self, asset: ET.Element, values: ET.Element) -> str | None:
        """The asset's own GUID - never one it merely references."""
        guid = self._first(values, self.guid_paths)
        if guid:
            return guid
        # Last resort: the first GUID anywhere below <Values>.
        for candidate in values.iterfind(".//GUID"):
            if candidate.text and candidate.text.strip():
                return candidate.text.strip()
        return None

    def display_text_id(self, asset: ET.Element, values: ET.Element) -> str | None:
        return self._first(values, self.display_text_paths)

    def tech_name_id(self, asset: ET.Element, values: ET.Element) -> str | None:
        return self._first(values, self.tech_name_paths)

    def description_id(self, asset: ET.Element, values: ET.Element) -> str | None:
        return self._first(values, self.description_paths)

    def fallback_name(self, asset: ET.Element, values: ET.Element) -> str:
        return self._first(values, self.fallback_name_paths) or "N/A"

    def is_text_id(self, value) -> bool:
        """True when *value* can be a key in texts_*.xml."""
        if not value:
            return False
        value = str(value).strip()
        if not value.isdigit():
            return False
        return int(value) >= self.min_text_id_value

    def collect_text_ids(self, asset: ET.Element, values: ET.Element) -> list[str]:
        """Ids inside the asset that may resolve to a translation.

        Only tags listed in :attr:`text_id_tags` are considered. Collecting
        every numeric value would link unrelated numbers such as
        ``<BuildModeRandomRotation>90</BuildModeRandomRotation>`` or
        ``<MaximumHitPoints>2500</MaximumHitPoints>`` to whatever text entry
        happens to carry that id.
        """
        found = set()
        if self.text_id_tags:
            for child in values.iter():
                if child.tag in self.text_id_tags and self.is_text_id(child.text):
                    found.add(child.text.strip())

        for extra in (self.display_text_id(asset, values),
                      self.tech_name_id(asset, values),
                      self.description_id(asset, values)):
            if self.is_text_id(extra):
                found.add(str(extra).strip())
        return sorted(found)

    def build_asset(self, asset: ET.Element, values: ET.Element) -> tuple[str, dict] | None:
        """Turn one <Asset> element into a (guid, record) pair."""
        guid = self.asset_guid(asset, values)
        if not guid:
            return None

        return guid, {
            "xml": ET.tostring(asset, encoding="unicode"),
            "template_name": asset.findtext("Template") or "NoTemplate",
            "oasis_id": self.display_text_id(asset, values),
            "visible_tech_name_id": self.tech_name_id(asset, values),
            "info_description_id": self.description_id(asset, values),
            "fallback_name": self.fallback_name(asset, values),
            "text_ids": self.collect_text_ids(asset, values),
        }

    # -- references ------------------------------------------------------
    def reference_guid(self, tag: str, node: ET.Element) -> str | None:
        """GUID referenced by a buff/effect entry below *tag*."""
        return node.findtext(self.reference_fields.get(tag, "GUID"))

    # -- detection -------------------------------------------------------
    def detect_score(self, folder: str) -> int:
        """How strongly *folder* looks like data of this game (0 = not at all)."""
        return 0


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
_REGISTRY: dict[str, AnnoGame] = {}
#: Display order of the registered games.
GAME_ORDER = ("anno117", "anno1800")


def register(game: AnnoGame) -> AnnoGame:
    _REGISTRY[game.key] = game
    return game


def _load_implementations() -> None:
    """Import the game modules on first use.

    Done lazily instead of at module bottom: the implementations import this
    module for the base class, so a top-level import here would be circular.
    """
    if _REGISTRY:
        return
    import anno117  # noqa: F401
    import anno1800  # noqa: F401


def all_games() -> list[AnnoGame]:
    """Registered games in display order."""
    _load_implementations()
    return [_REGISTRY[key] for key in GAME_ORDER if key in _REGISTRY]


def get_game(key: str) -> AnnoGame:
    """Look up a game by key; falls back to the first registered game."""
    games = all_games()
    if key in _REGISTRY:
        return _REGISTRY[key]
    return games[0] if games else AnnoGame()


def detect_game(folder: str) -> AnnoGame | None:
    """Guess which game a data folder belongs to by inspecting its files."""
    best, best_score = None, 0
    for game in all_games():
        score = game.detect_score(folder)
        if score > best_score:
            best, best_score = game, score
    return best


def path_groups() -> tuple:
    """(key, label, settings_key) for every game - used by the settings UI."""
    return tuple((game.key, game.label, game.settings_key) for game in all_games())
