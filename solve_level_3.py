"""
High-Performance Solver for Level 2 Age of Enteland.
Ensures 100% valid actions, builds all upgrades across all towns,
and maximizes infrastructure score + Enteloot.
"""
from __future__ import annotations

import heapq
import json
import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Set

from enteland import data
from enteland.state import Level
from enteland.simulator import Simulator, SimResult
from enteland import scoring


class SmartLevel2Solver:
    def __init__(self, level: Level, level_number: int = 2):
        self.level = level
        self.level_number = level_number
        self.sim = Simulator(level)
        self.actions: List[dict] = []
        self.dist, self.nxt = self._build_all_pairs()

    def _build_all_pairs(self):
        verts = list(self.level.towns.keys()) + list(self.level.nodes.keys())
        graph: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for r in self.level.routes:
            # For Level 3, we allow fast routes. Tie-break against tolls.
            w = r.weight + (0.001 if r.toll > 0 else 0)
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
                    nd = du + real_w
                    if nd < d.get(v, math.inf):
                        d[v] = nd
                        prev[v] = u
                        heapq.heappush(pq, (nd, v))
            dist[src] = d
            nxt[src] = prev
        return dist, nxt

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
        """Process action in sim and record if valid, return success."""
        before_tick = self.sim._current_tick_after_last()
        self.sim._process_action(len(self.actions), act)
        entry = self.sim.log[-1]
        if entry.status == "ok":
            self.actions.append(act)
            return True
        else:
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
            is_fast = False
            std, fastr = self.level.routes_between(cur, nxt_node)
            if std is None and fastr is not None:
                is_fast = True
            elif std is not None and fastr is not None and fastr.weight < std.weight:
                is_fast = True
            
            edge_w = self.d(cur, nxt_node)
            if self._remaining_ticks() < edge_w:
                return False
            act = {"type": "travel", "destination": nxt_node}
            if is_fast:
                act["fast"] = True
            if not self._apply_action(act):
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
            if node.type == "mine" and self.level_number < 3:
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
            score = rate - 0.2 * dd
            if score > best_score:
                best, best_score = tid, score
        return best

    # ------------------------------------------------------------- Sourcing
    def obtain_resource(self, resource: str, quantity_needed: int) -> bool:
        """Gather enough of `resource`."""
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

        for _ in range(gathers):
            if self._remaining_ticks() < node.gather_time:
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
        """Ensure all components in components_dict are in inventory."""
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
            needed_enteloot = cost - self.sim.player.enteloot + 500
            if not self.make_money(needed_enteloot):
                print(f"Failed to make money {needed_enteloot} for {upgrade_name}")
                return False

        if not self.craft_components_batch(udef["components"]):
            print(f"Failed to craft components {udef['components']} for {upgrade_name}")
            return False

        if not self.travel_to(town_id):
            print(f"Failed to travel to {town_id} for {upgrade_name}")
            return False

        if self.sim.player.enteloot < cost:
            needed_enteloot = cost - self.sim.player.enteloot + 300
            if not self.make_money(needed_enteloot):
                print(f"Failed to make money 2 {needed_enteloot} for {upgrade_name}")
                return False
            if not self.travel_to(town_id):
                return False

        if self._remaining_ticks() < udef["build_time"]:
            return False
        return self._apply_action({"type": "build", "upgrade": upgrade_name})

    # ------------------------------------------------------------- Money Making
    def make_money(self, target_amount: float) -> bool:
        """Earn Enteloot by crafting and selling."""
        earned = 0.0
        while earned < target_amount and self._remaining_ticks() > 30:
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
                    if qty > 50:
                        sell_qty = qty - 20
                        town_dest = cur if cur in self.level.towns else (self._nearest_affinity_town(cur) or "Demacia")
                        if self.d(cur, town_dest) < self._remaining_ticks() - 2:
                            if self.travel_to(town_dest):
                                price = data.RESOURCES[item]["sell_price"]
                                if self._apply_action({"type": "sell", "item": item, "quantity": sell_qty}):
                                    earned += price * sell_qty

            if earned >= target_amount:
                break

            # Fast stone-works cycle
            batch = 30
            stone_needed = batch * 5
            if not self.obtain_resource("stone", stone_needed):
                break
            aff_town = "Demacia"
            if not self.travel_to(aff_town):
                break
            if not self._apply_action({"type": "craft", "item": "stone-works", "quantity": batch}):
                break
            if not self._apply_action({"type": "sell", "item": "stone-works", "quantity": batch}):
                break
            earned += batch * self.level.towns[aff_town].item_rates["stone-works"]

        return self.sim.player.enteloot >= target_amount

    def build_tools(self) -> bool:
        if self.level_number < 3:
            return True
        # Ensure we have the components for boots and pickaxe
        # boots = 2 iron-fittings, 2 rope
        # pickaxe = 2 iron-fittings, 2 planks
        needed_comps = {"iron-fittings": 4, "rope": 2, "planks": 2}
        if not self.craft_components_batch(needed_comps):
            return False
        
        # Now travel to affinity town and craft them
        aff_town = self._nearest_affinity_town(self.sim.player.position) or "Demacia"
        if not self.travel_to(aff_town):
            return False
            
        if "pickaxe" not in self.sim.player.inventory:
            self._apply_action({"type": "craft", "item": "pickaxe", "quantity": 1})
        if "boots" not in self.sim.player.inventory:
            self._apply_action({"type": "craft", "item": "boots", "quantity": 1})
        return True

    # ------------------------------------------------------------- High Level Strategy
    def solve(self) -> Tuple[List[dict], SimResult]:
        print(f"[SOLVER] Starting smart solver for level {self.level_number}, total ticks {self.level.total_ticks}...")

        # Phase 1: Build initial bank
        self.make_money(2000)

        # Phase 1.5: Build tools (Level 3+)
        self.build_tools()

        # List of all towns to develop, sorted by enteloot rate (lower is better for passive income)
        all_towns = list(self.level.towns.keys())
        all_towns.sort(key=lambda t: self.level.towns[t].enteloot_rate)

        # Phase 2: Systematic Infrastructure Development across ALL 10 towns
        prod_upgrades_order = [
            "farmhouse",
            "fertilised-fields",
            "woodlands",
            "quarry",
            "pottery-house",
            "pier",
        ]

        for town_id in all_towns:
            if self._remaining_ticks() < 250:
                print(f"[SOLVER] Low ticks remaining ({self._remaining_ticks()}), stopping upgrade loop.")
                break
            print(f"[SOLVER] Developing town: {town_id} (ticks remaining: {self._remaining_ticks()}, Enteloot: {self.sim.player.enteloot:.0f})")

            # 1. Build first 2 production upgrades
            for up in prod_upgrades_order[:2]:
                if self._remaining_ticks() < 120:
                    break
                self.build_upgrade(town_id, up)

            # 2. Build rec-center
            if self._remaining_ticks() >= 120:
                self.build_upgrade(town_id, "rec-center")

            # 3. Build fire-station
            if self._remaining_ticks() >= 120:
                self.build_upgrade(town_id, "fire-station")

            # 3.5 Build police-station (Level 3+)
            if self.level_number >= 3 and self._remaining_ticks() >= 120:
                self.build_upgrade(town_id, "police-station")

            # 4. Build school
            if self._remaining_ticks() >= 120:
                self.build_upgrade(town_id, "school")

            # 5. Build library
            if self._remaining_ticks() >= 120:
                self.build_upgrade(town_id, "library")

            # 6. Build remaining production upgrades
            for up in prod_upgrades_order[2:]:
                if self._remaining_ticks() < 120:
                    break
                self.build_upgrade(town_id, up)

        # Phase 3: Massive Endgame Grind
        print(f"[SOLVER] Upgrades complete! Starting massive endgame grind. Ticks remaining: {self._remaining_ticks()}")
        self._sync_trickle()

        best_yield_nodes = {}
        for nid, n in self.level.nodes.items():
            r = n.resource
            y = n.yield_
            if r not in best_yield_nodes or y > best_yield_nodes[r][1]:
                best_yield_nodes[r] = (nid, y)
                
        best_val = 0
        best_plan = None
        
        for rec_name, rec in data.RECIPES.items():
            if not rec.get("sellable"): continue
            g_ticks = 0
            possible = True
            req_nodes = {}
            for inp, qty in rec["inputs"].items():
                if inp not in best_yield_nodes:
                    possible = False
                    break
                nid, y = best_yield_nodes[inp]
                req_nodes[inp] = (nid, y, qty)
                g_ticks += qty / y
            if not possible: continue
            
            for tname, town in self.level.towns.items():
                price = town.item_rates.get(rec_name, 0)
                c_ticks = 1 if town.has_affinity("crafting") else 2
                val_per_tick = price / (g_ticks + c_ticks)
                if val_per_tick > best_val:
                    best_val = val_per_tick
                    best_plan = {
                        "recipe": rec_name,
                        "town": tname,
                        "nodes": req_nodes,
                        "c_ticks": c_ticks
                    }
                    
        if best_plan:
            nodes_to_visit = list(set(info[0] for info in best_plan["nodes"].values()))
            path_nodes = []
            cur = self.sim.player.position
            unvisited = list(nodes_to_visit)
            travel_ticks = 0
            while unvisited:
                nxt = min(unvisited, key=lambda n: self.d(cur, n))
                travel_ticks += self.d(cur, nxt)
                path_nodes.append(nxt)
                unvisited.remove(nxt)
                cur = nxt
                
            travel_ticks += self.d(cur, best_plan["town"])
            rem_ticks = self._remaining_ticks() - travel_ticks - 100
            
            if rem_ticks > 0:
                g_ticks_per_p = sum(info[2]/info[1] for info in best_plan["nodes"].values())
                ticks_per_p = best_plan["c_ticks"] + g_ticks_per_p
                P = int(rem_ticks / ticks_per_p)
                
                if P > 0:
                    for nid in path_nodes:
                        self.travel_to(nid)
                        for res, info in best_plan["nodes"].items():
                            if info[0] == nid:
                                qty_needed = info[2] * P
                                gathers_needed = math.ceil(qty_needed / info[1])
                                for _ in range(gathers_needed):
                                    if not self._apply_action({"type": "gather"}):
                                        break
                                        
                    self.travel_to(best_plan["town"])
                    self._apply_action({"type": "craft", "item": best_plan["recipe"], "quantity": P})
                    self._apply_action({"type": "sell", "item": best_plan["recipe"], "quantity": P})

        # Final Sell of all remaining raw resources
        
        cur = self.sim.player.position
        if cur not in self.level.towns:
            town_dest = self._nearest_affinity_town(cur) or "Demacia"
            if self.d(cur, town_dest) < self._remaining_ticks():
                self.travel_to(town_dest)

        if self.sim.player.position in self.level.towns:
            self._sync_trickle()
            for item, qty in list(self.sim.player.inventory.items()):
                if qty <= 0:
                    continue
                if item in data.RESOURCES:
                    if self._remaining_ticks() >= 1:
                        self._apply_action({"type": "sell", "item": item, "quantity": qty})

        result = self.sim.run([])
        return self.actions, result


if __name__ == "__main__":
    lvl = Level.load("level3.json", 3)
    solver = SmartLevel2Solver(lvl, 3)
    actions, result = solver.solve()
    
    print("\n=== LEVEL 3 SOLVER RESULTS ===")
    print(f"Final Tick: {result.final_tick}/{lvl.total_ticks}")
    print(f"Final Enteloot: {result.final_enteloot:.0f}")
    print(f"Total Items Sold: {result.total_sold}")
    print(f"Upgrades Built ({len(result.upgrades_built())} towns): {result.upgrades_built()}")
    score = scoring.estimate_score(result, 3)
    print(f"Estimated Infrastructure Score: {score:.0f}")
    
    rows = result.to_log_rows()
    ok_count = sum(1 for r in rows if r["status"] == "ok")
    inv_count = sum(1 for r in rows if r["status"] == "invalid")
    skip_count = sum(1 for r in rows if r["status"] == "skipped_tick_limit")
    print(f"Actions stats: {ok_count} OK, {inv_count} INVALID, {skip_count} SKIPPED")

    with open("level3_actions.txt", "w", encoding="utf-8") as f:
        json.dump({"actions": actions}, f, indent=2)
    print(f"Wrote {len(actions)} actions to level3_actions.txt")
