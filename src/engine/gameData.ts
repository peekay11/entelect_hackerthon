export const LEVEL_UNLOCKS: Record<string, string[]> = {
  "1": ["travel", "buy", "sell", "gather"],
  "2": ["craft", "build", "recipes", "construction_components", "production_upgrades", "civic_upgrades"],
  "3": ["fast_routes", "mine_nodes", "ore", "iron-fittings", "tools", "police-station"],
  "4": ["upkeep"],
};

export const NODE_TYPES: Record<string, { resource: string; gather_time: number; min_level?: number }> = {
  fields: { resource: "wheat", gather_time: 2 },
  forest: { resource: "wood", gather_time: 2 },
  quarry: { resource: "stone", gather_time: 2 },
  "clay-pit": { resource: "clay", gather_time: 2 },
  "fishing-grounds": { resource: "fish", gather_time: 2 },
  pasture: { resource: "sheep", gather_time: 2 },
  mine: { resource: "ore", gather_time: 3, min_level: 3 },
};

export const TOOLS: Record<string, { inputs: Record<string, number>; once_per_run: boolean; min_level: number; effect: { type: string; value: number; min?: number } }> = {
  boots: { inputs: { "iron-fittings": 2, rope: 2 }, once_per_run: true, min_level: 3, effect: { type: "travel_time_delta", value: -1, min: 1 } },
  pickaxe: { inputs: { "iron-fittings": 2, planks: 2 }, once_per_run: true, min_level: 3, effect: { type: "gather_time_delta", value: -1, min: 1 } },
};
export const CONSTANTS = {
  craft_time_base: 2,
  craft_time_affinity: 1,
  invalid_action_ticks: 1,
  upkeep_action_ticks: 5,
  upkeep_boost_multiplier: 2,
  upkeep_boost_duration_ticks: 50,
  sell_bonus_multiplier: 1.5,
  rounding: "floor",
  min_travel_ticks: 1,
  min_gather_ticks: 1,
};

export const RESOURCES: Record<string, { sell_price: number; buy_price: number | null }> = {
  wheat: { sell_price: 2, buy_price: 4 },
  wood: { sell_price: 3, buy_price: 5 },
  stone: { sell_price: 3, buy_price: 5 },
  clay: { sell_price: 4, buy_price: 6 },
  fish: { sell_price: 4, buy_price: 6 },
  sheep: { sell_price: 5, buy_price: 8 },
  ore: { sell_price: 6, buy_price: null },
};

export const RECIPES: Record<string, { inputs: Record<string, number>; craft_time: number; sellable: boolean }> = {
  bread: { inputs: { wheat: 3 }, craft_time: 2, sellable: true },
  "fish-n-chips": { inputs: { fish: 2, wheat: 1 }, craft_time: 2, sellable: true },
  stew: { inputs: { sheep: 1, fish: 1, wheat: 1 }, craft_time: 2, sellable: true },
  "wooden-crafts": { inputs: { wood: 4 }, craft_time: 2, sellable: true },
  furniture: { inputs: { wood: 3, sheep: 1 }, craft_time: 2, sellable: true },
  "stone-works": { inputs: { stone: 5 }, craft_time: 2, sellable: true },
  "roof-tiles": { inputs: { clay: 3, stone: 2 }, craft_time: 2, sellable: true },
  "wool-garments": { inputs: { sheep: 3 }, craft_time: 2, sellable: true },
  pottery: { inputs: { clay: 4, wood: 1 }, craft_time: 2, sellable: true },
};

export const COMPONENTS: Record<string, { inputs: Record<string, number>; craft_time: number; sellable: boolean }> = {
  planks: { inputs: { wood: 2 }, craft_time: 2, sellable: false },
  thatch: { inputs: { wheat: 2 }, craft_time: 2, sellable: false },
  "stone-blocks": { inputs: { stone: 3 }, craft_time: 2, sellable: false },
  mortar: { inputs: { clay: 1, stone: 1 }, craft_time: 2, sellable: false },
  bricks: { inputs: { clay: 2, mortar: 1 }, craft_time: 2, sellable: false },
  rope: { inputs: { sheep: 2 }, craft_time: 2, sellable: false },
  fencing: { inputs: { wood: 2, rope: 1 }, craft_time: 2, sellable: false },
  "kiln-glass": { inputs: { clay: 2, wood: 2 }, craft_time: 2, sellable: false },
  nets: { inputs: { rope: 1, fencing: 1 }, craft_time: 2, sellable: false },
  "iron-fittings": { inputs: { ore: 2, wood: 1 }, craft_time: 2, sellable: false },
};

export const ALL_UPGRADES: Record<string, {
  category: 'production' | 'civic';
  boosts?: string;
  components: Record<string, number>;
  enteloot_cost: number;
  build_time: number;
  score_value: number;
  prerequisite: { type: string; count?: number; upgrade?: string } | null;
  description: string;
}> = {
  farmhouse: {
    category: 'production',
    boosts: 'sheep',
    components: { planks: 3, thatch: 2 },
    enteloot_cost: 500,
    build_time: 3,
    score_value: 1000,
    prerequisite: null,
    description: 'Doubles passive sheep trickle generation'
  },
  pier: {
    category: 'production',
    boosts: 'fish',
    components: { planks: 4, nets: 2 },
    enteloot_cost: 600,
    build_time: 3,
    score_value: 1000,
    prerequisite: null,
    description: 'Doubles passive fish trickle generation'
  },
  "fertilised-fields": {
    category: 'production',
    boosts: 'wheat',
    components: { fencing: 2, thatch: 2 },
    enteloot_cost: 500,
    build_time: 3,
    score_value: 1000,
    prerequisite: null,
    description: 'Doubles passive wheat trickle generation'
  },
  quarry: {
    category: 'production',
    boosts: 'stone',
    components: { "stone-blocks": 3, planks: 2 },
    enteloot_cost: 600,
    build_time: 3,
    score_value: 1000,
    prerequisite: null,
    description: 'Doubles passive stone trickle generation'
  },
  woodlands: {
    category: 'production',
    boosts: 'wood',
    components: { fencing: 2, rope: 2 },
    enteloot_cost: 500,
    build_time: 3,
    score_value: 1000,
    prerequisite: null,
    description: 'Doubles passive wood trickle generation'
  },
  "pottery-house": {
    category: 'production',
    boosts: 'clay',
    components: { bricks: 4, planks: 2 },
    enteloot_cost: 700,
    build_time: 3,
    score_value: 1000,
    prerequisite: null,
    description: 'Doubles passive clay trickle generation'
  },
  "rec-center": {
    category: 'civic',
    components: { planks: 4, bricks: 3, rope: 1 },
    enteloot_cost: 1200,
    build_time: 4,
    score_value: 3000,
    prerequisite: { type: 'any_production_upgrades', count: 1 },
    description: '+20% passive Enteloot trickle amount'
  },
  "fire-station": {
    category: 'civic',
    components: { bricks: 5, "stone-blocks": 3, rope: 2 },
    enteloot_cost: 1800,
    build_time: 4,
    score_value: 4000,
    prerequisite: { type: 'any_production_upgrades', count: 2 },
    description: '+50% upkeep boost duration'
  },
  school: {
    category: 'civic',
    components: { bricks: 6, planks: 3, "kiln-glass": 2 },
    enteloot_cost: 2000,
    build_time: 5,
    score_value: 5000,
    prerequisite: { type: 'specific_upgrade', upgrade: 'rec-center' },
    description: '+50% passive Enteloot trickle amount'
  },
  library: {
    category: 'civic',
    components: { bricks: 5, planks: 5, "kiln-glass": 2 },
    enteloot_cost: 2500,
    build_time: 5,
    score_value: 6000,
    prerequisite: { type: 'specific_upgrade', upgrade: 'school' },
    description: '+50% passive Enteloot trickle amount'
  }
};
