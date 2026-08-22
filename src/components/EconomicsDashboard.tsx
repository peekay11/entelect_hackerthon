import React from 'react';
import { Coins, ShoppingCart, TrendingUp, Award, Layers, Sparkles, PieChart } from 'lucide-react';
import { TimelineSnapshot } from '../engine/simulator';
import { ALL_UPGRADES, RECIPES, RESOURCES } from '../engine/gameData';

interface EconomicsDashboardProps {
  snapshot?: TimelineSnapshot | null;
}

export const EconomicsDashboard: React.FC<EconomicsDashboardProps> = ({ snapshot }) => {
  const upgradesBuilt = snapshot?.upgrades_built || {};
  const towns = Object.keys(upgradesBuilt);
  
  let baseInfraScore = 0;
  let totalUpgrades = 0;
  let activeTowns = 0;

  towns.forEach(t => {
    const list = upgradesBuilt[t] || [];
    if (list.length > 0) activeTowns++;
    list.forEach(u => {
      baseInfraScore += ALL_UPGRADES[u]?.score_value || 0;
      totalUpgrades++;
    });
  });

  const regionalMultiplier = activeTowns >= 10 ? 2.0 : 1.0 + activeTowns * 0.1;
  const scaledInfraScore = baseInfraScore * regionalMultiplier;
  const liquidScore = Math.floor((snapshot?.enteloot ?? 0) * 0.1);
  const totalScore = scaledInfraScore + liquidScore;
  const entelootVal = snapshot?.enteloot ?? 0;
  const totalSoldVal = snapshot?.total_sold ?? 0;
  const currentTick = snapshot?.tick ?? 0;

  return (
    <div id="economics-dashboard" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total Score Card */}
      <div className="bg-gradient-to-br from-indigo-950/80 to-slate-900/90 rounded-2xl border border-indigo-500/30 p-5 shadow-xl flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-indigo-300">Infrastructure Score</span>
          <Award className="w-5 h-5 text-amber-400" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-black text-white font-mono tracking-tight">
            {totalScore.toLocaleString()}
          </div>
          <p className="text-[11px] text-indigo-300/80 mt-1">
            {scaledInfraScore.toLocaleString()} (Infra) + {liquidScore.toLocaleString()} (Loot)
          </p>
        </div>
        <div className="text-[10px] text-slate-400 pt-2 border-t border-indigo-500/20 flex justify-between">
          <span>Regional Multiplier:</span>
          <strong className="text-amber-300">{regionalMultiplier.toFixed(1)}x (10 Towns)</strong>
        </div>
      </div>

      {/* Enteloot Balance Card */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400">Enteloot Reserve</span>
          <Coins className="w-5 h-5 text-amber-400" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-black text-amber-300 font-mono tracking-tight">
            {entelootVal.toLocaleString()} 🪙
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Liquid coin reserve at tick {currentTick}
          </p>
        </div>
        <div className="text-[10px] text-slate-400 pt-2 border-t border-slate-800 flex justify-between">
          <span>Active Town Boosts:</span>
          <strong className="text-emerald-400">+120% Trickle Yield</strong>
        </div>
      </div>

      {/* Upgrades Built Card */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400">Total Upgrades Built</span>
          <Layers className="w-5 h-5 text-purple-400" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-black text-purple-300 font-mono tracking-tight">
            {totalUpgrades} / 100
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {Math.round((totalUpgrades / 100) * 100)}% Global Construction
          </p>
        </div>
        <div className="text-[10px] text-slate-400 pt-2 border-t border-slate-800 flex justify-between">
          <span>Base Value:</span>
          <strong className="text-slate-300">{baseInfraScore.toLocaleString()} pts</strong>
        </div>
      </div>

      {/* Total Items Sold Card */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400">Trade Volume</span>
          <ShoppingCart className="w-5 h-5 text-emerald-400" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-black text-emerald-300 font-mono tracking-tight">
            {totalSoldVal.toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Total crafted & raw goods sold
          </p>
        </div>
        <div className="text-[10px] text-slate-400 pt-2 border-t border-slate-800 flex justify-between">
          <span>Top Seller:</span>
          <strong className="text-emerald-300">Stone-works & Stew</strong>
        </div>
      </div>
    </div>
  );
};
