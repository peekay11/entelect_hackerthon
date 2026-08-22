"""
High-Performance Solver for Level 4 Age of Enteland.
Handles:
- Upkeep mechanic (Level 4 unlock: 5 ticks -> 2x Enteloot trickle for 50/75 ticks)
- Fast routes with tolls
- Mine nodes & Ore gathering
- Permanent Tools (boots: travel -1, pickaxe: gather -1)
- 30 Towns full civic & production upgrade infrastructure (Maximizing multiplier & score)
- Bulk component crafting & resource routing
- Late-game liquidation & high-margin trade loops
"""
from __future__ import annotations

import heapq
import json
import math
import os
import zipfile
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Set

from enteland import data
from enteland.state import Level
from enteland.simulator import Simulator, SimResult
from enteland import scoring


class Level4Solver:
    def __init__(self, level: Level, verbose: bool = True):
        self.level = level
        self.level_number = 4
        self.verbose = verbose
        self.sim = Simulator(level)
        self.actions: List[dict] = []
        self._build_graph()

    def _build_graph(self):
        verts = list(self.level.towns.keys()) + list(self.level.nodes.keys())
        graph: Dict[str, List[Tuple[str, float, int, int]]] = defaultdict(list)
        for r in self.level.routes:
            # Prefer fast routes if available, slightly penalize toll to avoid bankrupting early
            w = r.weight + (0.01 if r.toll > 0 else 0)
            graph[r.a].append((r.b, w, r.weight, r.toll))
            graph[r.b].append((r.a, w, r.weight, r.toll))

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
                for v, penalty_w, real_w, toll in graph.get(u, []):
                    # effective weight with boots if active
                    eff_w = real_w
                    if "boots" in self.sim.player.tools:
                        eff_w = max(1, eff_w - 1)
                    nd = du + eff_w
                    if nd < d.get(v, math.inf):
                        d[v] = nd
                        prev[v] = u
                        heapq.heappush(pq, (nd, v))
            dist[src] = d
            nxt[src] = prev
        self.dist = dist
        self.nxt = nxt

    def d(self, a: str, b: str) -> float:
        return self.dist.get(a, {}).get(b, math.inf)

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

    def _apply_action(self, act: dict) -> bool:
        before_tick = self.sim._current_tick_after_last()
        self.sim._process_action(len(self.actions), act)
        entry = self.sim.log[-1]
        if entry.status == "ok":
            self.actions.append(act)
            return True
        else:
            if self.verbose:
                print(f"[WARN] Action {act} failed: {entry.status} ({entry.detail}) at tick {before_tick}")
            return False

    def travel_to(self, dest: str) -> bool:
        cur = self.sim.player.position
        if cur == dest:
            return True
        p = self.path(cur, dest)
        if not p:
            return False
        for nxt_node in p[1:]:
            std, fastr = self.level.routes_between(cur, nxt_node)
            is_fast = False
            if fastr is not None:
                if std is None:
                    is_fast = True
                elif fastr.weight < std.weight and self.sim.player.enteloot >= fastr.toll:
                    is_fast = True

            edge_w = fastr.weight if is_fast else (std.weight if std else 1)
            if "boots" in self.sim.player.tools:
                edge_w = max(1, edge_w - 1)

            if self._remaining_ticks() < edge_w:
                return False

            act = {"type": "travel", "destination": nxt_node}
            if is_fast:
                act["fast"] = True
            if not self._apply_action(act):
                # Fallback to standard if fast failed
                if is_fast and std is not None:
                    act_std = {"type": "travel", "destination": nxt_node}
                    if not self._apply_action(act_std):
                        return False
                else:
                    return False
            cur = nxt_node
        return True

    def _remaining_ticks(self) -> int:
        return self.level.total_ticks - self.sim._current_tick_after_last()

    def _sync_trickle(self):
        cur_tick = self.sim._current_tick_after_last()
        self.sim._flush_all(cur_tick)

    # ------------------------------------------------------------- Resource Helpers
    def _nearest_node_for(self, resource: str, frm: str) -> Optional[str]:
        best, best_d = None, math.inf
        for nid, node in self.level.nodes.items():
            if node.resource != resource:
                continue
            dd = self.d(frm, nid)
            if dd < best_d:
                best, best_d = nid, dd
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

    def _best_sell_town(self, good: str, frm: str) -> Optional[str]:
        best, best_score = None, -math.inf
        for tid, town in self.level.towns.items():
            rate = town.item_rates.get(good)
            if rate is None:
                continue
            dd = self.d(frm, tid)
            if dd == math.inf:
                continue
            score = rate - 0.1 * dd
            if score > best_score:
                best, best_score = tid, score
        return best

    # ------------------------------------------------------------- Sourcing
    def obtain_resource(self, resource: str, quantity_needed: int) -> bool:
        self._sync_trickle()
        have = self.sim.player.inventory.get(resource, 0)
        needed = quantity_needed - have
        if needed <= 0:
            return True

        cur = self.sim.player.position
        node_id = self._nearest_node_for(resource, cur)
        if not node_id:
            return False
        node = self.level.nodes[node_id]
        gathers = math.ceil(needed / node.yield_)

        if not self.travel_to(node_id):
            return False

        gtime = node.gather_time
        if "pickaxe" in self.sim.player.tools:
            gtime = max(1, gtime - 1)

        for _ in range(gathers):
            if self._remaining_ticks() < gtime:
                return False
            if not self._apply_action({"type": "gather"}):
                return False
        return True

    # ------------------------------------------------------------- Component Crafting
    def _expand_components(self, top_components: Dict[str, int]) -> Tuple[Dict[str, int], Dict[str, int]]:
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

        for name, qty in top_components.items():
            visit(name, qty)
        return leaf_needs, comp_needs

    def _toposort_components(self, comp_needs: Dict[str, int]) -> List[str]:
        remaining = dict(comp_needs)
        ordered = []
        while remaining:
            ready = [c for c in remaining if all(inp not in remaining for inp in data.COMPONENTS[c]["inputs"])]
            if not ready:
                ready = list(remaining.keys())
            for c in ready:
                ordered.append(c)
                del remaining[c]
        return ordered

    def craft_components_batch(self, components_dict: Dict[str, int]) -> bool:
        self._sync_trickle()
        needed_top = {}
        for c, q in components_dict.items():
            cur_q = self.sim.player.inventory.get(c, 0)
            if cur_q < q:
                needed_top[c] = q - cur_q

        if not needed_top:
            return True

        leaf_needs, comp_needs = self._expand_components(needed_top)

        # Gather all leaf resources
        for res, qty in leaf_needs.items():
            if not self.obtain_resource(res, qty):
                return False

        # Travel to nearest affinity town
        cur = self.sim.player.position
        aff_town = self._nearest_affinity_town(cur) or "Demacia"
        if not self.travel_to(aff_town):
            return False

        # Craft in topological order
        order = self._toposort_components(comp_needs)
        for comp_name in order:
            qty_to_craft = comp_needs[comp_name]
            if qty_to_craft <= 0:
                continue
            if self._remaining_ticks() < qty_to_craft:
                return False
            if not self._apply_action({"type": "craft", "item": comp_name, "quantity": qty_to_craft}):
                return False
        return True

    # ------------------------------------------------------------- Tools (Level 3+)
    def craft_tools(self) -> bool:
        needed_comps = {"iron-fittings": 4, "rope": 2, "planks": 2}
        if not self.craft_components_batch(needed_comps):
            return False

        aff_town = self._nearest_affinity_town(self.sim.player.position) or "Demacia"
        if not self.travel_to(aff_town):
            return False

        if "pickaxe" not in self.sim.player.tools:
            self._apply_action({"type": "craft", "item": "pickaxe", "quantity": 1})
        if "boots" not in self.sim.player.tools:
            self._apply_action({"type": "craft", "item": "boots", "quantity": 1})

        # Re-build graph with boots travel discount
        self._build_graph()
        return True

    # ------------------------------------------------------------- Building
    def build_upgrade(self, town_id: str, upgrade_name: str) -> bool:
        udef = data.ALL_UPGRADES[upgrade_name]
        self._sync_trickle()

        town = self.level.towns[town_id]
        if upgrade_name in town.upgrades:
            return True

        prereq = udef.get("prerequisite")
        if prereq:
            if prereq["type"] == "any_production_upgrades":
                have = sum(1 for n in town.upgrades if n in data.PRODUCTION_UPGRADES)
                if have < prereq["count"]:
                    return False
            elif prereq["type"] == "specific_upgrade":
                if prereq["upgrade"] not in town.upgrades:
                    return False

        cost = udef["enteloot_cost"]
        if self.sim.player.enteloot < cost:
            needed_enteloot = cost - self.sim.player.enteloot + 1000
            if not self.make_money(needed_enteloot):
                return False

        if not self.craft_components_batch(udef["components"]):
            return False

        if not self.travel_to(town_id):
            return False

        if self.sim.player.enteloot < cost:
            needed_enteloot = cost - self.sim.player.enteloot + 500
            if not self.make_money(needed_enteloot):
                return False
            if not self.travel_to(town_id):
                return False

        if self._remaining_ticks() < udef["build_time"]:
            return False
        return self._apply_action({"type": "build", "upgrade": upgrade_name})

    # ------------------------------------------------------------- Upkeep (Level 4 unlock)
    def trigger_upkeep(self, town_id: str) -> bool:
        if self.sim.player.position != town_id:
            if not self.travel_to(town_id):
                return False
        if self._remaining_ticks() < data.UPKEEP_ACTION_TICKS:
            return False
        return self._apply_action({"type": "upkeep"})

    # ------------------------------------------------------------- Money Making
    def make_money(self, target_amount: float) -> bool:
        earned = 0.0
        while earned < target_amount and self._remaining_ticks() > 50:
            self._sync_trickle()
            cur = self.sim.player.position

            # Sell existing recipes/resources
            for item, qty in list(self.sim.player.inventory.items()):
                if qty <= 0:
                    continue
                if item in data.RECIPES:
                    best_town = self._best_sell_town(item, cur)
                    if best_town and self.d(cur, best_town) < self._remaining_ticks() - 2:
                        if self.travel_to(best_town):
                            rate = self.level.towns[best_town].item_rates[item]
                            if self._apply_action({"type": "sell", "item": item, "quantity": qty}):
                                earned += rate * qty
                elif item in data.RESOURCES:
                    if qty > 40:
                        sell_qty = qty - 10
                        town_dest = cur if cur in self.level.towns else (self._nearest_affinity_town(cur) or "Demacia")
                        if self.d(cur, town_dest) < self._remaining_ticks() - 2:
                            if self.travel_to(town_dest):
                                price = data.RESOURCES[item]["sell_price"]
                                if self._apply_action({"type": "sell", "item": item, "quantity": sell_qty}):
                                    earned += price * sell_qty

            if earned >= target_amount:
                break

            # Fast high-yield recipe cycle: pottery (4 clay, 1 wood) or stone-works (5 stone)
            batch = 40
            clay_needed = batch * 4
            wood_needed = batch * 1
            if not self.obtain_resource("clay", clay_needed):
                break
            if not self.obtain_resource("wood", wood_needed):
                break
            aff_town = self._nearest_affinity_town(self.sim.player.position) or "Demacia"
            if not self.travel_to(aff_town):
                break
            if not self._apply_action({"type": "craft", "item": "pottery", "quantity": batch}):
                break
            best_t = self._best_sell_town("pottery", aff_town) or aff_town
            if not self.travel_to(best_t):
                break
            rate = self.level.towns[best_t].item_rates.get("pottery", 60)
            if not self._apply_action({"type": "sell", "item": "pottery", "quantity": batch}):
                break
            earned += batch * rate

        return self.sim.player.enteloot >= target_amount

    # ------------------------------------------------------------- High-Level Solver
    def solve(self) -> Tuple[List[dict], SimResult]:
        print(f"[SOLVER L4] Starting solver for Level 4 (Total ticks: {self.level.total_ticks})...")

        # Step 1: Initial cash buffer
        self.make_money(5000)

        # Step 2: Craft Boots & Pickaxe early to permanently reduce travel & gather costs!
        print("[SOLVER L4] Crafting Tools (Boots & Pickaxe)...")
        self.craft_tools()

        # Step 3: Upgrade ALL 30 Towns systematically
        # Order towns by distance from starting position
        all_towns = list(self.level.towns.keys())
        all_towns.sort(key=lambda t: self.d(self.level.starting_town, t))

        prod_upgrades = [
            "farmhouse",
            "fertilised-fields",
            "woodlands",
            "quarry",
            "pottery-house",
            "pier",
        ]

        print(f"[SOLVER L4] Beginning full infrastructure deployment across {len(all_towns)} towns...")
        for town_id in all_towns:
            if self._remaining_ticks() < 500:
                print(f"[SOLVER L4] Low ticks remaining ({self._remaining_ticks()}), stopping town upgrades.")
                break

            print(f"[SOLVER L4] Upgrading town: {town_id} (Tick: {self.sim._current_tick_after_last()}, Enteloot: {self.sim.player.enteloot:.0f})")

            # 1. Build first 2 production upgrades (fulfills civic prereqs)
            for up in prod_upgrades[:2]:
                if self._remaining_ticks() < 200:
                    break
                self.build_upgrade(town_id, up)

            # 2. Build rec-center (req 1 prod)
            if self._remaining_ticks() >= 200:
                self.build_upgrade(town_id, "rec-center")

            # 3. Build fire-station (req 2 prod) -> lengthens upkeep to 75 ticks!
            if self._remaining_ticks() >= 200:
                self.build_upgrade(town_id, "fire-station")

            # 4. Build police-station (req fire-station) -> decreases rate by -2 ticks!
            if self._remaining_ticks() >= 200:
                self.build_upgrade(town_id, "police-station")

            # 5. Build school (req rec-center)
            if self._remaining_ticks() >= 200:
                self.build_upgrade(town_id, "school")

            # 6. Build library (req school)
            if self._remaining_ticks() >= 200:
                self.build_upgrade(town_id, "library")

            # 7. Build remaining 4 production upgrades
            for up in prod_upgrades[2:]:
                if self._remaining_ticks() < 200:
                    break
                self.build_upgrade(town_id, up)

            # 8. Trigger Upkeep on this town to multiply its boosted Enteloot production
            if self._remaining_ticks() >= 50:
                self.trigger_upkeep(town_id)

        print(f"[SOLVER L4] Infrastructure phase complete! Ticks remaining: {self._remaining_ticks()}")

        # Step 4: Late-game high-volume manufacturing and trading loop
        # We have tens of thousands of ticks remaining. We repeatedly harvest, craft high-yield items, and upkeep key towns!
        craft_order = [
            ("pottery", {"clay": 4, "wood": 1}, 50),
            ("roof-tiles", {"clay": 3, "stone": 2}, 50),
            ("furniture", {"wood": 3, "sheep": 1}, 50),
            ("stone-works", {"stone": 5}, 50),
        ]

        affinity_towns = [tid for tid, t in self.level.towns.items() if t.has_affinity("crafting")]

        while self._remaining_ticks() > 200:
            cur = self.sim.player.position

            # Periodically boost nearest town with upkeep if active window passed
            if cur in self.level.towns:
                rt = self.sim.town_rt[cur]
                if not self.sim._is_upkeep_active_at(rt, self.sim._current_tick_after_last()):
                    self.trigger_upkeep(cur)

            # Pick high-value craft
            chosen_good, inputs, batch_size = craft_order[len(self.actions) % len(craft_order)]

            # Sourcing inputs
            ok = True
            for res, qty_per in inputs.items():
                if not self.obtain_resource(res, qty_per * batch_size):
                    ok = False
                    break
            if not ok:
                break

            aff_t = self._nearest_affinity_town(self.sim.player.position) or "Demacia"
            if not self.travel_to(aff_t):
                break

            if not self._apply_action({"type": "craft", "item": chosen_good, "quantity": batch_size}):
                break

            sell_t = self._best_sell_town(chosen_good, aff_t) or aff_t
            if not self.travel_to(sell_t):
                break

            if not self._apply_action({"type": "sell", "item": chosen_good, "quantity": batch_size}):
                break

        # Step 5: Final inventory liquidation
        print("[SOLVER L4] Final inventory liquidation...")
        self._sync_trickle()
        cur = self.sim.player.position
        if cur not in self.level.towns:
            town_dest = self._nearest_affinity_town(cur) or "Demacia"
            if self.d(cur, town_dest) < self._remaining_ticks():
                self.travel_to(town_dest)

        if self.sim.player.position in self.level.towns:
            self._sync_trickle()
            for item, qty in list(self.sim.player.inventory.items()):
                if qty > 0 and item in data.RESOURCES and self._remaining_ticks() >= 1:
                    self._apply_action({"type": "sell", "item": item, "quantity": qty})

        result = self.sim.run([])
        return self.actions, result


def create_submission_zip():
    zip_filename = "submission_level4.zip"
    files_to_pack = [
        "solve_level_4.py",
        "level4_actions.txt",
        "enteland/__init__.py",
        "enteland/data.py",
        "enteland/scoring.py",
        "enteland/simulator.py",
        "enteland/state.py",
        "data/resources.json",
        "level4.json",
    ]
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in files_to_pack:
            if os.path.exists(f):
                zipf.write(f, arcname=f)
    print(f"Created {zip_filename} successfully!")


if __name__ == "__main__":
    lvl = Level.load("level4.json", 4)
    solver = Level4Solver(lvl, verbose=True)
    actions, result = solver.solve()

    print("\n=======================================================")
    print("           AGE OF ENTELAND — LEVEL 4 RESULTS           ")
    print("=======================================================")
    print(f"Final Tick: {result.final_tick} / {lvl.total_ticks}")
    print(f"Final Enteloot: {result.final_enteloot:,.0f} 🪙")
    print(f"Total Items Sold: {result.total_sold}")
    upgrades_by_town = result.upgrades_built()
    print(f"Towns with Upgrades: {len(upgrades_by_town)} / {len(lvl.towns)}")
    
    total_upgrades = sum(len(ups) for ups in upgrades_by_town.values())
    print(f"Total Upgrades Constructed: {total_upgrades} (Max possible: {len(lvl.towns)*11} = 330)")

    score = scoring.estimate_score(result, 4)
    print(f"Estimated Infrastructure & Overall Score: {score:,.0f} pts")

    rows = result.to_log_rows()
    ok_count = sum(1 for r in rows if r["status"] == "ok")
    inv_count = sum(1 for r in rows if r["status"] == "invalid")
    skip_count = sum(1 for r in rows if r["status"] == "skipped_tick_limit")
    print(f"Action Log Stats: {ok_count} OK, {inv_count} INVALID, {skip_count} SKIPPED")

    with open("level4_actions.txt", "w", encoding="utf-8") as f:
        json.dump({"actions": actions}, f, indent=2)
    print(f"Saved {len(actions)} actions to level4_actions.txt")

    create_submission_zip()
