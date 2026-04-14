/**
 * Sidebar — Navegación lateral persistente (desktop).
 * En mobile, se oculta y se usa Bottom Nav.
 */

import { motion } from 'framer-motion';
import { SignalIcon } from '@heroicons/react/24/outline';
import { TABS } from './navConfig';

export function Sidebar({ activeTab, onTabChange, lastCycle, mode }) {
  return (
    <aside className="hidden md:flex flex-col w-56 border-r border-tv-border bg-tv-panel/60 backdrop-blur-sm">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-tv-border">
        <div className="w-8 h-8 bg-gradient-to-br from-tv-blue to-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-tv-blue/20">
          <SignalIcon className="w-4 h-4 text-white" />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-bold text-tv-text leading-tight truncate">
            Agente
          </div>
          <div className="text-[10px] text-tv-text-dim">de Trading</div>
        </div>
      </div>

      {/* Nav items */}
      <nav className="flex-1 p-2 space-y-0.5">
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              className={`relative w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                active
                  ? 'text-tv-text bg-tv-panel-2'
                  : 'text-tv-text-dim hover:text-tv-text hover:bg-tv-panel-2/50'
              }`}
            >
              {active && (
                <motion.div
                  layoutId="sidebar-active-indicator"
                  className="absolute left-0 top-1 bottom-1 w-0.5 bg-tv-blue rounded-r"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer con versión + estado */}
      <div className="px-4 py-3 border-t border-tv-border space-y-1">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              mode === 'LIVE'
                ? 'bg-tv-up animate-pulse'
                : mode === 'SIMULATION'
                ? 'bg-tv-blue animate-pulse'
                : 'bg-tv-text-dim'
            }`}
          />
          <span className="text-[10px] text-tv-text-dim uppercase tracking-wider">
            {mode || 'UNKNOWN'}
          </span>
        </div>
        <div className="text-[10px] text-tv-text-dim">
          Ultimo ciclo: {lastCycle}
        </div>
        <div className="text-[10px] text-tv-text-dim/60">v2.0.0</div>
      </div>
    </aside>
  );
}
