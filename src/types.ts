export interface Route {
  a: string;
  b: string;
  weight: number;
  toll: number;
  fast?: boolean;
}

export interface Town {
  id: string;
  name: string;
  description?: string;
  affinities: string[];
  item_rates: Record<string, number>;
  trickle_production: Record<string, { interval: number; amount: number }>;
  trickle_enteloot: { interval: number; amount: number };
  x?: number;
  y?: number;
}

export interface NodeDef {
  id: string;
  type: string;
  resource: string;
  yield: number;
  gather_time: number;
  x?: number;
  y?: number;
}

export interface LevelData {
  level_number: number;
  total_ticks: number;
  starting_town: string;
  starting_enteloot: number;
  towns: Record<string, Town>;
  nodes: Record<string, NodeDef>;
  routes: Route[];
}

export interface Action {
  type: 'travel' | 'gather' | 'craft' | 'build' | 'sell' | 'buy' | 'upkeep';
  destination?: string;
  item?: string;
  quantity?: number;
  upgrade?: string;
  town?: string;
}

export interface LogEntry {
  action_index: number;
  action: Action;
  status: 'ok' | 'invalid' | 'skipped_tick_limit';
  detail: string;
  start_tick: number;
  end_tick: number;
  player_pos_after: string;
  enteloot_after: number;
  inventory_after: Record<string, number>;
  upgrades_after: Record<string, string[]>;
}

export interface SimState {
  current_tick: number;
  player_pos: string;
  enteloot: number;
  inventory: Record<string, number>;
  upgrades_built: Record<string, string[]>;
  total_sold: number;
  sold_by_item: Record<string, number>;
  score: number;
}
