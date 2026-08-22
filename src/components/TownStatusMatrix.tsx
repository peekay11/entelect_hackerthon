import React from 'react';
import { ALL_UPGRADES } from '../engine/gameData';
import { CheckCircle2, Circle, Trophy, Zap, Shield, Sparkles } from 'lucide-react';
import { LevelData } from '../types';

interface TownStatusMatrixProps {
  level: LevelData;
  upgradesBuilt: Record<string, string[]>;
}

export const TownStatusMatrix: React.FC<TownStatusMatrixProps> = ({
  level,
  upgradesBuilt = {}
}) => {
  const towns = Object.keys(level?.towns || {});
  const productionKeys = Object.keys(ALL_UPGRADES).filter(k => ALL_UPGRADES[k].category === 'production');
  const civicKeys = Object.keys(ALL_UPGRADES).filter(k => ALL_UPGRADES[k].category === 'civic');

  // Compute total upgrades built
  let totalBuilt = 0;
  let totalMax = Math.max(1, towns.length * 10);
  let activeTownsCount = 0;

  towns.forEach(t => {
    const count = (upgradesBuilt[t] || []).length;
    totalBuilt += count;
    if (count > 0) activeTownsCount++;
  });

  const completionPct = Math.round((totalBuilt / totalMax) * 100);
  const multiplier = activeTownsCount >= 10 ? 2.0 : 1.0 + activeTownsCount * 0.1;

  return (
    <div id="town-status-matrix" className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-6">
      {/* Header with summary stats */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h3 className="font-bold text-white text-base flex items-center gap-2">
            <Trophy className="w-5 h-5 text-amber-400" />
            Infrastructure Matrix (All 10 Towns x 10 Upgrades)
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Full regional upgrade status, production multipliers, and score multiplier tracking.
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="bg-slate-950/80 px-3.5 py-1.5 rounded-xl border border-slate-800 text-xs">
            <span className="text-slate-400">Total Upgrades: </span>
            <strong className="text-emerald-400 font-mono text-sm ml-1">
              {totalBuilt} / {totalMax} ({completionPct}%)
            </strong>
          </div>

          <div className="bg-indigo-950/40 border border-indigo-500/30 px-3.5 py-1.5 rounded-xl text-xs">
            <span className="text-indigo-300">Regional Multiplier: </span>
            <strong className="text-indigo-200 font-mono text-sm ml-1">{multiplier.toFixed(1)}x MAX</strong>
          </div>
        </div>
      </div>

      {/* Matrix Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400">
              <th className="py-2.5 px-3 font-semibold text-slate-200">Town</th>
              <th className="py-2.5 px-2 text-center font-semibold text-amber-400" colSpan={productionKeys.length}>
                Production Upgrades (Double Trickle)
              </th>
              <th className="py-2.5 px-2 text-center font-semibold text-indigo-400" colSpan={civicKeys.length}>
                Civic Upgrades (Enteloot & Upkeep)
              </th>
              <th className="py-2.5 px-3 text-right font-semibold text-slate-200">Town Total</th>
            </tr>
            <tr className="border-b border-slate-800/80 text-[10px] text-slate-400 bg-slate-950/20">
              <th className="py-2 px-3">Name</th>
              {productionKeys.map(k => (
                <th key={k} className="py-2 px-1 text-center font-medium capitalize" title={ALL_UPGRADES[k].description}>
                  {k.replace('fertilised-', 'fert-').replace('pottery-house', 'pottery')}
                </th>
              ))}
              {civicKeys.map(k => (
                <th key={k} className="py-2 px-1 text-center font-medium capitalize" title={ALL_UPGRADES[k].description}>
                  {k.replace('fire-station', 'fire-stn')}
                </th>
              ))}
              <th className="py-2 px-3 text-right">Score Pts</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {towns.map(t => {
              const builtList = upgradesBuilt[t] || [];
              const townScore = builtList.reduce((acc, u) => acc + (ALL_UPGRADES[u]?.score_value || 0), 0);
              const isTownComplete = builtList.length === 10;

              return (
                <tr
                  key={t}
                  className={`hover:bg-slate-800/30 transition-colors ${
                    isTownComplete ? 'bg-emerald-950/10' : ''
                  }`}
                >
                  <td className="py-2.5 px-3 font-bold text-slate-200 flex items-center gap-1.5">
                    {isTownComplete && <Sparkles className="w-3.5 h-3.5 text-amber-400" />}
                    {t}
                  </td>

                  {/* Production upgrades */}
                  {productionKeys.map(u => {
                    const isBuilt = builtList.includes(u);
                    return (
                      <td key={u} className="py-2.5 px-1 text-center">
                        {isBuilt ? (
                          <span className="inline-flex items-center justify-center text-emerald-400">
                            <CheckCircle2 className="w-4 h-4 fill-emerald-500/20" />
                          </span>
                        ) : (
                          <span className="inline-flex items-center justify-center text-slate-600">
                            <Circle className="w-3.5 h-3.5" />
                          </span>
                        )}
                      </td>
                    );
                  })}

                  {/* Civic upgrades */}
                  {civicKeys.map(u => {
                    const isBuilt = builtList.includes(u);
                    return (
                      <td key={u} className="py-2.5 px-1 text-center">
                        {isBuilt ? (
                          <span className="inline-flex items-center justify-center text-indigo-400">
                            <CheckCircle2 className="w-4 h-4 fill-indigo-500/20" />
                          </span>
                        ) : (
                          <span className="inline-flex items-center justify-center text-slate-600">
                            <Circle className="w-3.5 h-3.5" />
                          </span>
                        )}
                      </td>
                    );
                  })}

                  <td className="py-2.5 px-3 text-right font-mono font-bold text-amber-300">
                    {townScore.toLocaleString()} pts
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
