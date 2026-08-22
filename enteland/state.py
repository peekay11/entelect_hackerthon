"""Per-level data structures (map, towns, nodes, routes, run params)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Route:
    a: str
    b: str
    weight: int
    toll: int = 0
    fast: bool = False

    def other(self, v: str) -> str:
        return self.b if v == self.a else self.a


@dataclass
class Node:
    id: str
    type: str
    resource: str
    yield_: int
    gather_time: int


@dataclass
class Town:
    id: str
    production_rate: int
    production_resources: Dict[str, int]
    enteloot_rate: int
    enteloot_amount: int
    affinities: List[str] = field(default_factory=list)
    item_rates: Dict[str, int] = field(default_factory=dict)
    # Mutable run-time state (built upgrades, upkeep timer) lives here too,
    # since each upgrade may only be built once per town.
    upgrades: set = field(default_factory=set)
    upkeep_active_until: Optional[int] = None  # tick at which the boost expires (exclusive)

    def has_affinity(self, kind: str = "crafting") -> bool:
        return kind in self.affinities


@dataclass
class Level:
    level_number: int
    total_ticks: int
    starting_town: str
    starting_enteloot: int
    towns: Dict[str, Town]
    nodes: Dict[str, Node]
    routes: List[Route]
    # adjacency: vertex -> list of Route
    adjacency: Dict[str, List[Route]] = field(default_factory=dict)

    @staticmethod
    def load(path: str, level_number: int) -> "Level":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return Level.from_dict(raw, level_number)

    @staticmethod
    def from_dict(raw: dict, level_number: int) -> "Level":
        run = raw["run"]
        towns = {}
        for tid, t in raw["towns"].items():
            towns[tid] = Town(
                id=tid,
                production_rate=t["production"]["rate"],
                production_resources=dict(t["production"]["resources"]),
                enteloot_rate=t["enteloot"]["rate"],
                enteloot_amount=t["enteloot"]["amount"],
                affinities=list(t.get("affinities", [])),
                item_rates=dict(t.get("item-rates", {})),
                upgrades=set(t.get("upgrades", [])),
            )
        nodes = {}
        for nid, n in raw.get("nodes", {}).items():
            nodes[nid] = Node(
                id=nid,
                type=n["type"],
                resource=n["resource"],
                yield_=n["yield"],
                gather_time=n["gather-time"],
            )
        routes = []
        for r in raw.get("routes", []):
            a, b = r["between"]
            routes.append(Route(a=a, b=b, weight=r["weight"], toll=r.get("toll", 0),
                                 fast=r.get("toll", 0) > 0))
        level = Level(
            level_number=level_number,
            total_ticks=run["total_ticks"],
            starting_town=run["starting_town"],
            starting_enteloot=run["starting_enteloot"],
            towns=towns,
            nodes=nodes,
            routes=routes,
        )
        adjacency: Dict[str, List[Route]] = {}
        for r in routes:
            adjacency.setdefault(r.a, []).append(r)
            adjacency.setdefault(r.b, []).append(r)
        level.adjacency = adjacency
        return level

    def vertex_kind(self, vid: str) -> str:
        if vid in self.towns:
            return "town"
        if vid in self.nodes:
            return "node"
        return "unknown"

    def routes_between(self, a: str, b: str) -> Tuple[Optional[Route], Optional[Route]]:
        """Return (standard_route, fast_route) between a and b, either may be None."""
        std, fast = None, None
        for r in self.adjacency.get(a, []):
            if r.other(a) == b:
                if r.toll > 0:
                    fast = r
                else:
                    std = r
        return std, fast
