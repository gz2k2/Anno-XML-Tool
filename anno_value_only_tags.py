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
"""
from __future__ import annotations

VALUE_ONLY_TAGS: frozenset[str] = frozenset({
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
