import json
import random

def generate_mock_level3():
    data = {
        "run": {
            "total_ticks": 50000,
            "starting_town": "T0",
            "starting_enteloot": 1000
        },
        "towns": {},
        "nodes": {},
        "routes": []
    }
    
    # 15 Towns
    for i in range(15):
        tname = f"T{i}"
        aff = ["crafting"] if random.random() < 0.3 else []
        data["towns"][tname] = {
            "production": { "rate": random.randint(50, 200), "resources": { "wheat": 2 } },
            "upgrades": [],
            "affinities": aff,
            "item-rates": {
                "bread": random.randint(10, 40),
                "fish-n-chips": random.randint(10, 50),
                "stew": random.randint(25, 50),
                "wooden-crafts": random.randint(10, 50),
                "furniture": random.randint(35, 65),
                "stone-works": random.randint(20, 60),
                "roof-tiles": random.randint(40, 70),
                "wool-garments": random.randint(30, 60),
                "pottery": random.randint(50, 70)
            },
            "enteloot": { "rate": random.randint(50, 200), "amount": 50 }
        }
        
    # 21 Nodes (3 Mine)
    types = ["fields", "forest", "quarry", "clay-pit", "fishing-grounds", "pasture"]
    resources = {"fields": "wheat", "forest": "wood", "quarry": "stone", "clay-pit": "clay", "fishing-grounds": "fish", "pasture": "sheep"}
    
    for i in range(21):
        nname = f"N{i}"
        if i < 3:
            ntype = "mine"
            res = "ore"
            gt = 3
        elif i - 3 < len(types):
            ntype = types[i - 3]
            res = resources[ntype]
            gt = 2
        else:
            ntype = random.choice(types)
            res = resources[ntype]
            gt = 2
            
        data["nodes"][nname] = {
            "type": ntype,
            "resource": res,
            "yield": random.randint(4, 10),
            "gather-time": gt
        }
        
    # 51 Routes (6 Fast)
    verts = list(data["towns"].keys()) + list(data["nodes"].keys())
    routes = []
    edges = set()
    
    # ensure connectivity (spanning tree)
    random.shuffle(verts)
    for i in range(1, len(verts)):
        u = verts[i-1]
        v = verts[i]
        edges.add((u, v))
        edges.add((v, u))
        routes.append({"between": [u, v], "weight": random.randint(5, 20), "toll": 0})
        
    while len(routes) < 51:
        u = random.choice(verts)
        v = random.choice(verts)
        if u != v and (u, v) not in edges:
            edges.add((u, v))
            edges.add((v, u))
            is_fast = len(routes) >= 45 # last 6 are fast
            if is_fast:
                routes.append({"between": [u, v], "weight": random.randint(1, 5), "toll": random.randint(10, 50)})
            else:
                routes.append({"between": [u, v], "weight": random.randint(5, 20), "toll": 0})
                
    data["routes"] = routes
    
    with open("level3.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Generated mock level3.json")

if __name__ == "__main__":
    generate_mock_level3()
