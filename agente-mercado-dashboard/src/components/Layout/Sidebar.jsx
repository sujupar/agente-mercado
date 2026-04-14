/**
 * Sidebar colapsable (desktop) — estilo fintech Stripe/Mercury.
 * Expandido: w-60 con iconos + labels + footer.
 * Colapsado: w-14 solo iconos con tooltip.
 */

import { motion, AnimatePresence } from 'framer-motion';
import {
  SignalIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from '@heroicons/react/24/outline';
import { TABS } from './navConfig';
import { useSidebar } from '../../context/SidebarContext';

export function Sidebar({ activeTab, onTabChange, lastCycle, mode }) {
  const { collapsed, toggle } = useSidebar();

  return (
    <aside
      className={`hidden md:flex flex-col border-r border-fm-border bg-fm-surface transition-[width] duration-200 ease-out ${
        collapsed ? 'w-14' : 'w-60'
      }`}
    >
      {/* Logo */}
      <div className={`flex items-center h-16 border-b border-fm-border ${collapsed ? 'justify-center' : 'px-5 gap-3'}`}>
        <div className="w-8 h-8 bg-gradient-to-br from-fm-primary to-fm-accent rounded-lg flex items-center justify-center flex-shrink-0">
          <SignalIcon className="w-4 h-4 text-white" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden whitespace-nowrap"
            >
              <div className="text-sm font-semibold text-fm-text leading-tight">Agente</div>
              <div className="text-xs text-fm-text-dim">de Mercado</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Nav items */}
      <nav className={`flex-1 py-4 space-y-1 ${collapsed ? 'px-2' : 'px-3'}`}>
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              title={collapsed ? label : undefined}
              className={`group relative w-full flex items-center rounded-lg text-sm font-medium transition-colors focus-ring ${
                collapsed ? 'justify-center h-10' : 'gap-3 px-3 h-10'
              } ${
                active
                  ? 'bg-fm-primary-soft text-fm-primary'
                  : 'text-fm-text-2 hover:bg-fm-surface-2 hover:text-fm-text'
              }`}
            >
              {active && (
                <motion.span
                  layoutId="sidebar-indicator"
                  className="absolute left-0 top-2 bottom-2 w-0.5 bg-fm-primary rounded-r"
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span>{label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Footer: estado */}
      {!collapsed && (
        <div className="px-5 py-4 border-t border-fm-border space-y-2">
          <div className="flex items-center gap-2">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                mode === 'LIVE'
                  ? 'bg-fm-danger animate-pulse'
                  : mode === 'SIMULATION'
                  ? 'bg-fm-primary animate-pulse'
                  : 'bg-fm-text-dim'
              }`}
            />
            <span className="text-xs text-fm-text-2 font-medium">
              {mode || 'UNKNOWN'}
            </span>
          </div>
          <div className="text-[11px] text-fm-text-dim">
            Último ciclo<br />
            <span className="text-fm-text-2 font-medium">{lastCycle}</span>
          </div>
          <div className="text-[10px] text-fm-text-dim/80">v2.0</div>
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={toggle}
        title={collapsed ? 'Expandir' : 'Contraer'}
        className={`flex items-center border-t border-fm-border h-10 text-fm-text-dim hover:text-fm-text hover:bg-fm-surface-2 transition-colors focus-ring ${
          collapsed ? 'justify-center' : 'justify-end px-5'
        }`}
      >
        {collapsed ? (
          <ChevronDoubleRightIcon className="w-4 h-4" />
        ) : (
          <ChevronDoubleLeftIcon className="w-4 h-4" />
        )}
      </button>
    </aside>
  );
}
