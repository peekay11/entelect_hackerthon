import React, { useState, useMemo } from 'react';
import { LevelData, NodeDef, Town } from '../types';
import { ALL_UPGRADES, RESOURCES } from '../engine/gameData';
import { 
  Building2, 
  Trees, 
  Hammer, 
  Fish, 
  Wheat, 
  Coins, 
  MapPin, 
  Sparkles,
  Info,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';

interface MapVisualizerProps {
  level: LevelData;
  playerPos: string;
  upgradesBuilt: Record<string, string[]>;
  currentTick: number;
}

// Fixed optimal graph layout coordinates (width: 900, height: 600)
const TOWN_COORDS: Record<string, { x: number; y: number }> = {
  Demacia: { x: 180, y: 140 },
  Noxus: { x: 720, y: 150 },
  Piltover: { x: 380, y: 220 },
  Zaun: { x: 420, y: 310 },
  Ionia: { x: 800, y: 320 },
  Shurima: { x: 260, y: 370 },
  Freljord: { x: 450, y: 80 },
  Bilgewater: { x: 740, y: 480 },
  Targon: { x: 130, y: 490 },
  Ixtal: { x: 460, y: 490 },
};

const NODE_COORDS: Record<string, { x: number; y: number }> = {
  N0: { x: 90, y: 240 },
  N1: { x: 260, y: 70 },
  N2: { x: 280, y: 250 },
  N3: { x: 600, y: 90 },
  N4: { x: 570, y: 210 },
  N5: { x: 660, y: 260 },
  N6: { x: 830, y: 200 },
  N7: { x: 170, y: 390 },
  N8: { x: 340, y: 470 },
  N9: { x: 580, y: 430 },
  N10: { x: 670, y: 380 },
  N11: { x: 830, y: 430 },
  N12: { x: 370, y: 390 },
  N13: { x: 500, y: 280 },
  // Fallbacks for worked examples or generic nodes
  A: { x: 150, y: 300 },
  B: { x: 350, y: 300 },
  C: { x: 550, y: 300 },
  D: { x: 750, y: 300 },
};

export const MapVisualizer: React.FC<MapVisualizerProps> = ({
  level,
  playerPos,
  upgradesBuilt,
  currentTick
}) => {
  const [selectedEntity, setSelectedEntity] = useState<{ type: 'town' | 'node'; id: string } | null>(null);

  // Compute coordinate map for all towns and nodes
  const nodePositions = useMemo(() => {
    const coords: Record<string, { x: number; y: number }> = {};
    const towns = Object.keys(level.towns);
    const nodes = Object.keys(level.nodes);

    towns.forEach((t, i) => {
      coords[t] = TOWN_COORDS[t] || {
        x: 150 + (i % 4) * 200,
        y: 120 + Math.floor(i / 4) * 160
      };
    });

    nodes.forEach((n, i) => {
      coords[n] = NODE_COORDS[n] || {
        x: 100 + (i % 5) * 160,
        y: 180 + Math.floor(i / 5) * 140
      };
    });

    return coords;
  }, [level]);

  const playerCoord = nodePositions[playerPos] || { x: 450, y: 300 };

  const getNodeIcon = (resType: string) => {
    switch (resType) {
      case 'wheat': return <Wheat className="w-3.5 h-3.5 text-amber-300" />;
      case 'wood': return <Trees className="w-3.5 h-3.5 text-emerald-400" />;
      case 'stone': return <Hammer className="w-3.5 h-3.5 text-slate-300" />;
      case 'clay': return <Building2 className="w-3.5 h-3.5 text-orange-400" />;
      case 'fish': return <Fish className="w-3.5 h-3.5 text-cyan-300" />;
      case 'sheep': return <Sparkles className="w-3.5 h-3.5 text-pink-300" />;
      default: return <Coins className="w-3.5 h-3.5 text-yellow-400" />;
    }
  };

  const selectedTown = selectedEntity?.type === 'town' ? level.towns[selectedEntity.id] : null;
  const selectedNode = selectedEntity?.type === 'node' ? level.nodes[selectedEntity.id] : null;

  return (
    <div id="map-visualizer-container" className="flex flex-col lg:flex-row gap-4 h-full">
      {/* Interactive Map Canvas Container */}
      <div className="flex-1 relative bg-slate-900/90 rounded-2xl border border-slate-800 p-4 overflow-hidden shadow-2xl flex flex-col">
        <div className="flex items-center justify-between mb-3 px-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-indigo-500/20 text-indigo-400 text-xs font-bold border border-indigo-500/30">
              MAP
            </span>
            <h3 className="font-semibold text-slate-200 text-sm tracking-wide">
              Enteland World Topology & Route Network
            </h3>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
              <span>Town (10)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
              <span>Resource Node (14)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full border-2 border-emerald-400 bg-emerald-500/30"></span>
              <span>Player Position</span>
            </div>
          </div>
        </div>

        {/* SVG Network Graph */}
        <div className="flex-1 w-full relative min-h-[480px]">
          <svg
            viewBox="0 0 920 580"
            className="w-full h-full select-none"
            style={{ filter: 'drop-shadow(0 4px 12px rgba(0, 0, 0, 0.4))' }}
          >
            {/* Background Grid Pattern */}
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
              </pattern>
              <linearGradient id="routeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#6366f1" stopOpacity="0.8" />
              </linearGradient>
            </defs>
            <rect width="920" height="580" fill="url(#grid)" />

            {/* Routes / Edges */}
            {level.routes.map((r, i) => {
              const p1 = nodePositions[r.a];
              const p2 = nodePositions[r.b];
              if (!p1 || !p2) return null;
              const isToll = r.toll > 0;
              const isFast = !!r.fast;
              const isConnectedToPlayer = r.a === playerPos || r.b === playerPos;

              const midX = (p1.x + p2.x) / 2;
              const midY = (p1.y + p2.y) / 2;

              return (
                <g key={`route-${i}`}>
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    stroke={
                      isConnectedToPlayer
                        ? '#38bdf8'
                        : isToll
                        ? '#ef4444'
                        : isFast
                        ? '#10b981'
                        : '#475569'
                    }
                    strokeWidth={isConnectedToPlayer ? 2.5 : isToll ? 2 : 1.5}
                    strokeDasharray={isToll ? '4 3' : undefined}
                    strokeOpacity={isConnectedToPlayer ? 0.9 : 0.4}
                  />
                  {/* Weight label badge */}
                  <g transform={`translate(${midX}, ${midY})`}>
                    <circle r="8" fill="#0f172a" stroke="#334155" strokeWidth="1" />
                    <text
                      textAnchor="middle"
                      dy="3"
                      fontSize="9"
                      fill={isToll ? '#f87171' : '#94a3b8'}
                      fontWeight="bold"
                    >
                      {r.weight}
                    </text>
                  </g>
                </g>
              );
            })}

            {/* Resource Nodes */}
            {Object.entries(level.nodes).map(([nId, node]) => {
              const pos = nodePositions[nId];
              if (!pos) return null;
              const isPlayerHere = playerPos === nId;
              const isSelected = selectedEntity?.id === nId;

              return (
                <g
                  key={`node-${nId}`}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  className="cursor-pointer transition-transform hover:scale-110"
                  onClick={() => setSelectedEntity({ type: 'node', id: nId })}
                >
                  <circle
                    r={isSelected ? 16 : 13}
                    fill="#1e293b"
                    stroke={isSelected ? '#f59e0b' : isPlayerHere ? '#10b981' : '#475569'}
                    strokeWidth={isSelected ? 3 : isPlayerHere ? 2.5 : 1.5}
                  />
                  <text
                    textAnchor="middle"
                    dy="3"
                    fontSize="9"
                    fill="#f8fafc"
                    fontWeight="600"
                  >
                    {nId}
                  </text>
                  {/* Node Resource Pill */}
                  <g transform="translate(0, 20)">
                    <rect
                      x="-24"
                      y="-7"
                      width="48"
                      height="14"
                      rx="7"
                      fill="#0f172a"
                      stroke="#334155"
                      strokeWidth="1"
                    />
                    <text
                      textAnchor="middle"
                      dy="3"
                      fontSize="8"
                      fill="#cbd5e1"
                      fontWeight="500"
                    >
                      {node.resource} (+{node.yield})
                    </text>
                  </g>
                </g>
              );
            })}

            {/* Towns */}
            {Object.entries(level.towns).map(([tId, town]) => {
              const pos = nodePositions[tId];
              if (!pos) return null;
              const isPlayerHere = playerPos === tId;
              const isSelected = selectedEntity?.id === tId;
              const builtList = upgradesBuilt[tId] || [];
              const hasCraftingAffinity = town.affinities?.includes('crafting');

              return (
                <g
                  key={`town-${tId}`}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  className="cursor-pointer transition-transform hover:scale-105"
                  onClick={() => setSelectedEntity({ type: 'town', id: tId })}
                >
                  {/* Outer aura for upgraded town */}
                  {builtList.length > 0 && (
                    <circle
                      r="28"
                      fill="none"
                      stroke="#6366f1"
                      strokeWidth="1"
                      strokeOpacity="0.4"
                      strokeDasharray="3 2"
                    />
                  )}

                  {/* Main Town Hexagon/Circle */}
                  <circle
                    r={isSelected ? 22 : 18}
                    fill={hasCraftingAffinity ? '#312e81' : '#1e1b4b'}
                    stroke={
                      isSelected
                        ? '#818cf8'
                        : isPlayerHere
                        ? '#34d399'
                        : builtList.length === 10
                        ? '#f59e0b'
                        : '#6366f1'
                    }
                    strokeWidth={isSelected ? 3.5 : isPlayerHere ? 3 : 2}
                  />

                  {/* Town Icon */}
                  <text
                    textAnchor="middle"
                    dy="4"
                    fontSize="10"
                    fill="#ffffff"
                    fontWeight="bold"
                  >
                    {tId.substring(0, 3)}
                  </text>

                  {/* Town Name & Upgrades Badge */}
                  <g transform="translate(0, -26)">
                    <rect
                      x="-38"
                      y="-8"
                      width="76"
                      height="16"
                      rx="8"
                      fill="#090d16"
                      stroke={builtList.length === 10 ? '#f59e0b' : '#3730a3'}
                      strokeWidth="1"
                    />
                    <text
                      textAnchor="middle"
                      dy="4"
                      fontSize="9"
                      fill={builtList.length === 10 ? '#fde047' : '#e0e7ff'}
                      fontWeight="bold"
                    >
                      {tId} ({builtList.length}/10)
                    </text>
                  </g>
                </g>
              );
            })}

            {/* Active Player Marker */}
            {playerCoord && (
              <g transform={`translate(${playerCoord.x}, ${playerCoord.y})`}>
                {/* Ripple animation */}
                <circle r="30" fill="none" stroke="#34d399" strokeWidth="1.5" opacity="0.6">
                  <animate
                    attributeName="r"
                    values="16;36"
                    dur="1.8s"
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="opacity"
                    values="0.8;0"
                    dur="1.8s"
                    repeatCount="indefinite"
                  />
                </circle>
                <circle r="7" fill="#10b981" stroke="#ffffff" strokeWidth="2" />
              </g>
            )}
          </svg>
        </div>
      </div>

      {/* Detail Sidebar / Inspector Card */}
      <div className="w-full lg:w-80 bg-slate-900/90 rounded-2xl border border-slate-800 p-5 flex flex-col justify-between shadow-xl">
        <div>
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <Info className="w-4 h-4 text-indigo-400" />
            <h4 className="font-semibold text-slate-200 text-sm">Entity Inspector</h4>
          </div>

          {selectedTown && (
            <div className="mt-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    {selectedTown.name || selectedEntity?.id}
                    {selectedTown.affinities?.includes('crafting') && (
                      <span className="px-2 py-0.5 text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full">
                        Crafting Affinity
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-slate-400">Town Location</p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono font-bold text-amber-400">
                    {(upgradesBuilt[selectedEntity!.id] || []).length} / 10
                  </span>
                  <p className="text-[10px] text-slate-500">Upgrades</p>
                </div>
              </div>

              {/* Passive Trickle Generation */}
              <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800/80">
                <p className="text-[11px] font-semibold text-slate-400 mb-2">Passive Generation</p>
                <div className="space-y-1.5 text-xs">
                  {selectedTown.trickle_enteloot && (
                    <div className="flex items-center justify-between text-yellow-300">
                      <span className="flex items-center gap-1.5">
                        <Coins className="w-3.5 h-3.5" /> Enteloot
                      </span>
                      <span>
                        +{selectedTown.trickle_enteloot.amount} / {selectedTown.trickle_enteloot.interval} ticks
                      </span>
                    </div>
                  )}
                  {selectedTown.trickle_production && Object.entries(selectedTown.trickle_production).map(([res, spec]) => (
                    <div key={res} className="flex items-center justify-between text-slate-300">
                      <span className="flex items-center gap-1.5 capitalize">
                        {getNodeIcon(res)} {res}
                      </span>
                      <span>
                        +{spec.amount} / {spec.interval} ticks
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Upgrades Built In This Town */}
              <div>
                <p className="text-[11px] font-semibold text-slate-400 mb-2">Upgrades Built</p>
                <div className="flex flex-wrap gap-1.5">
                  {ALL_UPGRADES && Object.keys(ALL_UPGRADES).map(uKey => {
                    const isBuilt = (upgradesBuilt[selectedEntity!.id] || []).includes(uKey);
                    return (
                      <span
                        key={uKey}
                        className={`text-[10px] px-2 py-1 rounded-md border font-medium transition-colors ${
                          isBuilt
                            ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                            : 'bg-slate-950/40 border-slate-800 text-slate-500 line-through'
                        }`}
                      >
                        {uKey}
                      </span>
                    );
                  })}
                </div>
              </div>

              {/* Item Buy/Sell Rates */}
              {selectedTown.item_rates && (
                <div>
                  <p className="text-[11px] font-semibold text-slate-400 mb-2">Crafted Goods Sell Rates</p>
                  <div className="max-h-36 overflow-y-auto pr-1 space-y-1 text-xs">
                    {Object.entries(selectedTown.item_rates).map(([item, rate]) => (
                      <div
                        key={item}
                        className="flex items-center justify-between py-1 px-2 rounded bg-slate-950/40 border border-slate-800/50"
                      >
                        <span className="capitalize text-slate-300">{item}</span>
                        <span className="font-mono text-amber-400 font-medium">{rate} 🪙</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {selectedNode && (
            <div className="mt-4 space-y-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  {selectedNode.type} Node ({selectedEntity?.id})
                </h3>
                <p className="text-xs text-slate-400">Resource Harvest Site</p>
              </div>

              <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800/80 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Resource Harvested:</span>
                  <span className="font-bold text-white flex items-center gap-1 capitalize">
                    {getNodeIcon(selectedNode.resource)} {selectedNode.resource}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Yield per Gather:</span>
                  <span className="font-mono font-bold text-emerald-400">+{selectedNode.yield} units</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Gather Time:</span>
                  <span className="font-mono text-slate-300">{selectedNode.gather_time} ticks</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Raw Market Sell Price:</span>
                  <span className="font-mono text-amber-400">
                    {RESOURCES[selectedNode.resource]?.sell_price || 0} 🪙 / unit
                  </span>
                </div>
              </div>
            </div>
          )}

          {!selectedEntity && (
            <div className="py-12 text-center text-slate-500 text-xs">
              <MapPin className="w-8 h-8 mx-auto text-slate-600 mb-2 opacity-60" />
              Click any Town or Resource Node on the map to inspect its rates, upgrades, yields, and connections.
            </div>
          )}
        </div>

        {/* Current Position Summary */}
        <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-400">Player Location:</span>
          </div>
          <span className="font-bold text-emerald-300">{playerPos}</span>
        </div>
      </div>
    </div>
  );
};
