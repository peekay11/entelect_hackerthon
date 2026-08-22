import React, { useState, useMemo } from 'react';
import { 
  LEVEL2_DATA, 
  LEVEL2_ACTIONS, 
  LEVEL1_ACTIONS, 
  WORKED_EXAMPLE_DATA, 
  WORKED_EXAMPLE_ACTIONS 
} from './engine/levelPresets';
import { ClientSimulator } from './engine/simulator';
import { MapVisualizer } from './components/MapVisualizer';
import { TimelineController } from './components/TimelineController';
import { TownStatusMatrix } from './components/TownStatusMatrix';
import { ActionLogViewer } from './components/ActionLogViewer';
import { EconomicsDashboard } from './components/EconomicsDashboard';
import { ActionRunnerModal } from './components/ActionRunnerModal';
import { Action, LevelData } from './types';
import { 
  Trophy, 
  Coins, 
  Map, 
  Layers, 
  ScrollText, 
  BarChart3, 
  Code2, 
  Download,
  Sparkles,
  CheckCircle,
  Play
} from 'lucide-react';

export function App() {
  const [selectedLevelId, setSelectedLevelId] = useState<'2' | '1' | 'worked_example'>('2');
  const [customActions, setCustomActions] = useState<Action[] | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Active Level Data & Actions
  const currentLevelData: LevelData = useMemo(() => {
    if (selectedLevelId === 'worked_example') {
      return WORKED_EXAMPLE_DATA as unknown as LevelData;
    }
    return LEVEL2_DATA as unknown as LevelData;
  }, [selectedLevelId]);

  const currentActions: Action[] = useMemo(() => {
    if (customActions) return customActions;
    if (selectedLevelId === 'worked_example') return WORKED_EXAMPLE_ACTIONS as Action[];
    if (selectedLevelId === '1') return LEVEL1_ACTIONS as Action[];
    return LEVEL2_ACTIONS as Action[];
  }, [selectedLevelId, customActions]);

  // Run simulation
  const sim = useMemo(() => {
    return new ClientSimulator(currentLevelData, currentActions);
  }, [currentLevelData, currentActions]);

  // Timeline State
  const [timelineIndex, setTimelineIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(20);
  const [activeTab, setActiveTab] = useState<'map' | 'matrix' | 'logs' | 'economy'>('map');

  const snapshot = sim.timeline[Math.min(timelineIndex, sim.timeline.length - 1)] || sim.timeline[0];

  const handleLevelChange = (lvl: '2' | '1' | 'worked_example') => {
    setSelectedLevelId(lvl);
    setCustomActions(null);
    setTimelineIndex(0);
    setIsPlaying(false);
  };

  const handleDownloadActions = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({ actions: currentActions }, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `level${selectedLevelId}_actions.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-4 lg:px-8 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-amber-500 p-0.5 shadow-lg flex items-center justify-center">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Trophy className="w-5 h-5 text-amber-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-black text-lg text-white tracking-tight">Age of Enteland</h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  SOLVER v2.0
                </span>
              </div>
              <p className="text-xs text-slate-400">Tactical Strategy Optimizer & Live Simulation Engine</p>
            </div>
          </div>

          {/* Level Switcher Pills */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => handleLevelChange('2')}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-colors ${
                selectedLevelId === '2'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Level 2 (Full Infrastructure)
            </button>
            <button
              onClick={() => handleLevelChange('1')}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-colors ${
                selectedLevelId === '1'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Level 1 (Harvester)
            </button>
            <button
              onClick={() => handleLevelChange('worked_example')}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-colors ${
                selectedLevelId === 'worked_example'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Worked Example
            </button>
          </div>

          {/* Action Runner & Export Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition-colors"
            >
              <Code2 className="w-3.5 h-3.5 text-indigo-400" /> Custom JSON
            </button>
            <button
              onClick={handleDownloadActions}
              className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-md transition-all"
            >
              <Download className="w-3.5 h-3.5" /> Export Actions
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 lg:p-8 space-y-6">
        {/* Real-time Economic Metrics Cards */}
        <EconomicsDashboard snapshot={snapshot} />

        {/* Playback Scrubbing Timeline */}
        <TimelineController
          timeline={sim.timeline}
          currentIndex={timelineIndex}
          onIndexChange={(idx) => setTimelineIndex(idx)}
          isPlaying={isPlaying}
          onTogglePlay={() => setIsPlaying(!isPlaying)}
          speed={speed}
          onSpeedChange={(s) => setSpeed(s)}
          totalTicks={currentLevelData.total_ticks}
        />

        {/* View Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2 text-xs font-bold">
          <button
            onClick={() => setActiveTab('map')}
            className={`px-4 py-2 rounded-xl flex items-center gap-2 transition-colors ${
              activeTab === 'map'
                ? 'bg-slate-800 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Map className="w-4 h-4 text-indigo-400" /> World Topology & Simulation Map
          </button>
          <button
            onClick={() => setActiveTab('matrix')}
            className={`px-4 py-2 rounded-xl flex items-center gap-2 transition-colors ${
              activeTab === 'matrix'
                ? 'bg-slate-800 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-4 h-4 text-amber-400" /> Town Upgrade Matrix (100/100)
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-4 py-2 rounded-xl flex items-center gap-2 transition-colors ${
              activeTab === 'logs'
                ? 'bg-slate-800 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ScrollText className="w-4 h-4 text-emerald-400" /> Action Audit Log ({sim.logs.length})
          </button>
        </div>

        {/* Active Tab Component */}
        <div className="min-h-[500px]">
          {activeTab === 'map' && (
            <MapVisualizer
              level={currentLevelData}
              playerPos={snapshot.player_pos}
              upgradesBuilt={snapshot.upgrades_built}
              currentTick={snapshot.tick}
            />
          )}

          {activeTab === 'matrix' && (
            <TownStatusMatrix
              level={currentLevelData}
              upgradesBuilt={snapshot.upgrades_built}
            />
          )}

          {activeTab === 'logs' && (
            <ActionLogViewer
              logs={sim.logs}
              currentActionIndex={snapshot.action_index}
              onSelectActionIndex={(idx) => {
                setTimelineIndex(idx);
                setIsPlaying(false);
              }}
            />
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 py-4 px-4 text-center text-xs text-slate-500">
        Age of Enteland Competition Strategy Optimizer & Live Simulator — Built with React & TypeScript
      </footer>

      {/* Custom Action Runner Modal */}
      <ActionRunnerModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        level={currentLevelData}
        onLoadCustomActions={(acts) => {
          setCustomActions(acts);
          setTimelineIndex(0);
          setIsPlaying(false);
        }}
      />
    </div>
  );
}
