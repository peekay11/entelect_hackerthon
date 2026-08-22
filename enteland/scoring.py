"""
Proxy / estimated scoring.

IMPORTANT: the spec describes Age of Enteland's scoring only qualitatively
(see "Scoring" section of the spec). It gives:
  - exact score_value points per upgrade (used directly below), and
  - one *proposed, unconfirmed* formula in the "Ideas" appendix
    (distribution_multiplier = built / total_possible), which is explicitly
    listed as an idea, not a confirmed rule.

There is no official, fully-specified formula for:
  - Level 1's "Enteloot generation + held-item value + sell-count multiplier"
  - exactly how the Level 2-4 "development spread across towns" multiplier
    is computed.

The functions below implement a reasonable, clearly-labelled ESTIMATE good
enough to let a solver compare candidate strategies against each other.
They are NOT guaranteed to match the official judge's score. Swap in the
real formula here the moment Entelect publishes/clarifies it — everything
else in the engine (ticks, Enteloot, inventory, upgrades) is exact per the
spec and does not depend on this module.
"""
from __future__ import annotations

from typing import Dict

from . import data
from .simulator import SimResult


def _held_inventory_value(result: SimResult) -> float:
    total = 0.0
    for item, qty in result.final_inventory.items():
        if qty <= 0:
            continue
        if item in data.RESOURCES:
            total += qty * data.RESOURCES[item]["sell_price"]
        elif item in data.RECIPES:
            lo, hi = data.RECIPES[item]["sell_range"]
            total += qty * ((lo + hi) / 2)
        # construction components / tools held at the end: no direct sell value
    return total


def estimate_score_level1(result: SimResult) -> float:
    enteloot_generated = result.sim.total_enteloot_generated_from_trickle
    held_value = _held_inventory_value(result)
    sell_multiplier = 1.0 + 0.02 * result.total_sold
    return (enteloot_generated + held_value) * sell_multiplier


def estimate_score_level2plus(result: SimResult) -> float:
    built = result.upgrades_built()
    infra_points = 0.0
    towns_with_upgrades = 0
    total_possible = len(data.ALL_UPGRADES) * len(result.sim.level.towns)
    built_count = 0
    for tid, names in built.items():
        if names:
            towns_with_upgrades += 1
        for n in names:
            udef = data.ALL_UPGRADES.get(n, {})
            infra_points += udef.get("score_value", 0)
            built_count += 1
    n_towns = max(1, len(result.sim.level.towns))
    distribution_multiplier = 1.0 + (towns_with_upgrades / n_towns)  # spreads across towns -> bonus
    invested_bonus = 0.0  # Enteloot *spent* on building already shows up via infra_points
    hoard_penalty_weight = 0.05  # hoarded Enteloot scores "far less" than invested
    return infra_points * distribution_multiplier + hoard_penalty_weight * result.final_enteloot


def estimate_score(result: SimResult, level_number: int) -> float:
    if level_number == 1:
        return estimate_score_level1(result)
    return estimate_score_level2plus(result)
