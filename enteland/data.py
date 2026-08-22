"""
Global constant tables for Age of Enteland.

These are identical across every level (per the spec's "Data organisation"
note) so they are NOT part of a level JSON file. They live in
data/resources.json (the digitised version of the spec's tables) and are
loaded once here.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "resources.json")

with open(_DATA_PATH, "r", encoding="utf-8") as f:
    RAW = json.load(f)

CONSTANTS = RAW["constants"]
LEVEL_UNLOCKS: Dict[str, List[str]] = RAW["level_unlocks"]
RESOURCES: Dict[str, dict] = RAW["resources"]
NODE_TYPES: Dict[str, dict] = RAW["node_types"]
RECIPES: Dict[str, dict] = RAW["recipes"]
COMPONENTS: Dict[str, dict] = RAW["components"]
PRODUCTION_UPGRADES: Dict[str, dict] = RAW["upgrades"]["production"]
CIVIC_UPGRADES: Dict[str, dict] = RAW["upgrades"]["civic"]
ALL_UPGRADES: Dict[str, dict] = {**PRODUCTION_UPGRADES, **CIVIC_UPGRADES}
TOOLS: Dict[str, dict] = RAW["tools"]

CRAFT_TIME_BASE = CONSTANTS["craft_time_base"]           # 2
CRAFT_TIME_AFFINITY = CONSTANTS["craft_time_affinity"]    # 1
INVALID_ACTION_TICKS = CONSTANTS["invalid_action_ticks"]  # 1
UPKEEP_ACTION_TICKS = CONSTANTS["upkeep_action_ticks"]    # 5
UPKEEP_MULTIPLIER = CONSTANTS["upkeep_boost_multiplier"]  # 2
UPKEEP_DURATION = CONSTANTS["upkeep_boost_duration_ticks"]  # 50
MIN_TRAVEL_TICKS = CONSTANTS["min_travel_ticks"]          # 1
MIN_GATHER_TICKS = CONSTANTS["min_gather_ticks"]          # 1

# A "craftable" name -> is it a sellable good, a construction component, or a tool
ALL_CRAFTABLES = {}
for name, r in RECIPES.items():
    ALL_CRAFTABLES[name] = {**r, "kind": "recipe"}
for name, c in COMPONENTS.items():
    ALL_CRAFTABLES[name] = {**c, "kind": "component"}


def level_allows(level: int, feature: str) -> bool:
    """True if `feature` is unlocked by `level` (levels are cumulative)."""
    for lvl in range(1, level + 1):
        if feature in LEVEL_UNLOCKS.get(str(lvl), []):
            return True
    return False


def min_level_for(entry: dict, default: int = 1) -> int:
    return entry.get("min_level", default)
