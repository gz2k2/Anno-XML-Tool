"""XML handling for Anno 117.

Characteristics compared to Anno 1800:

* Translations are keyed by ``<LineId>`` inside ``texts_*.xml``.
* The display name of an asset is referenced through ``Text/OasisId``.
* Technology assets carry ``Tech/VisibleTechName``.
* There is no ``properties.xml`` and no inline ``LocaText`` block.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

from anno_game import AnnoGame, register


class Anno117Game(AnnoGame):
    """Data layout of Anno 117."""

    key = "anno117"
    label = "Anno 117 XML Files"
    settings_key = "Paths/xml_paths_anno117"

    # Anno 117 keys its translations by LineId.
    text_key_tag = "LineId"

    guid_paths = ("Standard/GUID", "GUID")
    # OasisId is the Anno 117 display-name reference. LineID is accepted as a
    # secondary source because some assets carry both.
    display_text_paths = ("Text/OasisId", "Text/LineID")
    tech_name_paths = ("Tech/VisibleTechName",)
    description_paths = ("Standard/InfoDescription", "Text/InfoDescription")
    fallback_name_paths = ("Standard/Name", "Name")

    # Tags that really reference a texts_*.xml entry. Everything else in an
    # asset is a plain number and must not be resolved as text.
    text_id_tags = frozenset({
        "GUID",              # references to other assets
        "OasisId",           # display name
        "LineId", "LineID",  # translated strings
        "VisibleTechName",
        "InfoDescription",
    })

    reference_fields = {
        "Effects": "EffectAsset",
        "FunctionalEffects": "FunctionalEffect",
        "TechResearchableTrigger": "TechResearchableTrigger",
        "UnlockReward": "UnlockReward",
        "Resources": "Resource",
    }

    default_buff_tags = (
        "AdditionalFunctionalEffect",
        "BoostBuffs",
        "Buffs",
        "Effects",
        "FunctionalEffects",
        "Resources",
        "TechResearchableTrigger",
        "UnlockReward",
        "MythicEffect",
    )

    def detect_score(self, folder: str) -> int:
        """Score based on the text-key element actually used in the data."""
        score = 0
        files = self.find_files(folder)
        if not files["assets"]:
            return 0
        score += 1

        for text_path in files["texts"][:1]:
            try:
                # Only the first entries are needed to identify the schema.
                for _event, element in ET.iterparse(text_path, events=("end",)):
                    if element.tag != "Text":
                        continue
                    if element.find("LineId") is not None:
                        score += 3
                        break
                    if element.find("GUID") is not None:
                        break
            except (ET.ParseError, OSError):
                continue

        # properties.xml is an Anno 1800 artefact; its absence favours 117.
        if not os.path.isfile(os.path.join(folder, "data", "config",
                                           "export", "main", "asset",
                                           "properties.xml")):
            score += 1
        return score


register(Anno117Game())
