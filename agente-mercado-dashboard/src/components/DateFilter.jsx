/**
 * DateFilter — Selector de rango de fechas para filtrar datos.
 * Usado en StrategiesPage y StrategyDetail.
 */

import { useState } from 'react';

const PRESETS = [
  { label: 'Hoy', getValue: () => { const d = new Date().toISOString().slice(0, 10); return { from: d, to: d }; } },
  { label: '7d', getValue: () => { const t = new Date(); const f = new Date(t - 7*86400000); return { from: f.toISOString().slice(0,10), to: t.toISOString().slice(0,10) }; } },
  { label: '30d', getValue: () => { const t = new Date(); const f = new Date(t - 30*86400000); return { from: f.toISOString().slice(0,10), to: t.toISOString().slice(0,10) }; } },
  { label: 'Todo', getValue: () => ({ from: null, to: null }) },
];

export function DateFilter({ fromDate, toDate, onChange }) {
  const [showCustom, setShowCustom] = useState(false);

  const handlePreset = (preset) => {
    const { from, to } = preset.getValue();
    onChange(from, to);
    setShowCustom(false);
  };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {PRESETS.map((preset) => (
        <button
          key={preset.label}
          onClick={() => handlePreset(preset)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            (preset.label === 'Todo' && !fromDate && !toDate) ||
            (preset.label === 'Hoy' && fromDate === new Date().toISOString().slice(0, 10))
              ? 'bg-blue-500/20 text-blue-400 ring-1 ring-blue-500/30'
              : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
          }`}
        >
          {preset.label}
        </button>
      ))}
      <button
        onClick={() => setShowCustom(!showCustom)}
        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
          showCustom ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
        }`}
      >
        Rango
      </button>
      {showCustom && (
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={fromDate || ''}
            onChange={(e) => onChange(e.target.value || null, toDate)}
            className="px-2 py-1 rounded-lg bg-gray-800 border border-gray-700 text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
          />
          <span className="text-gray-500 text-xs">a</span>
          <input
            type="date"
            value={toDate || ''}
            onChange={(e) => onChange(fromDate, e.target.value || null)}
            className="px-2 py-1 rounded-lg bg-gray-800 border border-gray-700 text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
          />
        </div>
      )}
    </div>
  );
}
