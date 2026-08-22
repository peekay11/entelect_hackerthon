import React, { useEffect, useRef } from 'react';
import { 
  Play, 
  Pause, 
  SkipBack, 
  SkipForward, 
  RotateCcw, 
  Zap, 
  Clock,
  Compass,
  Hammer,
  ShoppingBag,
  Layers,
  Sparkles
} from 'lucide-react';
import { Action } from '../types';
import { TimelineSnapshot } from '../engine/simulator';

interface TimelineControllerProps {
  timeline: TimelineSnapshot[];
  currentIndex: number;
  onIndexChange: (idx: number) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
  totalTicks: number;
}

export const TimelineController: React.FC<TimelineControllerProps> = ({
  timeline,
  currentIndex,
  onIndexChange,
  isPlaying,
  onTogglePlay,
  speed,
  onSpeedChange,
  totalTicks
}) => {
  const currentSnapshot = timeline[currentIndex] || timeline[0];
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(10, Math.floor(1000 / (10 * speed)));
      timerRef.current = window.setInterval(() => {
        onIndexChange(Math.min(timeline.length - 1, currentIndex + 1));
      }, intervalMs);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, currentIndex, speed, timeline.length, onIndexChange]);

  const getActionIcon = (act: Action | null) => {
    if (!act) return <Clock className="w-4 h-4 text-slate-400" />;
    switch (act.type) {
      case 'travel': return <Compass className="w-4 h-4 text-blue-400" />;
      case 'gather': return <Sparkles className="w-4 h-4 text-amber-400" />;
      case 'craft': return <Hammer className="w-4 h-4 text-orange-400" />;
      case 'build': return <Layers className="w-4 h-4 text-purple-400" />;
      case 'sell': return <ShoppingBag className="w-4 h-4 text-emerald-400" />;
      default: return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div id="timeline-controller" className="bg-slate-900/90 rounded-2xl border border-slate-800 p-4 shadow-xl space-y-4">
      {/* Top row: Playback buttons, Speed controls, Tick readout */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Playback Button Group */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onIndexChange(0)}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Reset to Tick 0"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={() => onIndexChange(Math.max(0, currentIndex - 1))}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Step Back"
          >
            <SkipBack className="w-4 h-4" />
          </button>
          <button
            onClick={onTogglePlay}
            className={`px-4 py-2 rounded-lg font-bold flex items-center gap-2 text-sm transition-all shadow-md ${
              isPlaying
                ? 'bg-amber-500 hover:bg-amber-600 text-slate-950'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white'
            }`}
          >
            {isPlaying ? (
              <>
                <Pause className="w-4 h-4 fill-current" /> Pause
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" /> Play Simulation
              </>
            )}
          </button>
          <button
            onClick={() => onIndexChange(Math.min(timeline.length - 1, currentIndex + 1))}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Step Forward"
          >
            <SkipForward className="w-4 h-4" />
          </button>
          <button
            onClick={() => onIndexChange(timeline.length - 1)}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Jump to End"
          >
            <Zap className="w-4 h-4 text-amber-400" />
          </button>
        </div>

        {/* Speed Selector */}
        <div className="flex items-center gap-1.5 bg-slate-950/70 p-1 rounded-xl border border-slate-800">
          {[1, 5, 20, 50, 100].map((s) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                speed === s
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Live Action Status Card */}
        <div className="flex items-center gap-3 bg-slate-950/80 px-3 py-1.5 rounded-xl border border-slate-800 text-xs">
          <div className="flex items-center gap-1.5">
            {getActionIcon(currentSnapshot.active_action)}
            <span className="font-semibold capitalize text-slate-200">
              {currentSnapshot.active_action?.type || 'Idle Start'}
            </span>
          </div>
          {currentSnapshot.active_action && (
            <span className="text-slate-400 font-mono">
              {currentSnapshot.active_action.destination && `→ ${currentSnapshot.active_action.destination}`}
              {currentSnapshot.active_action.item && `${currentSnapshot.active_action.quantity || 1}x ${currentSnapshot.active_action.item}`}
              {currentSnapshot.active_action.upgrade && `★ ${currentSnapshot.active_action.upgrade}`}
            </span>
          )}
          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            {currentSnapshot.action_status.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Scrubber Timeline Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-mono font-medium">
            Tick <strong className="text-white font-bold text-sm">{currentSnapshot.tick}</strong> / {totalTicks}
          </span>
          <span className="font-mono text-slate-400">
            Step <strong className="text-indigo-300">{currentIndex + 1}</strong> of {timeline.length}
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={timeline.length - 1}
          value={currentIndex}
          onChange={(e) => onIndexChange(Number(e.target.value))}
          className="w-full h-2.5 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-500 border border-slate-800"
        />
      </div>
    </div>
  );
};
