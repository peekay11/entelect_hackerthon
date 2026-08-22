import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from enteland.state import Level
from enteland.simulator import Simulator

LEVEL_PATH = os.path.join(os.path.dirname(__file__), "..", "examples", "worked_example_level.json")


def test_worked_example_matches_spec():
    level = Level.load(LEVEL_PATH, level_number=2)  # level 2 to allow crafting
    sim = Simulator(level)
    actions = [
        {"type": "travel", "destination": "N1"},
        {"type": "gather"},
        {"type": "gather"},
        {"type": "travel", "destination": "Demacia"},
        {"type": "craft", "item": "bread", "quantity": 4},
        {"type": "travel", "destination": "Piltover"},
        {"type": "sell", "item": "bread", "quantity": 4},
    ]
    result = sim.run(actions)

    rows = result.to_log_rows()
    expected_ticks_after = [2, 4, 6, 8, 12, 15, 16]
    for row, expected in zip(rows, expected_ticks_after):
        assert row["status"] == "ok", row
        assert row["tick_after"] == expected, (row, expected)

    assert result.final_tick == 16
    # spec: 16 ticks turn 12 gathered wheat into 160 Enteloot of *profit*
    # (starting 200 -> ends 360)
    assert result.final_enteloot == 360.0
    assert result.final_inventory.get("bread", 0) == 0
    assert result.final_inventory.get("wheat", 0) == 0
    print("Worked example replicated exactly: tick", result.final_tick,
          "Enteloot", result.final_enteloot)


def test_invalid_and_tick_limit_handling():
    level = Level.load(LEVEL_PATH, level_number=2)
    sim = Simulator(level)
    actions = [
        {"type": "travel", "destination": "Nowhere"},          # invalid: unknown destination -> 1 tick
        {"type": "sell", "item": "wheat", "quantity": 999},     # invalid: not enough wheat -> 1 tick
        {"type": "made_up_type"},                                # invalid: unknown type -> 1 tick
        {"type": "buy", "item": "wheat"},                         # invalid: missing quantity -> 1 tick
    ]
    result = sim.run(actions)
    rows = result.to_log_rows()
    assert all(r["status"] == "invalid" for r in rows)
    assert [r["ticks"] for r in rows] == [1, 1, 1, 1]
    assert result.final_tick == 4


def test_tick_cutoff():
    level = Level.load(LEVEL_PATH, level_number=2)
    level.total_ticks = 3  # artificially tiny budget
    sim = Simulator(level)
    actions = [
        {"type": "travel", "destination": "N1"},  # costs 2 ticks -> tick 2, fine
        {"type": "gather"},                        # costs 2 ticks -> would push to 4 > 3 -> skipped, clock->3
        {"type": "gather"},                        # clock already at 3 -> skipped
    ]
    result = sim.run(actions)
    rows = result.to_log_rows()
    assert rows[0]["status"] == "ok" and rows[0]["tick_after"] == 2
    assert rows[1]["status"] == "skipped_tick_limit" and rows[1]["tick_after"] == 3
    assert rows[2]["status"] == "skipped_tick_limit" and rows[2]["tick_after"] == 3
    assert result.final_tick == 3


if __name__ == "__main__":
    test_worked_example_matches_spec()
    test_invalid_and_tick_limit_handling()
    test_tick_cutoff()
    print("All tests passed.")
