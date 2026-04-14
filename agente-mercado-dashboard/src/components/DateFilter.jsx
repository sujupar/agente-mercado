/**
 * DateFilter — Selector de rango de fechas para filtrar datos.
 * Usado en StrategiesPage, StrategyDetail y Topbar global.
 */

import { useState } from 'react';

/**
 * Helper exportado: rango del día de HOY en formato ISO YYYY-MM-DD.
 * Usado como default en toda la aplicación.
 */
export const getTodayRange = () => {
  const d = new Date().toISOString().slice(0, 10);
  return { from: d, to: d };
};

const getDaysAgoRange = (days) => {
  const t = new Date();
  const f = new Date(t - days * 86400000);
  return {
    from: f.toISOString().slice(0, 10),
    to: t.toISOString().slice(0, 10),
  };
};

const PRESETS = [
  { label: 'Hoy', key: 'today', getValue: getTodayRange },
  { label: '7d', key: '7d', getValue: () => getDaysAgoRange(7) },
  { label: '30d', key: '30d', getValue: () => getDaysAgoRange(30) },
  { label: 'Todo', key: 'all', getValue: () => ({ from: null, to: null }) },
];

const todayISO = () => new Date().toISOString().slice(0, 10);

const isPresetActive = (preset, fromDate, toDate) => {
  const today = todayISO();
  if (preset.key === 'all') return !fromDate && !toDate;
  if (preset.key === 'today') return fromDate === today && toDate === today;
  const { from, to } = preset.getValue();
  return fromDate === from && toDate === to;
};

export function DateFilter({ fromDate, toDate, onChange, size = 'md' }) {
  const [showCustom, setShowCustom] = useState(false);

  const handlePreset = (preset) => {
    const { from, to } = preset.getValue();
    onChange(from, to);
    setShowCustom(false);
  };

  const btnClasses = size === 'sm'
    ? 'px-2 py-1 text-[11px]'
    : 'px-3 py-1.5 text-xs';

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {PRESETS.map((preset) => {
        const active = isPresetActive(preset, fromDate, toDate);
        return (
          <button
            key={preset.key}
            onClick={() => handlePreset(preset)}
            className={`${btnClasses} rounded-md font-medium transition-colors ${
              active
                ? 'bg-tv-blue/20 text-tv-blue ring-1 ring-tv-blue/40'
                : 'text-tv-text-dim hover:text-tv-text hover:bg-tv-panel-2'
            }`}
          >
            {preset.label}
          </button>
        );
      })}
      <button
        onClick={() => setShowCustom(!showCustom)}
        className={`${btnClasses} rounded-md font-medium transition-colors ${
          showCustom
            ? 'bg-tv-blue/20 text-tv-blue ring-1 ring-tv-blue/40'
            : 'text-tv-text-dim hover:text-tv-text hover:bg-tv-panel-2'
        }`}
      >
        Rango
      </button>
      {showCustom && (
        <div className="flex items-center gap-1.5">
          <input
            type="date"
            value={fromDate || ''}
            onChange={(e) => onChange(e.target.value || null, toDate)}
            className="px-2 py-1 rounded-md bg-tv-panel border border-tv-border text-[11px] text-tv-text focus:border-tv-blue focus:outline-none"
          />
          <span className="text-tv-text-dim text-[11px]">a</span>
          <input
            type="date"
            value={toDate || ''}
            onChange={(e) => onChange(fromDate, e.target.value || null)}
            className="px-2 py-1 rounded-md bg-tv-panel border border-tv-border text-[11px] text-tv-text focus:border-tv-blue focus:outline-none"
          />
        </div>
      )}
    </div>
  );
}
