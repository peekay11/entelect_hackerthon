import React, { useState, useMemo } from 'react';
import { LogEntry } from '../types';
import { Search, Filter, CheckCircle2, AlertCircle, Clock, ExternalLink } from 'lucide-react';

interface ActionLogViewerProps {
  logs: LogEntry[];
  currentActionIndex: number;
  onSelectActionIndex: (idx: number) => void;
}

export const ActionLogViewer: React.FC<ActionLogViewerProps> = ({
  logs,
  currentActionIndex,
  onSelectActionIndex
}) => {
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const filteredLogs = useMemo(() => {
    return logs.filter(l => {
      if (filterType !== 'all' && l.action.type !== filterType) return false;
      if (filterStatus !== 'all' && l.status !== filterStatus) return false;
      if (!search.trim()) return true;

      const q = search.toLowerCase();
      return (
        l.action.type.toLowerCase().includes(q) ||
        (l.action.destination && l.action.destination.toLowerCase().includes(q)) ||
        (l.action.item && l.action.item.toLowerCase().includes(q)) ||
        (l.action.upgrade && l.action.upgrade.toLowerCase().includes(q)) ||
        (l.detail && l.detail.toLowerCase().includes(q))
      );
    });
  }, [logs, search, filterType, filterStatus]);

  const okCount = logs.filter(l => l.status === 'ok').length;
  const invCount = logs.filter(l => l.status === 'invalid').length;
  const skipCount = logs.filter(l => l.status === 'skipped_tick_limit').length;

  return (
    <div id="action-log-viewer" className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl space-y-4">
      {/* Header with stats badges */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-white text-base">Execution Action Trace & Audit Log</h3>
          <p className="text-xs text-slate-400">
            Chronological log of all simulated actions with validity checks and state transitions.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-3 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> {okCount} Valid OK
          </span>
          {invCount > 0 && (
            <span className="px-3 py-1 rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/30 font-semibold flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" /> {invCount} Invalid
            </span>
          )}
          {skipCount > 0 && (
            <span className="px-3 py-1 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold">
              {skipCount} Skipped Limit
            </span>
          )}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search actions, destinations, upgrades, items..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Action Type Filter */}
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="all">All Action Types</option>
          <option value="travel">Travel</option>
          <option value="gather">Gather</option>
          <option value="craft">Craft</option>
          <option value="build">Build</option>
          <option value="sell">Sell</option>
        </select>

        {/* Status Filter */}
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="all">All Statuses</option>
          <option value="ok">OK (Valid)</option>
          <option value="invalid">Invalid</option>
          <option value="skipped_tick_limit">Skipped (Tick Limit)</option>
        </select>
      </div>

      {/* Table of Actions */}
      <div className="max-h-96 overflow-y-auto border border-slate-800 rounded-xl">
        <table className="w-full text-xs text-left border-collapse">
          <thead className="sticky top-0 bg-slate-950 border-b border-slate-800 text-slate-400 font-semibold z-10">
            <tr>
              <th className="py-2.5 px-3">#</th>
              <th className="py-2.5 px-2">Ticks</th>
              <th className="py-2.5 px-2">Action</th>
              <th className="py-2.5 px-3">Parameters</th>
              <th className="py-2.5 px-2 text-center">Status</th>
              <th className="py-2.5 px-3">Player Pos</th>
              <th className="py-2.5 px-3 text-right">Enteloot After</th>
              <th className="py-2.5 px-2 text-center">Jump</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredLogs.slice(0, 300).map((l) => {
              const isSelected = l.action_index === currentActionIndex;

              return (
                <tr
                  key={l.action_index}
                  onClick={() => onSelectActionIndex(l.action_index)}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-indigo-950/40 text-indigo-200 border-l-4 border-indigo-500'
                      : 'hover:bg-slate-800/40 text-slate-300'
                  }`}
                >
                  <td className="py-2 px-3 text-slate-500">{l.action_index + 1}</td>
                  <td className="py-2 px-2 text-slate-400">
                    {l.start_tick} → {l.end_tick} (+{l.end_tick - l.start_tick})
                  </td>
                  <td className="py-2 px-2 capitalize font-bold text-white">
                    {l.action.type}
                  </td>
                  <td className="py-2 px-3 font-sans text-xs">
                    {l.action.type === 'travel' && (
                      <span className="text-blue-300">Destination: {l.action.destination}</span>
                    )}
                    {l.action.type === 'gather' && (
                      <span className="text-amber-300">Harvest raw node resource</span>
                    )}
                    {l.action.type === 'craft' && (
                      <span className="text-orange-300">
                        {l.action.quantity || 1}x {l.action.item}
                      </span>
                    )}
                    {l.action.type === 'build' && (
                      <span className="text-purple-300">Upgrade: {l.action.upgrade}</span>
                    )}
                    {l.action.type === 'sell' && (
                      <span className="text-emerald-300">
                        {l.action.quantity || 1}x {l.action.item}
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-2 text-center">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        l.status === 'ok'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : l.status === 'invalid'
                          ? 'bg-rose-500/20 text-rose-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {l.status}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-300">{l.player_pos_after}</td>
                  <td className="py-2 px-3 text-right font-bold text-amber-300">
                    {(l.enteloot_after ?? 0).toLocaleString()} 🪙
                  </td>
                  <td className="py-2 px-2 text-center text-slate-500 hover:text-indigo-400">
                    <ExternalLink className="w-3.5 h-3.5 mx-auto" />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {filteredLogs.length > 300 && (
        <p className="text-[11px] text-slate-500 text-center">
          Showing first 300 of {filteredLogs.length} matching actions. Use search or filters to narrow down.
        </p>
      )}
    </div>
  );
};
