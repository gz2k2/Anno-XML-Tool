"""Shared list of buff/effect XML tags for all Anno games.

These tags are scanned for linked assets in the Buffs/Effects pane and in the
XML export. Anno 117 and Anno 1800 use the same list.

Extend this tuple when a new tag should be followed.
"""

from __future__ import annotations

DEFAULT_BUFF_TAGS: tuple[str, ...] = (
    "AdditionalFunctionalEffect",
    "BoostBuffs",
    "Buffs",
    "Effects",
    "FunctionalEffects",
    "ItemAction",
    "MythicEffect",
    "Resources",
    "RewardPool",
    "TechResearchableTrigger",
    "UnlockReward",
)
