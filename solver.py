import json
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class TownProduction:
    rate: int
    resources: Dict[str, int]

@dataclass
class EntelootInfo:
    rate: int
    amount: int

@dataclass
class Town:
    name: str
    production: TownProduction
    upgrades: List[str]
    affinities: List[str]
    item_rates: Dict[str, int]
    enteloot: EntelootInfo

@dataclass
class Node:
    name: str
    type: str
    resource: str
    yield_amount: int
    gather_time: int

@dataclass
class Route:
    between: List[str]
    weight: int
    toll: int

class GameState:
    def __init__(self, data: dict):
        self.total_ticks = data['run']['total_ticks']
        self.starting_town = data['run']['starting_town']
        self.starting_enteloot = data['run']['starting_enteloot']
        
        self.towns: Dict[str, Town] = {}
        for name, info in data['towns'].items():
            self.towns[name] = Town(
                name=name,
                production=TownProduction(**info['production']),
                upgrades=info['upgrades'],
                affinities=info['affinities'],
                item_rates=info['item-rates'],
                enteloot=EntelootInfo(**info['enteloot'])
            )
            
        self.nodes: Dict[str, Node] = {}
        for name, info in data['nodes'].items():
            self.nodes[name] = Node(
                name=name,
                type=info['type'],
                resource=info['resource'],
                yield_amount=info['yield'],
                gather_time=info['gather-time']
            )
            
        self.routes: List[Route] = []
        for info in data['routes']:
            self.routes.append(Route(
                between=info['between'],
                weight=info['weight'],
                toll=info['toll']
            ))

    def print_summary(self):
        print(f"Total Ticks: {self.total_ticks}")
        print(f"Starting Town: {self.starting_town}")
        print(f"Starting Enteloot: {self.starting_enteloot}")
        print(f"Loaded {len(self.towns)} towns, {len(self.nodes)} nodes, and {len(self.routes)} routes.")

if __name__ == "__main__":
    with open('/home/paseka-dev/Downloads/1.txt', 'r') as f:
        data = json.load(f)
    game = GameState(data)
    game.print_summary()
