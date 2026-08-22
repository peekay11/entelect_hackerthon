"""
Simulation engine for Age of Enteland.

Design notes / interpretation calls (documented because the spec leaves a
few edge cases underspecified — see README "Interpretation notes"):

1. Passive trickle (town resource production + town Enteloot generation) is
   modelled with the formula given in the spec:
       accumulated = floor(tick / rate) * amount
   `amount`/`rate` can change mid-run (production upgrades, civic %
   bonuses, upkeep's temporary doubling, police-station's rate reduction).
   Whenever any of those changes for a town, we FLUSH that town's trickle
   up to the current tick (crediting the player using the *old* amount/
   rate for the elapsed window) before applying the change, and again we
   split a flush at an upkeep-expiry boundary if one falls inside the
   window being flushed. This keeps the formula exact for the common case
   and only approximates the rare case of a rate-change (police-station)
   landing inside the same open interval as another change.

2. Trickle is "auto-stored" (Assumption 6): it is credited straight into
   the player's global inventory / Enteloot balance, not into a per-town
   pool that must be collected.

3. Tick-limit cutoff (Assumption 1) is treated as a distinct rule from the
   generic invalid-action rule (Assumption 4): if an action's *nominal*
   tick cost (its real cost if it were to succeed, or 1 tick if it is
   malformed/prerequisite-invalid) would push the clock past total_ticks,
   the action is skipped, nothing else about it is applied, and the clock
   jumps straight to total_ticks (only on the first action that trips
   this). Every subsequent action in the submission is then also skipped
   the same way, since the clock is already saturated.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import data
from .state import Level, Town


# --------------------------------------------------------------------------
# Player / world state
# --------------------------------------------------------------------------

@dataclass
class TownRuntime:
    """Per-town bookkeeping needed for exact trickle accounting."""
    last_flush_tick: int = 0
    upkeep_start: Optional[int] = None   # tick the current boost window begins
    upkeep_expiry: Optional[int] = None  # tick the current boost window ends (exclusive)


@dataclass
class Player:
    position: str
    enteloot: float
    inventory: Dict[str, int] = field(default_factory=dict)
    tools: set = field(default_factory=set)

    def has(self, item: str, qty: int) -> bool:
        return self.inventory.get(item, 0) >= qty

    def add(self, item: str, qty: int) -> None:
        self.inventory[item] = self.inventory.get(item, 0) + qty

    def remove(self, item: str, qty: int) -> None:
        self.inventory[item] = self.inventory.get(item, 0) - qty


@dataclass
class LogEntry:
    index: int
    action: dict
    status: str          # "ok" | "invalid" | "skipped_tick_limit" | "rejected"
    ticks: int
    tick_before: int
    tick_after: int
    enteloot_before: float
    enteloot_after: float
    detail: str = ""


class Simulator:
    def __init__(self, level: Level):
        self.level = level
        self.level_number = level.level_number
        self.player = Player(position=level.starting_town, enteloot=float(level.starting_enteloot))
        self.town_rt: Dict[str, TownRuntime] = {tid: TownRuntime() for tid in level.towns}
        self.total_sold_count = 0
        self.total_enteloot_generated_from_trickle = 0.0
        self.log: List[LogEntry] = []
        self._tick_limit_hit = False

    # ---------------------------------------------------------------- utils
    def _town(self, tid: str) -> Town:
        return self.level.towns[tid]

    def _base_production_amount(self, town: Town, resource: str) -> int:
        return town.production_resources.get(resource, 0)

    def _resource_production_upgrade_built(self, town: Town, resource: str) -> bool:
        for name, up in data.PRODUCTION_UPGRADES.items():
            if up["boosts"] == resource and name in town.upgrades:
                return True
        return False

    def _effective_resource_amount(self, town: Town, resource: str) -> int:
        base = self._base_production_amount(town, resource)
        if base <= 0:
            return 0
        if self._resource_production_upgrade_built(town, resource):
            base = base * 2
        return int(math.floor(base))

    def _civic_pct_bonus(self, town: Town) -> float:
        total = 0.0
        for name in town.upgrades:
            up = data.CIVIC_UPGRADES.get(name)
            if up and up["effect"]["type"] == "enteloot_amount_pct":
                total += up["effect"]["value"]
        return total

    def _effective_enteloot_rate(self, town: Town) -> int:
        rate = town.enteloot_rate
        if "police-station" in town.upgrades:
            eff = data.CIVIC_UPGRADES["police-station"]["effect"]
            rate = max(eff.get("min", 1), rate + eff["value"])
        return max(1, rate)

    def _effective_enteloot_amount(self, town: Town, upkeep_active: bool) -> int:
        amount = town.enteloot_amount * (1.0 + self._civic_pct_bonus(town))
        if upkeep_active:
            amount *= data.UPKEEP_MULTIPLIER
        return int(math.floor(amount))

    def _upkeep_duration_for(self, town: Town) -> int:
        return 75 if "fire-station" in town.upgrades else data.UPKEEP_DURATION

    def _is_upkeep_active_at(self, rt: TownRuntime, tick: int) -> bool:
        return rt.upkeep_start is not None and rt.upkeep_start <= tick < rt.upkeep_expiry

    # ---------------------------------------------------- flushing (credit)
    def _flush_resource(self, tid: str, resource: str, tick: int) -> None:
        """Credit trickled `resource` for town `tid` up to `tick`."""
        town = self._town(tid)
        rate = max(1, town.production_rate)
        # resource trickle has no time-varying rate/expiry window, so a
        # single-step flush using the *current* effective amount is exact
        # for everything except mid-run production-upgrade builds, which
        # always call this flush (with the OLD amount still active)
        # immediately before updating town.upgrades.
        prev_cycles = 0  # we recompute cumulative total directly (idempotent)
        amount = self._effective_resource_amount(town, resource)
        if amount <= 0:
            return
        # We track credited totals via inventory deltas keyed per resource
        # using a running "already credited" ledger stored on the runtime.
        key = f"__trickle_{resource}"
        already = getattr(self.town_rt[tid], key, 0)
        total_now = (tick // rate) * amount
        delta = total_now - already
        if delta > 0:
            self.player.add(resource, delta)
        setattr(self.town_rt[tid], key, max(already, total_now))

    def _flush_all_resources(self, tick: int) -> None:
        for tid, town in self.level.towns.items():
            for resource in town.production_resources:
                self._flush_resource(tid, resource, tick)

    def _flush_enteloot(self, tid: str, tick: int) -> None:
        town = self._town(tid)
        rt = self.town_rt[tid]
        if tick <= rt.last_flush_tick:
            return
        # Split the flush at an upkeep-expiry boundary if one falls inside
        # the window, so the boosted/unboosted portions are each credited
        # with the correct amount.
        segments = []
        start = rt.last_flush_tick
        if rt.upkeep_expiry is not None and start < rt.upkeep_expiry < tick:
            segments.append(rt.upkeep_expiry)
        segments.append(tick)
        cur = start
        for boundary in segments:
            rate = self._effective_enteloot_rate(town)
            active = self._is_upkeep_active_at(rt, cur)
            amount = self._effective_enteloot_amount(town, active)
            c0 = cur // rate
            c1 = boundary // rate
            cycles = max(0, c1 - c0)
            credited = cycles * amount
            if credited > 0:
                self.player.enteloot += credited
                self.total_enteloot_generated_from_trickle += credited
            cur = boundary
        rt.last_flush_tick = tick

    def _flush_all_enteloot(self, tick: int) -> None:
        for tid in self.level.towns:
            self._flush_enteloot(tid, tick)

    def _flush_all(self, tick: int) -> None:
        self._flush_all_resources(tick)
        self._flush_all_enteloot(tick)

    # --------------------------------------------------------------- run
    def run(self, actions: List[dict]) -> "SimResult":
        for i, action in enumerate(actions):
            self._process_action(i, action)
            if self.player.position and self._current_tick_after_last() >= self.level.total_ticks:
                # Continue looping so every remaining action is still logged
                # as skipped (matches "run continues, logging each entry").
                pass
        # final flush at the run's end tick
        end_tick = self.log[-1].tick_after if self.log else 0
        end_tick = min(end_tick, self.level.total_ticks) if end_tick else 0
        self._flush_all(min(max(end_tick, 0), self.level.total_ticks))
        return SimResult(self)

    def _current_tick_after_last(self) -> int:
        return self.log[-1].tick_after if self.log else 0

    # --------------------------------------------------------- per-action
    def _process_action(self, index: int, action: Any) -> None:
        tick_before = self._current_tick_after_last()
        ent_before = self.player.enteloot

        if tick_before >= self.level.total_ticks:
            self.log.append(LogEntry(index, action if isinstance(action, dict) else {"raw": action},
                                      "skipped_tick_limit", 0, tick_before, tick_before,
                                      ent_before, ent_before, "clock already at total_ticks"))
            return

        self._flush_all(tick_before)  # bring balances current before validating

        outcome = self._validate(action, tick_before)
        # outcome: ("execute", ticks, apply_fn, detail) | ("invalid", detail)
        kind = outcome[0]
        nominal_ticks = outcome[1] if kind == "execute" else data.INVALID_ACTION_TICKS

        if tick_before + nominal_ticks > self.level.total_ticks:
            self.log.append(LogEntry(index, action if isinstance(action, dict) else {"raw": action},
                                      "skipped_tick_limit", 0, tick_before, self.level.total_ticks,
                                      ent_before, self.player.enteloot,
                                      "action would exceed total_ticks; clock advanced to end"))
            return

        if kind == "invalid":
            tick_after = tick_before + data.INVALID_ACTION_TICKS
            self.log.append(LogEntry(index, action if isinstance(action, dict) else {"raw": action},
                                      "invalid", data.INVALID_ACTION_TICKS, tick_before, tick_after,
                                      ent_before, self.player.enteloot, outcome[1]))
            return

        # execute
        _, ticks, apply_fn, detail = outcome
        apply_fn()
        tick_after = tick_before + ticks
        self.log.append(LogEntry(index, action, "ok", ticks, tick_before, tick_after,
                                  ent_before, self.player.enteloot, detail))

    # ------------------------------------------------------------- validate
    def _validate(self, action: Any, tick: int):
        if not isinstance(action, dict):
            return ("invalid", "not an object")
        atype = action.get("type")
        if not isinstance(atype, str):
            return ("invalid", "missing/invalid 'type'")

        handler = getattr(self, f"_h_{atype.replace('-', '_')}", None)
        if handler is None:
            return ("invalid", f"unknown action type '{atype}'")
        return handler(action, tick)

    # ------------------------------------------------------------- travel
    def _h_travel(self, action: dict, tick: int):
        dest = action.get("destination")
        if not isinstance(dest, str):
            return ("invalid", "missing/invalid 'destination'")
        fast_req = action.get("fast", False)
        if not isinstance(fast_req, bool):
            return ("invalid", "'fast' must be a boolean")
        origin = self.player.position
        if dest not in self.level.towns and dest not in self.level.nodes:
            return ("invalid", f"unknown destination '{dest}'")
        std, fastr = self.level.routes_between(origin, dest)
        if fast_req:
            if not data.level_allows(self.level_number, "fast_routes"):
                return ("invalid", "fast routes not unlocked at this level")
            if fastr is None:
                return ("invalid", "no fast route exists between these vertices")
            route = fastr
        else:
            if std is None:
                return ("invalid", "no standard route exists between these vertices")
            route = std
        toll = route.toll
        if toll > self.player.enteloot:
            return ("invalid", "insufficient Enteloot to pay toll")
        weight = route.weight
        if "boots" in self.player.tools:
            weight = max(1, weight - 1)

        def apply():
            self.player.enteloot -= toll
            self.player.position = dest

        return ("execute", weight, apply, f"travel {origin}->{dest} ({'fast' if fast_req else 'standard'})")

    # --------------------------------------------------------------- gather
    def _h_gather(self, action: dict, tick: int):
        node = self.level.nodes.get(self.player.position)
        if node is None:
            return ("invalid", "not currently at a resource node")
        if node.type == "mine" and not data.level_allows(self.level_number, "ore"):
            return ("invalid", "mine nodes not unlocked at this level")
        gtime = node.gather_time
        if "pickaxe" in self.player.tools:
            gtime = max(1, gtime - 1)

        def apply():
            self.player.add(node.resource, node.yield_)

        return ("execute", gtime, apply, f"gather {node.resource} x{node.yield_} at {node.id}")

    # ------------------------------------------------------------------ buy
    def _h_buy(self, action: dict, tick: int):
        item = action.get("item")
        qty = action.get("quantity")
        if not isinstance(item, str) or not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            return ("invalid", "missing/invalid 'item' or 'quantity'")
        town = self.level.towns.get(self.player.position)
        if town is None:
            return ("invalid", "not currently at a town")
        res = data.RESOURCES.get(item)
        if res is None:
            return ("invalid", f"'{item}' is not a purchasable resource")
        if res["buy_price"] is None:
            return ("invalid", f"'{item}' cannot be bought (e.g. ore)")
        if item not in town.production_resources:
            return ("invalid", f"{town.id} does not produce/sell '{item}'")
        cost = res["buy_price"] * qty
        if cost > self.player.enteloot:
            return ("invalid", "insufficient Enteloot")

        def apply():
            self.player.enteloot -= cost
            self.player.add(item, qty)

        return ("execute", 1, apply, f"buy {qty} {item} @ {res['buy_price']} = {cost}")

    # ----------------------------------------------------------------- sell
    def _h_sell(self, action: dict, tick: int):
        item = action.get("item")
        qty = action.get("quantity")
        if not isinstance(item, str) or not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            return ("invalid", "missing/invalid 'item' or 'quantity'")
        town = self.level.towns.get(self.player.position)
        if town is None:
            return ("invalid", "not currently at a town")
        if not self.player.has(item, qty):
            return ("invalid", f"insufficient '{item}' in inventory")

        if item in data.RESOURCES:
            price = data.RESOURCES[item]["sell_price"]
        elif item in data.RECIPES:
            price = town.item_rates.get(item)
            if price is None:
                return ("invalid", f"{town.id} has no item-rate for '{item}'")
        else:
            return ("invalid", f"'{item}' is not sellable (component/tool)")

        revenue = price * qty

        def apply():
            self.player.remove(item, qty)
            self.player.enteloot += revenue
            self.total_sold_count += qty

        return ("execute", 1, apply, f"sell {qty} {item} @ {price} = {revenue}")

    # ---------------------------------------------------------------- craft
    def _h_craft(self, action: dict, tick: int):
        if not data.level_allows(self.level_number, "recipes"):
            return ("invalid", "crafting not unlocked at this level")
        item = action.get("item")
        qty = action.get("quantity")
        if not isinstance(item, str) or not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            return ("invalid", "missing/invalid 'item' or 'quantity'")
        town = self.level.towns.get(self.player.position)
        if town is None:
            return ("invalid", "not currently at a town")

        is_tool = item in data.TOOLS
        if is_tool:
            if not data.level_allows(self.level_number, "tools"):
                return ("invalid", "tools not unlocked at this level")
            if item in self.player.tools:
                return ("invalid", f"tool '{item}' already crafted (once per run)")
            recipe = data.TOOLS[item]
        elif item in data.ALL_CRAFTABLES:
            recipe = data.ALL_CRAFTABLES[item]
            if recipe.get("min_level", 1) > self.level_number:
                return ("invalid", f"'{item}' not unlocked at this level")
        else:
            return ("invalid", f"unknown craftable '{item}'")

        for inp, need in recipe["inputs"].items():
            if not self.player.has(inp, need * qty):
                return ("invalid", f"insufficient '{inp}' for crafting {item}")

        craft_time = data.CRAFT_TIME_AFFINITY if town.has_affinity("crafting") else data.CRAFT_TIME_BASE
        ticks = craft_time * qty

        def apply():
            for inp, need in recipe["inputs"].items():
                self.player.remove(inp, need * qty)
            if is_tool:
                self.player.tools.add(item)
            else:
                self.player.add(item, qty)

        return ("execute", ticks, apply, f"craft {item} x{qty} ({ticks} ticks)")

    # ---------------------------------------------------------------- build
    def _h_build(self, action: dict, tick: int):
        if not data.level_allows(self.level_number, "production_upgrades"):
            return ("invalid", "building not unlocked at this level")
        upgrade = action.get("upgrade")
        if not isinstance(upgrade, str):
            return ("invalid", "missing/invalid 'upgrade'")
        town = self.level.towns.get(self.player.position)
        if town is None:
            return ("invalid", "not currently at a town")
        udef = data.ALL_UPGRADES.get(upgrade)
        if udef is None:
            return ("invalid", f"unknown upgrade '{upgrade}'")
        if udef.get("min_level", 1) > self.level_number:
            return ("invalid", f"'{upgrade}' not unlocked at this level")
        if upgrade in town.upgrades:
            return ("invalid", f"'{upgrade}' already built at {town.id}")

        prereq = udef.get("prerequisite")
        if prereq:
            if prereq["type"] == "any_production_upgrades":
                have = sum(1 for n in town.upgrades if n in data.PRODUCTION_UPGRADES)
                if have < prereq["count"]:
                    return ("invalid", f"needs {prereq['count']} production upgrade(s) at {town.id} first")
            elif prereq["type"] == "specific_upgrade":
                if prereq["upgrade"] not in town.upgrades:
                    return ("invalid", f"needs '{prereq['upgrade']}' built at {town.id} first")

        for comp, need in udef["components"].items():
            if not self.player.has(comp, need):
                return ("invalid", f"insufficient component '{comp}' for {upgrade}")
        cost = udef["enteloot_cost"]
        if cost > self.player.enteloot:
            return ("invalid", "insufficient Enteloot")
        ticks = udef["build_time"]

        def apply():
            for comp, need in udef["components"].items():
                self.player.remove(comp, need)
            self.player.enteloot -= cost
            # flush this town's trickle up to *now* (pre-build values) before
            # the upgrade changes its production/enteloot formula
            self._flush_resource_group_for_town(town.id, tick)
            self._flush_enteloot(town.id, tick)
            town.upgrades.add(upgrade)

        return ("execute", ticks, apply, f"build {upgrade} at {town.id} ({ticks} ticks, {cost} Enteloot)")

    def _flush_resource_group_for_town(self, tid: str, tick: int) -> None:
        town = self._town(tid)
        for resource in town.production_resources:
            self._flush_resource(tid, resource, tick)

    # --------------------------------------------------------------- upkeep
    def _h_upkeep(self, action: dict, tick: int):
        if not data.level_allows(self.level_number, "upkeep"):
            return ("invalid", "upkeep not unlocked at this level")
        town = self.level.towns.get(self.player.position)
        if town is None:
            return ("invalid", "not currently at a town")
        ticks = data.UPKEEP_ACTION_TICKS

        def apply():
            self._flush_enteloot(town.id, tick)
            rt = self.town_rt[town.id]
            start = tick + ticks
            rt.upkeep_start = start
            rt.upkeep_expiry = start + self._upkeep_duration_for(town)
            rt.last_flush_tick = start  # nothing to credit between tick and start; boost starts exactly at start

        return ("execute", ticks, apply, f"upkeep boost triggered at {town.id}")


@dataclass
class SimResult:
    sim: Simulator

    @property
    def final_tick(self) -> int:
        return self.sim._current_tick_after_last()

    @property
    def final_enteloot(self) -> float:
        return self.sim.player.enteloot

    @property
    def final_inventory(self) -> Dict[str, int]:
        return dict(self.sim.player.inventory)

    @property
    def total_sold(self) -> int:
        return self.sim.total_sold_count

    def upgrades_built(self) -> Dict[str, List[str]]:
        return {tid: sorted(t.upgrades) for tid, t in self.sim.level.towns.items() if t.upgrades}

    def to_log_rows(self) -> List[dict]:
        rows = []
        for e in self.sim.log:
            rows.append({
                "index": e.index,
                "action": e.action,
                "status": e.status,
                "ticks": e.ticks,
                "tick_before": e.tick_before,
                "tick_after": e.tick_after,
                "enteloot_before": e.enteloot_before,
                "enteloot_after": e.enteloot_after,
                "detail": e.detail,
            })
        return rows
