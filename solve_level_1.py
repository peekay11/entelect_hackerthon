import json
import copy
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- GLOBAL CONSTANTS (PLACEHOLDERS) ---
# Please fill these in from the "Constraints" table in the full problem statement!
GLOBAL_SELL_PRICES = {
    "wheat": 2,  # From the worked example
    "sheep": 2,  
    "fish": 2,
    "stone": 2,
    "clay": 2,
    "wood": 2
}

BUY_PRICES = {
    "wheat": 1,
    "sheep": 1,
    "fish": 1,
    "stone": 1,
    "clay": 1,
    "wood": 1
}

# ---------------------------------------

@dataclass
class Node:
    name: str
    resource: str
    yield_amount: int
    gather_time: int

@dataclass
class Town:
    name: str
    produces: Dict[str, int]
    production_rate: int

@dataclass
class Route:
    destination: str
    weight: int
    toll: int

class GameSolver:
    def __init__(self, data: dict):
        self.total_ticks = data['run']['total_ticks']
        self.starting_town = data['run']['starting_town']
        self.starting_enteloot = data['run']['starting_enteloot']
        
        self.towns: Dict[str, Town] = {}
        for name, info in data['towns'].items():
            self.towns[name] = Town(
                name=name,
                produces=info['production']['resources'],
                production_rate=info['production']['rate']
            )
            
        self.nodes: Dict[str, Node] = {}
        for name, info in data['nodes'].items():
            self.nodes[name] = Node(
                name=name,
                resource=info['resource'],
                yield_amount=info['yield'],
                gather_time=info['gather-time']
            )
            
        self.graph: Dict[str, List[Route]] = {k: [] for k in list(self.towns.keys()) + list(self.nodes.keys())}
        for info in data['routes']:
            u, v = info['between']
            w = info['weight']
            toll = info['toll']
            self.graph[u].append(Route(v, w, toll))
            self.graph[v].append(Route(u, w, toll))

    def solve(self):
        # A simple greedy approach for Level 1:
        # Find the node with the best (yield * price / (gather_time + travel_time))
        # and just farm it, coming back to a town to sell before tick 1000.
        
        best_plan = []
        best_score = self.starting_enteloot
        
        print(f"Starting solver for {self.total_ticks} ticks from {self.starting_town} with {self.starting_enteloot} Enteloot...")
        
        # We will evaluate a simple loop strategy for every node:
        # 1. Travel from start to node
        # 2. Gather N times
        # 3. Travel to nearest town (or start town)
        # 4. Sell
        
        for node_name, node in self.nodes.items():
            # Find shortest path from starting town to this node
            # (Assuming graph is small, using direct edges or 1-hop)
            dist_to_node = self._shortest_path(self.starting_town, node_name)
            if dist_to_node is None:
                continue
                
            dist_to_town = self._shortest_path(node_name, self.starting_town)
            if dist_to_town is None:
                continue
                
            travel_ticks = dist_to_node + dist_to_town
            available_gather_ticks = self.total_ticks - travel_ticks
            
            if available_gather_ticks <= 0:
                continue
                
            num_gathers = available_gather_ticks // node.gather_time
            total_yield = num_gathers * node.yield_amount
            profit = total_yield * GLOBAL_SELL_PRICES.get(node.resource, 2)
            
            final_score = self.starting_enteloot + profit
            
            if final_score > best_score:
                best_score = final_score
                # Build the action list
                actions = []
                actions.append({"type": "travel", "destination": node_name})
                for _ in range(num_gathers):
                    actions.append({"type": "gather"})
                actions.append({"type": "travel", "destination": self.starting_town})
                actions.append({"type": "sell", "item": node.resource, "quantity": total_yield})
                
                best_plan = actions

        return best_plan

    def _shortest_path(self, start: str, end: str) -> int:
        # Simple BFS for shortest unweighted/weighted path
        import heapq
        queue = [(0, start)]
        visited = set()
        
        while queue:
            dist, current = heapq.heappop(queue)
            if current == end:
                return dist
            if current in visited:
                continue
            visited.add(current)
            
            for edge in self.graph[current]:
                if edge.destination not in visited:
                    heapq.heappush(queue, (dist + edge.weight, edge.destination))
        return None

if __name__ == "__main__":
    with open('/home/paseka-dev/Downloads/1.txt', 'r') as f:
        data = json.load(f)
        
    solver = GameSolver(data)
    best_actions = solver.solve()
    
    output = {"actions": best_actions}
    
    with open('/home/paseka-dev/entelect_hackerthon/level1_output.txt', 'w') as f:
        json.dump(output, f, indent=4)
        
    print(f"Generated {len(best_actions)} actions. Saved to level1_output.txt")
