"""
A greedy, heuristic baseline solver for Age of Enteland.

This is NOT a true optimiser (the real problem — routing + gather/buy/craft/
sell/build scheduling under a shared tick budget — is a large combinatorial
planning problem well beyond a one-shot greedy pass). What it does:

  - Runs actions directly against a live `Simulator`, so every action it
    emits is guaranteed to be exactly what gets logged (no drift between
    "planned" and "actually valid").
  - At each step, scores a handful of candidate "programs" (repeatable
    gather-and-sell loops, craft-and-sell loops, and — once affordable —
    upgrade-building chains with full construction-component expansion)
    by Enteloot-or-score gained per tick spent, and runs the best one.
  - Repeats until the tick budget runs out or nothing profitable remains.

Treat this as a working starting point to iterate on (better routing that
weighs fast-route tolls, multi-leg component sourcing, look-ahead instead of
greedy, etc.) rather than a finished, tuned strategy.
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from . import data
from .state import Level
from .simulator import Simulator, SimResult

SCORE_WEIGHT = 1.0  # how many "profit units" one infrastructure score point is worth


class GreedySolver:
    def __init__(self, level: Level, level_number: int, verbose: bool = False):
        self.level = level
        self.level_number = level_number
        self.sim = Simulator(level)
        self.actions: List[dict] = []
        self.verbose = verbose
        self.dist, self.nxt = self._build_all_pairs()

    # ------------------------------------------------------------ pathing
    def _build_all_pairs(self):
        """Dijkstra all-pairs shortest path over STANDARD routes only
        (fast routes are ignored by the planner for simplicity; the engine
        itself fully supports them for hand-written/other submissions)."""
        verts = list(self.level.towns.keys()) + list(self.level.nodes.keys())
        graph: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for r in self.level.routes:
            if r.toll > 0:
                continue
            graph[r.a].append((r.b, r.weight))
            graph[r.b].append((r.a, r.weight))

        dist = {}
        nxt = {}
        for src in verts:
            d = {src: 0}
            prev = {}
            pq = [(0, src)]
            visited = set()
            while pq:
                du, u = heapq.heappop(pq)
                if u in visited:
                    continue
                visited.add(u)
                for v, w in graph.get(u, []):
                    nd = du + w
                    if nd < d.get(v, math.inf):
                        d[v] = nd
                        prev[v] = u
                        heapq.heappush(pq, (nd, v))
            dist[src] = d
            nxt[src] = prev
        return dist, nxt

    def path(self, a: str, b: str) -> Optional[List[str]]:
        if a == b:
            return [a]
        if b not in self.dist.get(a, {}):
            return None
        path = [b]
        cur = b
        while cur != a:
            cur = self.nxt[a][cur]
            path.append(cur)
        path.reverse()
        return path

    def d(self, a: str, b: str) -> float:
        return self.dist.get(a, {}).get(b, math.inf)

    def _travel_actions(self, path: List[str]) -> List[dict]:
        return [{"type": "travel", "destination": v} for v in path[1:]]

    # ------------------------------------------------------------- helpers
    def _nearest_node_for(self, resource: str, frm: str) -> Optional[str]:
        best, best_d = None, math.inf
        for nid, node in self.level.nodes.items():
            if node.resource != resource:
                continue
            if node.type == "mine" and self.level_number < 3:
                continue
            dd = self.d(frm, nid)
            if dd < best_d:
                best, best_d = nid, dd
        return best

    def _nearest_producing_town(self, resource: str, frm: str) -> Optional[str]:
        best, best_d = None, math.inf
        for tid, town in self.level.towns.items():
            if resource not in town.production_resources:
                continue
            dd = self.d(frm, tid)
            if dd < best_d:
                best, best_d = tid, dd
        return best

    def _nearest_affinity_town(self, frm: str) -> Optional[str]:
        best, best_d = None, math.inf
        for tid, town in self.level.towns.items():
            if not town.has_affinity("crafting"):
                continue
            dd = self.d(frm, tid)
            if dd < best_d:
                best, best_d = tid, dd
        return best

    def _best_sell_town(self, good: str, frm: str, radius_bias: float = 0.15) -> Optional[str]:
        """Pick a town balancing item-rate against distance."""
        best, best_score = None, -math.inf
        for tid, town in self.level.towns.items():
            rate = town.item_rates.get(good)
            if rate is None:
                continue
            dd = self.d(frm, tid)
            if dd == math.inf:
                continue
            score = rate - radius_bias * rate * dd  # discount by travel
            if score > best_score:
                best, best_score = tid, score
        return best

    # ---------------------------------------------------- component chain
    def _expand(self, top_items: Dict[str, int]):
        leaf_needs = defaultdict(int)
        comp_needs = defaultdict(int)

        def visit(name, qty):
            if name in data.RESOURCES:
                leaf_needs[name] += qty
                return
            entry = data.COMPONENTS.get(name)
            if entry is None:
                return
            comp_needs[name] += qty
            for inp, need in entry["inputs"].items():
                visit(inp, need * qty)

        for name, qty in top_items.items():
            visit(name, qty)
        return leaf_needs, comp_needs

    def _toposort(self, comp_needs: Dict[str, int]) -> List[str]:
        remaining = dict(comp_needs)
        ordered = []
        guard = 0
        while remaining and guard < 20:
            guard += 1
            ready = [c for c in remaining
                     if all(inp not in remaining for inp in data.COMPONENTS[c]["inputs"])]
            if not ready:
                ready = list(remaining.keys())
            for c in ready:
                ordered.append(c)
                del remaining[c]
        return ordered

    def _source_leaf_plan(self, resource: str, qty: int, at_town: str):
        """Return (actions, ticks, enteloot_cost) to get `qty` of `resource`
        into inventory while ending back at `at_town`, choosing gather vs
        buy whichever costs fewer ticks. None if infeasible."""
        town = self.level.towns[at_town]
        options = []

        res = data.RESOURCES[resource]
        if resource in town.production_resources and res["buy_price"] is not None:
            options.append(("buy_here", 1, res["buy_price"] * qty))
        else:
            buy_town = self._nearest_producing_town(resource, at_town) if res["buy_price"] is not None else None
            if buy_town is not None and self.d(at_town, buy_town) < math.inf:
                travel = 2 * self.d(at_town, buy_town)
                options.append(("buy_away", travel + 1, res["buy_price"] * qty, buy_town))

        node_id = self._nearest_node_for(resource, at_town)
        if node_id is not None and self.d(at_town, node_id) < math.inf:
            node = self.level.nodes[node_id]
            gtime = node.gather_time
            gathers_needed = math.ceil(qty / node.yield_)
            travel = 2 * self.d(at_town, node_id)
            options.append(("gather", travel + gathers_needed * gtime, 0, node_id, gathers_needed))

        if not options:
            return None
        options.sort(key=lambda o: o[1])
        choice = options[0]

        actions = []
        if choice[0] == "buy_here":
            actions.append({"type": "buy", "item": resource, "quantity": qty})
            return actions, choice[1], choice[2]
        if choice[0] == "buy_away":
            _, ticks, cost, buy_town = choice
            actions += self._travel_actions(self.path(at_town, buy_town))
            actions.append({"type": "buy", "item": resource, "quantity": qty})
            actions += self._travel_actions(self.path(buy_town, at_town))
            return actions, ticks, cost
        if choice[0] == "gather":
            _, ticks, cost, node_id, gathers_needed = choice
            actions += self._travel_actions(self.path(at_town, node_id))
            actions += [{"type": "gather"} for _ in range(gathers_needed)]
            actions += self._travel_actions(self.path(node_id, at_town))
            return actions, ticks, cost
        return None

    def _prog_raw_sell(self, resource: str, batch_yield_target: int = 400):
        cur = self.sim.player.position
        node_id = self._nearest_node_for(resource, cur)
        if node_id is None:
            return None
        node = self.level.nodes[node_id]
        town_id = self._nearest_producing_town(resource, node_id) or self._nearest_town_any(node_id)
        if town_id is None:
            return None
        gather_time = node.gather_time
        if "pickaxe" in self.sim.player.tools:
            gather_time = max(1, gather_time - 1)
        batch = max(1, math.ceil(batch_yield_target / node.yield_))
        d_to_node = self.d(cur, node_id)
        d_node_town = self.d(node_id, town_id)
        if d_to_node == math.inf or d_node_town == math.inf:
            return None
            
        travel_ticks = d_to_node + d_node_town + 1
        max_gathers = (self._remaining_ticks() - travel_ticks) // gather_time
        if max_gathers <= 0:
            return None
            
        batch = max_gathers
        ticks = travel_ticks + batch * gather_time
        gained = batch * node.yield_ * data.RESOURCES[resource]["sell_price"]
        actions = self._travel_actions(self.path(cur, node_id))
        actions += [{"type": "gather"} for _ in range(batch)]
        actions += self._travel_actions(self.path(node_id, town_id))
        actions.append({"type": "sell", "item": resource, "quantity": batch * node.yield_})
        return gained, ticks, actions

    def _nearest_town_any(self, frm: str) -> Optional[str]:
        best, best_d = None, math.inf
        for tid in self.level.towns:
            dd = self.d(frm, tid)
            if dd < best_d:
                best, best_d = tid, dd
        return best

    def _prog_craft_sell(self, recipe_name: str, batch: int = 8):
        cur = self.sim.player.position
        recipe = data.RECIPES[recipe_name]
        affinity_town = self._nearest_affinity_town(cur)
        candidates = [t for t in [affinity_town] if t]
        best_sell_ref = self._best_sell_town(recipe_name, cur) or self._nearest_town_any(cur)
        if best_sell_ref is None:
            return None
        craft_town = affinity_town if affinity_town is not None else best_sell_ref
        if self.d(cur, craft_town) == math.inf:
            return None

        actions = self._travel_actions(self.path(cur, craft_town))
        ticks = self.d(cur, craft_town)
        cost = 0
        
        # We need to find the max batch we can afford time-wise.
        # This requires calculating per-item time cost.
        # For a simple heuristic, let's bump batch to a large safe number (e.g., 50) 
        # or calculate it. For now, let's just use 50 instead of 8 to get a massive boost over baseline!
        batch = 50
        for inp, need in recipe["inputs"].items():
            sub = self._source_leaf_plan(inp, need * batch, craft_town)
            if sub is None:
                return None
            sub_actions, sub_ticks, sub_cost = sub
            actions += sub_actions
            ticks += sub_ticks
            cost += sub_cost

        craft_time = data.CRAFT_TIME_AFFINITY if self.level.towns[craft_town].has_affinity("crafting") else data.CRAFT_TIME_BASE
        craft_ticks = craft_time * batch
        actions.append({"type": "craft", "item": recipe_name, "quantity": batch})
        ticks += craft_ticks

        sell_town = self._best_sell_town(recipe_name, craft_town) or craft_town
        actions += self._travel_actions(self.path(craft_town, sell_town))
        ticks += self.d(craft_town, sell_town)
        price = self.level.towns[sell_town].item_rates.get(recipe_name, 0)
        actions.append({"type": "sell", "item": recipe_name, "quantity": batch})
        ticks += 1
        gained = price * batch - cost
        if gained <= 0:
            return None
        return gained, ticks, actions

    def _prog_build(self, upgrade_name: str, udef: dict):
        cur = self.sim.player.position
        is_civic = upgrade_name in data.CIVIC_UPGRADES
        target_town = None
        if is_civic and udef.get("prerequisite"):
            prereq = udef["prerequisite"]
            for tid, town in self.level.towns.items():
                if upgrade_name in town.upgrades:
                    continue
                if prereq["type"] == "any_production_upgrades":
                    have = sum(1 for n in town.upgrades if n in data.PRODUCTION_UPGRADES)
                    ok = have >= prereq["count"]
                elif prereq["type"] == "specific_upgrade":
                    ok = prereq["upgrade"] in town.upgrades
                else:
                    ok = False
                if ok:
                    dd = self.d(cur, tid)
                    if dd < math.inf and (target_town is None or dd < self.d(cur, target_town)):
                        target_town = tid
            if target_town is None:
                return None
        else:
            # no prerequisite (production upgrades): any not-yet-built town works;
            # prefer a crafting-affinity town for speed.
            best, best_d = None, math.inf
            for tid, town in self.level.towns.items():
                if upgrade_name in town.upgrades:
                    continue
                dd = self.d(cur, tid) - (1000 if town.has_affinity("crafting") else 0)
                if dd < best_d:
                    best, best_d = tid, dd
            target_town = best
            if target_town is None:
                return None

        leaf_needs, comp_needs = self._expand(udef["components"])
        order = self._toposort(comp_needs)

        actions = self._travel_actions(self.path(cur, target_town))
        ticks = self.d(cur, target_town)
        cost = 0
        for resource, qty in leaf_needs.items():
            sub = self._source_leaf_plan(resource, qty, target_town)
            if sub is None:
                return None
            sub_actions, sub_ticks, sub_cost = sub
            actions += sub_actions
            ticks += sub_ticks
            cost += sub_cost

        craft_time = data.CRAFT_TIME_AFFINITY if self.level.towns[target_town].has_affinity("crafting") else data.CRAFT_TIME_BASE
        for comp_name in order:
            qty = comp_needs[comp_name]
            actions.append({"type": "craft", "item": comp_name, "quantity": qty})
            ticks += craft_time * qty

        cost += udef["enteloot_cost"]
        if cost > self.sim.player.enteloot:
            return None  # not affordable yet this round

        actions.append({"type": "build", "upgrade": upgrade_name})
        ticks += udef["build_time"]

        gained = SCORE_WEIGHT * udef["score_value"]
        return gained, ticks, actions

    def _prog_tool(self, tool_name: str, tdef: dict):
        """Crafting boots/pickaxe has no direct score/Enteloot payoff — its
        value is future ticks saved on every subsequent travel/gather. That
        is hard to price exactly without simulating the rest of the run, so
        we use a flat heuristic value (spec explicitly recommends investing
        early ticks here since savings compound)."""
        TOOL_VALUE = 1500.0
        cur = self.sim.player.position
        target_town = self._nearest_affinity_town(cur) or self._nearest_town_any(cur)
        if target_town is None or self.d(cur, target_town) == math.inf:
            return None
        leaf_needs, comp_needs = self._expand(tdef["inputs"])
        order = self._toposort(comp_needs)
        actions = self._travel_actions(self.path(cur, target_town))
        ticks = self.d(cur, target_town)
        cost = 0
        for resource, qty in leaf_needs.items():
            sub = self._source_leaf_plan(resource, qty, target_town)
            if sub is None:
                return None
            sub_actions, sub_ticks, sub_cost = sub
            actions += sub_actions
            ticks += sub_ticks
            cost += sub_cost
        craft_time = data.CRAFT_TIME_AFFINITY if self.level.towns[target_town].has_affinity("crafting") else data.CRAFT_TIME_BASE
        for comp_name in order:
            qty = comp_needs[comp_name]
            actions.append({"type": "craft", "item": comp_name, "quantity": qty})
            ticks += craft_time * qty
        if cost > self.sim.player.enteloot:
            return None
        actions.append({"type": "craft", "item": tool_name, "quantity": 1})
        ticks += craft_time * 1
        return TOOL_VALUE, ticks, actions

    # ----------------------------------------------------------------- run
    def _remaining_ticks(self) -> int:
        return self.level.total_ticks - self.sim._current_tick_after_last()

    def run(self, max_iterations: int = 2000) -> Tuple[List[dict], SimResult]:
        it = 0
        while self._remaining_ticks() > 1 and it < max_iterations:
            it += 1
            best = None  # (profit_per_tick, gained, ticks, actions, label)
            candidates = []

            for resource in data.RESOURCES:
                if resource == "ore" and self.level_number < 3:
                    continue
                prog = self._prog_raw_sell(resource)
                if prog:
                    candidates.append((*prog, f"gather-sell {resource}"))

            if data.level_allows(self.level_number, "recipes"):
                for name in data.RECIPES:
                    prog = self._prog_craft_sell(name)
                    if prog:
                        candidates.append((*prog, f"craft-sell {name}"))

            if data.level_allows(self.level_number, "tools"):
                for name, tdef in data.TOOLS.items():
                    if name in self.sim.player.tools:
                        continue
                    prog = self._prog_tool(name, tdef)
                    if prog:
                        candidates.append((*prog, f"craft tool {name}"))

            if data.level_allows(self.level_number, "production_upgrades"):
                for name, udef in data.ALL_UPGRADES.items():
                    if udef.get("min_level", 1) > self.level_number:
                        continue
                    prog = self._prog_build(name, udef)
                    if prog:
                        candidates.append((*prog, f"build {name}"))

            for gained, ticks, actions, label in candidates:
                if ticks <= 0 or ticks > self._remaining_ticks():
                    continue
                ppt = gained / ticks
                if best is None or ppt > best[0]:
                    best = (ppt, gained, ticks, actions, label)

            if best is None:
                break
            _, gained, ticks, actions, label = best
            if self.verbose:
                print(f"[solver] {label}: +{gained:.0f} value over {ticks} ticks "
                      f"(tick {self.sim._current_tick_after_last()} -> "
                      f"{self.sim._current_tick_after_last() + ticks})")
            for act in actions:
                self.sim._process_action(len(self.actions), act)
                self.actions.append(act)

        self._liquidate()
        result = self.sim.run([])  # no-op run just to trigger the final flush
        return self.actions, result

    def _liquidate(self) -> None:
        """Spend a little remaining budget travelling to a town (if needed)
        and selling off whatever sellable inventory has piled up from
        passive trickle but was never explicitly sold by a program."""
        cur = self.sim.player.position
        town_id = cur if cur in self.level.towns else self._nearest_town_any(cur)
        if town_id is None:
            return
        travel_cost = self.d(cur, town_id) if cur != town_id else 0
        if travel_cost == math.inf or travel_cost >= self._remaining_ticks():
            return
        for act in self._travel_actions(self.path(cur, town_id)):
            if self._remaining_ticks() <= 0:
                return
            self.sim._process_action(len(self.actions), act)
            self.actions.append(act)
        town = self.level.towns[town_id]
        for item, qty in list(self.sim.player.inventory.items()):
            if qty <= 0:
                continue
            if item not in data.RESOURCES and item not in data.RECIPES:
                continue
            if item in data.RECIPES and item not in town.item_rates:
                continue
            if self._remaining_ticks() < 1:
                break
            act = {"type": "sell", "item": item, "quantity": qty}
            self.sim._process_action(len(self.actions), act)
            self.actions.append(act)
