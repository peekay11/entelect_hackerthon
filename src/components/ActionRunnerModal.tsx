import React, { useState } from 'react';
import { Action, LevelData } from '../types';
import { Play, Code, CheckCircle2, AlertCircle, X, Download } from 'lucide-react';
import { ClientSimulator } from '../engine/simulator';

interface ActionRunnerModalProps {
  isOpen: boolean;
  onClose: () => void;
  level: LevelData;
  onLoadCustomActions: (actions: Action[]) => void;
}

export const ActionRunnerModal: React.FC<ActionRunnerModalProps> = ({
  isOpen,
  onClose,
  level,
  onLoadCustomActions
}) => {
  const [jsonText, setJsonText] = useState<string>('{\n  "actions": [\n    {"type": "travel", "destination": "N2"},\n    {"type": "gather"}\n  ]\n}');
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    actionsCount: number;
    score: number;
    error?: string;
  } | null>(null);

  if (!isOpen) return null;

  const handleTestSimulation = () => {
    try {
      const parsed = JSON.parse(jsonText);
      const actionList: Action[] = Array.isArray(parsed) ? parsed : parsed.actions;
      if (!Array.isArray(actionList)) {
        setValidationResult({
          valid: false,
          actionsCount: 0,
          score: 0,
          error: 'JSON must contain an array or an object with an "actions" array.'
        });
        return;
      }

      const sim = new ClientSimulator(level, actionList);
      const invalidCount = sim.logs.filter(l => l.status === 'invalid').length;

      setValidationResult({
        valid: invalidCount === 0,
        actionsCount: actionList.length,
        score: sim.finalScore,
        error: invalidCount > 0 ? `${invalidCount} invalid action(s) detected.` : undefined
      });
    } catch (e: any) {
      setValidationResult({
        valid: false,
        actionsCount: 0,
        score: 0,
        error: e.message || 'Invalid JSON syntax'
      });
    }
  };

  const handleApply = () => {
    try {
      const parsed = JSON.parse(jsonText);
      const actionList: Action[] = Array.isArray(parsed) ? parsed : parsed.actions;
      if (Array.isArray(actionList)) {
        onLoadCustomActions(actionList);
        onClose();
      }
    } catch (e) {
      // ignore
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Code className="w-5 h-5 text-indigo-400" />
            <h3 className="font-bold text-white text-base">Custom Strategy & Action Runner</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Editor Body */}
        <div className="p-4 space-y-3 flex-1 overflow-y-auto">
          <p className="text-xs text-slate-400">
            Paste or edit an Age of Enteland JSON action sequence to simulate and benchmark in real time:
          </p>
          <textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            rows={12}
            className="w-full bg-slate-950 font-mono text-xs text-slate-200 p-3 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500 selection:bg-indigo-600"
          />

          {/* Validation Result Preview */}
          {validationResult && (
            <div
              className={`p-3 rounded-xl border text-xs flex items-start gap-2.5 ${
                validationResult.valid
                  ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
                  : 'bg-rose-950/30 border-rose-500/40 text-rose-300'
              }`}
            >
              {validationResult.valid ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              )}
              <div className="space-y-0.5">
                <p className="font-bold">
                  {validationResult.valid ? 'Simulation Passed (100% Valid)' : 'Simulation Failed'}
                </p>
                <p>
                  Actions tested: <strong>{validationResult.actionsCount}</strong> | Resulting Score:{' '}
                  <strong>{(validationResult.score ?? 0).toLocaleString()}</strong>
                </p>
                {validationResult.error && <p className="text-rose-400">{validationResult.error}</p>}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/40 flex items-center justify-between">
          <button
            onClick={handleTestSimulation}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Play className="w-3.5 h-3.5" /> Test Simulation
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl hover:bg-slate-800 text-slate-400 text-xs font-semibold transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleApply}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-md"
            >
              Load into Visualizer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
