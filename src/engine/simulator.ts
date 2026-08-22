import { ALL_UPGRADES, COMPONENTS, RECIPES, RESOURCES } from './gameData';
import { Action, LevelData, LogEntry, SimState } from '../types';

export interface TimelineSnapshot {
  tick: number;
  player_pos: string;
  enteloot: number;
  inventory: Record<string, number>;
  upgrades_built: Record<string, string[]>;
  total_sold: number;
  sold_by_item: Record<string, number>;
  active_action: Action | null;
  action_index: number;
  action_status: string;
  score: number;
}

export class ClientSimulator {
  level: LevelData;
  actions: Action[];
  timeline: TimelineSnapshot[] = [];
  logs: LogEntry[] = [];
  finalScore: number = 0;

  constructor(level: LevelData, actions: Action[]) {
    this.level = level;
    this.actions = actions;
    this.runSimulation();
  }

  private runSimulation() {
    let tick = 0;
    const maxTicks = this.level.total_ticks;
    let playerPos = this.level.starting_town;
    let enteloot = this.level.starting_enteloot;
    const inventory: Record<string, number> = {};
    const upgradesBuilt: Record<string, string[]> = {};
    for (const t of Object.keys(this.level.towns)) {
      upgradesBuilt[t] = [];
    }
    let totalSold = 0;
    const soldByItem: Record<string, number> = {};

    // Tracking last trickle tick
    const townResourceTicks: Record<string, Record<string, number>> = {};
    const townEntelootTicks: Record<string, number> = {};
    for (const t of Object.keys(this.level.towns)) {
      townResourceTicks[t] = {};
      const prod = this.level.towns[t].trickle_production || {};
      for (const r of Object.keys(prod)) {
        townResourceTicks[t][r] = 0;
      }
      townEntelootTicks[t] = 0;
    }

    const flushTrickle = (toTick: number) => {
      for (const [tName, town] of Object.entries(this.level.towns)) {
        // Resource trickle
        const prod = town.trickle_production || {};
        for (const [res, spec] of Object.entries(prod)) {
          const last = townResourceTicks[tName]?.[res] || 0;
          if (spec.interval > 0) {
            const intervals = Math.floor(toTick / spec.interval) - Math.floor(last / spec.interval);
            if (intervals > 0) {
              const ups = upgradesBuilt[tName] || [];
              let mult = 1;
              for (const u of ups) {
                if (ALL_UPGRADES[u]?.boosts === res) {
                  mult *= 2;
                }
              }
              const gained = intervals * spec.amount * mult;
              inventory[res] = (inventory[res] || 0) + gained;
              if (!townResourceTicks[tName]) townResourceTicks[tName] = {};
              townResourceTicks[tName][res] = toTick;
            }
          }
        }

        // Enteloot trickle
        const eSpec = town.trickle_enteloot;
        if (eSpec && eSpec.interval > 0) {
          const last = townEntelootTicks[tName] || 0;
          const intervals = Math.floor(toTick / eSpec.interval) - Math.floor(last / eSpec.interval);
          if (intervals > 0) {
            const ups = upgradesBuilt[tName] || [];
            let bonusPct = 0;
            if (ups.includes('rec-center')) bonusPct += 0.20;
            if (ups.includes('school')) bonusPct += 0.50;
            if (ups.includes('library')) bonusPct += 0.50;

            const baseAmount = eSpec.amount;
            const finalAmount = Math.floor(baseAmount * (1 + bonusPct));
            enteloot += intervals * finalAmount;
            townEntelootTicks[tName] = toTick;
          }
        }
      }
    };

    const calcScore = (currentTick: number) => {
      let baseInfra = 0;
      let totalUpgrades = 0;
      const townCounts: number[] = [];
      for (const [t, ups] of Object.entries(upgradesBuilt)) {
        townCounts.push(ups.length);
        for (const u of ups) {
          baseInfra += ALL_UPGRADES[u]?.score_value || 0;
          totalUpgrades++;
        }
      }
      const activeTowns = townCounts.filter(c => c > 0).length;
      const mult = activeTowns >= 10 ? 2.0 : 1.0 + activeTowns * 0.1;
      const infraScore = baseInfra * mult;
      const entelootScore = Math.floor(enteloot * 0.1);
      return infraScore + entelootScore;
    };

    const snapshot = (action: Action | null, idx: number, status: string) => {
      this.timeline.push({
        tick,
        player_pos: playerPos,
        enteloot,
        inventory: { ...inventory },
        upgrades_built: JSON.parse(JSON.stringify(upgradesBuilt)),
        total_sold: totalSold,
        sold_by_item: { ...soldByItem },
        active_action: action,
        action_index: idx,
        action_status: status,
        score: calcScore(tick),
      });
    };

    // Initial snapshot at tick 0
    snapshot(null, -1, 'start');

    for (let i = 0; i < this.actions.length; i++) {
      if (tick >= maxTicks) break;
      const act = this.actions[i];
      const startTick = tick;
      let duration = 1;
      let status: 'ok' | 'invalid' | 'skipped_tick_limit' = 'ok';
      let detail = '';

      if (act.type === 'travel') {
        const dest = act.destination || '';
        // Find route
        const route = this.level.routes.find(
          r => (r.a === playerPos && r.b === dest) || (r.b === playerPos && r.a === dest)
        );
        if (!route) {
          status = 'invalid';
          detail = `No route between ${playerPos} and ${dest}`;
          duration = 1;
        } else if (route.toll > enteloot) {
          status = 'invalid';
          detail = `Insufficient Enteloot for toll (${route.toll})`;
          duration = 1;
        } else {
          enteloot -= route.toll;
          duration = Math.max(1, route.weight);
          playerPos = dest;
        }
      } else if (act.type === 'gather') {
        const node = this.level.nodes[playerPos];
        if (!node) {
          status = 'invalid';
          detail = `Cannot gather at non-node location ${playerPos}`;
          duration = 1;
        } else {
          duration = Math.max(1, node.gather_time);
          inventory[node.resource] = (inventory[node.resource] || 0) + node.yield;
        }
      } else if (act.type === 'craft') {
        const item = act.item || '';
        const qty = act.quantity || 1;
        const recipe = RECIPES[item] || COMPONENTS[item];
        if (!recipe) {
          status = 'invalid';
          detail = `Unknown item ${item}`;
          duration = 1;
        } else {
          // Check ingredients
          let canCraft = true;
          for (const [inp, req] of Object.entries(recipe.inputs)) {
            if ((inventory[inp] || 0) < req * qty) {
              canCraft = false;
              break;
            }
          }
          if (!canCraft) {
            status = 'invalid';
            detail = `Insufficient materials to craft ${qty}x ${item}`;
            duration = 1;
          } else {
            // Deduct
            for (const [inp, req] of Object.entries(recipe.inputs)) {
              inventory[inp] = (inventory[inp] || 0) - req * qty;
            }
            inventory[item] = (inventory[item] || 0) + qty;
            const isAffinity = this.level.towns[playerPos]?.affinities?.includes('crafting');
            const unitTime = isAffinity ? 1 : 2;
            duration = unitTime * qty;
          }
        }
      } else if (act.type === 'build') {
        const uName = act.upgrade || '';
        const uDef = ALL_UPGRADES[uName];
        const town = this.level.towns[playerPos];
        if (!town) {
          status = 'invalid';
          detail = `Must be in a town to build`;
          duration = 1;
        } else if (!uDef) {
          status = 'invalid';
          detail = `Unknown upgrade ${uName}`;
          duration = 1;
        } else if (upgradesBuilt[playerPos]?.includes(uName)) {
          status = 'invalid';
          detail = `${uName} already built in ${playerPos}`;
          duration = 1;
        } else if (enteloot < uDef.enteloot_cost) {
          status = 'invalid';
          detail = `Need ${uDef.enteloot_cost} Enteloot (have ${enteloot})`;
          duration = 1;
        } else {
          // Check components
          let hasComponents = true;
          for (const [c, req] of Object.entries(uDef.components)) {
            if ((inventory[c] || 0) < req) {
              hasComponents = false;
              break;
            }
          }
          if (!hasComponents) {
            status = 'invalid';
            detail = `Missing construction components for ${uName}`;
            duration = 1;
          } else {
            for (const [c, req] of Object.entries(uDef.components)) {
              inventory[c] = (inventory[c] || 0) - req;
            }
            enteloot -= uDef.enteloot_cost;
            if (!upgradesBuilt[playerPos]) upgradesBuilt[playerPos] = [];
            upgradesBuilt[playerPos].push(uName);
            duration = uDef.build_time;
          }
        }
      } else if (act.type === 'sell') {
        const item = act.item || '';
        const qty = act.quantity || 1;
        const town = this.level.towns[playerPos];
        if (!town) {
          status = 'invalid';
          detail = `Must be in a town to sell`;
          duration = 1;
        } else if ((inventory[item] || 0) < qty) {
          status = 'invalid';
          detail = `Insufficient ${item} to sell ${qty} (have ${inventory[item] || 0})`;
          duration = 1;
        } else {
          const rate = town.item_rates?.[item] ?? RESOURCES[item]?.sell_price ?? 0;
          inventory[item] = (inventory[item] || 0) - qty;
          enteloot += rate * qty;
          totalSold += qty;
          soldByItem[item] = (soldByItem[item] || 0) + qty;
          duration = 1;
        }
      }

      if (tick + duration > maxTicks) {
        status = 'skipped_tick_limit';
        detail = `Action duration ${duration} exceeds remaining ticks`;
        tick = maxTicks;
      } else {
        tick += duration;
      }

      flushTrickle(tick);

      this.logs.push({
        action_index: i,
        action: act,
        status,
        detail,
        start_tick: startTick,
        end_tick: tick,
        player_pos_after: playerPos,
        enteloot_after: enteloot,
        inventory_after: { ...inventory },
        upgrades_after: JSON.parse(JSON.stringify(upgradesBuilt)),
      });

      snapshot(act, i, status);
    }

    // Advance to end of ticks if any left
    if (tick < maxTicks) {
      flushTrickle(maxTicks);
      tick = maxTicks;
      snapshot(null, -1, 'complete');
    }

    this.finalScore = calcScore(maxTicks);
  }
}
