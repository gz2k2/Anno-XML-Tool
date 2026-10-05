"""Shared list of value-only XML tags for all Anno games.

These tags hold pure quantities. They reference nothing at all: neither a
text entry in texts_*.xml nor another asset. <Amount>500</Amount> used to be
resolved against the asset database and displayed the name of the asset with
the GUID 500.

Anno 117 and Anno 1800 both read this set. Each game removes its own
``text_id_tags`` from it, so a tag that is a genuine text reference in one
game (e.g. ``LineID`` in Anno 117) is never suppressed there, while it stays
value-only in the other game (``LineID`` in Anno 1800 is an internal number).

Extend this set whenever a tag turns out to be a plain number.

User additions
--------------
Tags added in the viewer (right-click on a property > "Add to Value only
Tags") are stored in ``config_value_only.ini`` next to the application and
merged into ``VALUE_ONLY_TAGS``. They can be removed again with "Remove from
Value only Tags". Built-in tags can only be changed in this file.

Earlier versions used ``value_only.ini``; it is renamed automatically.
"""
from __future__ import annotations

import configparser
import os
import sys

#: File holding the user-defined tags (next to the EXE / this module).
USER_TAGS_FILE = "config_value_only.ini"
#: Previous file name, migrated on import.
LEGACY_USER_TAGS_FILE = "value_only.ini"

#: Section in config_value_only.ini that holds the user-defined tags.
USER_SECTION = "ValueOnlyTags"

BUILTIN_VALUE_ONLY_TAGS: frozenset[str] = frozenset({
    # Amounts / counters
    "Amount",
    "InactiveAmount",               # sibling of Amount in <Maintenance>
    "MinAmount",
    "MaxAmount",
    "FreeAmount",
    "CounterAmount",
    "ResidentAmount",
    "Elements",

    # Stats
    "MaximumHitPoints",
    "BuildModeRandomRotation",
    "LineID",                       # Anno 1800: internal number, not a text key

    # AI / trade
    "ActionWeight",
    "AgreementThreshold",
    "NotificationPriority",
    "TraderRerollInterval",
    "SellBudget",
    "BuyBudget",
    "MoneyValue",

    # Production / logistics
    "ProductionPerMinute",
    "CycleTime",
    "ProductivityFactor",
    "ClampedMaxTransporterLogisticCost",

    # Influence
    "Influence",
    "InfluenceCosts",
    "MinSpentInfluence",
    "MaxSpentInfluence",

    # Population
    "FullWeightPopulationCount",
    "NoWeightPopulationCount",

    # Chances / damage
    "BaseChance",
    "DamageExplosionChance",
    "DamageExplosionCheckMax",

    # Distances
    "Distance",
    "IndustrializationDistance",
    "FullSatisfactionDistance",
    "NoSatisfactionDistance",
    "DensityDistance",
})


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def user_tags_file() -> str:
    """Path of config_value_only.ini."""
    return os.path.join(_base_dir(), USER_TAGS_FILE)


def _migrate_legacy_file() -> None:
    """Rename value_only.ini to config_value_only.ini (once)."""
    legacy = os.path.join(_base_dir(), LEGACY_USER_TAGS_FILE)
    current = user_tags_file()
    if os.path.isfile(legacy) and not os.path.exists(current):
        try:
            os.replace(legacy, current)
        except OSError:
            # Keep working with the defaults; the old file stays untouched.
            pass


def _new_parser() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(allow_no_value=True)
    # XML tags are case-sensitive; configparser lower-cases keys by default.
    parser.optionxform = str
    return parser


def load_user_tags() -> frozenset[str]:
    """Tags stored in config_value_only.ini. A missing or broken file yields none."""
    parser = _new_parser()
    try:
        parser.read(user_tags_file(), encoding="utf-8")
    except (configparser.Error, OSError, UnicodeDecodeError):
        return frozenset()
    if not parser.has_section(USER_SECTION):
        return frozenset()
    return frozenset(tag.strip() for tag in parser.options(USER_SECTION)
                     if tag.strip())


def _write_user_tags(tags) -> None:
    """Rewrite config_value_only.ini with exactly *tags* (sorted)."""
    parser = _new_parser()
    parser.add_section(USER_SECTION)
    for tag in sorted(tags):
        parser.set(USER_SECTION, tag, None)
    with open(user_tags_file(), "w", encoding="utf-8") as handle:
        handle.write("; Value-only XML tags added in Anno XML Viewer.\n")
        handle.write("; One tag per line. These tags are never resolved as\n")
        handle.write("; text or asset reference, for Anno 117 and Anno 1800.\n\n")
        parser.write(handle)


def _set_user_tags(tags) -> None:
    """Update the module-level sets after config_value_only.ini changed."""
    global USER_VALUE_ONLY_TAGS, VALUE_ONLY_TAGS
    USER_VALUE_ONLY_TAGS = frozenset(tags)
    VALUE_ONLY_TAGS = BUILTIN_VALUE_ONLY_TAGS | USER_VALUE_ONLY_TAGS


def is_builtin(tag: str) -> bool:
    """True for tags defined in this module (cannot be removed in the UI)."""
    return (tag or "").strip() in BUILTIN_VALUE_ONLY_TAGS


def is_user_tag(tag: str) -> bool:
    """True for tags that come from config_value_only.ini."""
    return (tag or "").strip() in USER_VALUE_ONLY_TAGS


def add_user_tag(tag: str) -> bool:
    """Store *tag* in config_value_only.ini.

    Returns True if the tag was new (neither built in nor already stored).
    """
    tag = (tag or "").strip()
    if not tag or tag in VALUE_ONLY_TAGS:
        return False
    # Re-read the file so entries added by another instance are kept.
    tags = set(load_user_tags()) | set(USER_VALUE_ONLY_TAGS) | {tag}
    _write_user_tags(tags)
    _set_user_tags(tags)
    return True


def remove_user_tag(tag: str) -> bool:
    """Remove *tag* from config_value_only.ini.

    Built-in tags cannot be removed this way. Returns True if the tag was
    stored in the file and has been removed.
    """
    tag = (tag or "").strip()
    if not tag or tag not in USER_VALUE_ONLY_TAGS:
        return False
    tags = (set(load_user_tags()) | set(USER_VALUE_ONLY_TAGS)) - {tag}
    _write_user_tags(tags)
    _set_user_tags(tags)
    return True


_migrate_legacy_file()

#: Tags added by the user (config_value_only.ini).
USER_VALUE_ONLY_TAGS: frozenset[str] = load_user_tags()

#: Built-in tags plus the user additions - read by anno117.py / anno1800.py.
VALUE_ONLY_TAGS: frozenset[str] = BUILTIN_VALUE_ONLY_TAGS | USER_VALUE_ONLY_TAGS
