"""XML handling for Anno 1800.

Characteristics compared to Anno 117:

* Translations are keyed by ``<GUID>`` inside ``texts_*.xml``.
* An asset's own ``Standard/GUID`` IS its text key: the same number appears
  as the ``<GUID>`` of a ``<Text>`` entry in ``texts_*.xml``. So the display
  name is looked up with the asset GUID directly, no indirection needed::

      assets.xml    <Standard><GUID>1010371</GUID>
                              <Name>logistic_02 (Warehouse I)</Name>
      texts_*.xml   <Text><GUID>1010371</GUID><Text>Warehouse I</Text></Text>

  ``Text/LineID`` only appears on a minority of assets and is used as a
  secondary source.
* ``LineID`` is NOT a text reference in Anno 1800 - its value is an internal
  number and must not be looked up in texts_*.xml.
* Many assets embed an English string directly as
  ``LocaText/English/Text``, which is used as the fallback name.
* ``properties.xml`` ships alongside assets.xml and templates.xml.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

from anno_game import AnnoGame, register


class Anno1800Game(AnnoGame):
    """Data layout of Anno 1800."""

    key = "anno1800"
    label = "Anno 1800 XML Files"
    settings_key = "Paths/xml_paths_anno1800"

    # Anno 1800 reuses the GUID element as the translation key.
    text_key_tag = "GUID"

    guid_paths = ("Standard/GUID", "GUID")
    # Anno 1800 has no OasisId and no text indirection: the asset GUID IS the
    # text key. Text/LineID is deliberately absent - it holds an internal
    # number, not a text reference.
    display_text_paths = ("Standard/GUID", "GUID")
    tech_name_paths = ()
    description_paths = ("Text/InfoDescription", "Standard/InfoDescription")
    fallback_name_paths = ("Standard/Name", "Name")

    # Only the GUID links to a text entry. Tags such as LineID,
    # BuildModeRandomRotation or MaximumHitPoints carry ordinary numbers and
    # are never resolved against texts_*.xml.
    text_id_tags = frozenset({"GUID"})

    #: Extra data file shipped with Anno 1800.
    properties_file = "properties.xml"

    reference_fields = {
        "Effects": "EffectAsset",
        "FunctionalEffects": "FunctionalEffect",
        "UnlockReward": "UnlockReward",
        "Resources": "Resource",
        "ItemAction": "ItemAction",
        "RewardPool": "RewardPool",
    }

    default_buff_tags = (
        "BoostBuffs",
        "Buffs",
        "Effects",
        "FunctionalEffects",
        "ItemAction",
        "Resources",
        "RewardPool",
        "UnlockReward",
    )

    def display_text_id(self, asset: ET.Element, values: ET.Element) -> str | None:
        """Text key of the display name - always the asset's own GUID.

        texts_*.xml keys its entries by the very same number, so no
        indirection is involved. ``Text/LineID`` is explicitly NOT consulted:
        it contains an internal number that would resolve to an unrelated
        string.
        """
        return self._first(values, ("Standard/GUID", "GUID"))

    def fallback_name(self, asset: ET.Element, values: ET.Element) -> str:
        """Anno 1800 often stores a readable English string inline."""
        inline = asset.findtext(".//LocaText/English/Text")
        if inline and inline.strip():
            return inline.strip()
        return super().fallback_name(asset, values)

    def find_files(self, folder: str) -> dict:
        """Also report properties.xml, which only Anno 1800 ships."""
        files = super().find_files(folder)
        files["properties"] = ""
        for root, _dirs, names in os.walk(folder):
            for name in names:
                if name.lower() == self.properties_file:
                    files["properties"] = os.path.join(root, name)
                    return files
        return files

    def detect_score(self, folder: str) -> int:
        """Score based on the text-key element and the extra data file."""
        score = 0
        files = self.find_files(folder)
        if not files["assets"]:
            return 0
        score += 1

        if files.get("properties"):
            score += 2

        for text_path in files["texts"][:1]:
            try:
                for _event, element in ET.iterparse(text_path, events=("end",)):
                    if element.tag != "Text":
                        continue
                    if element.find("GUID") is not None:
                        score += 3
                        break
                    if element.find("LineId") is not None:
                        break
            except (ET.ParseError, OSError):
                continue
        return score


register(Anno1800Game())
