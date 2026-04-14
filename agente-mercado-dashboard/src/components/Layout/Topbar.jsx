/**
 * Topbar — Barra superior densa estilo TradingView.
 * Contiene: logo (mobile), AccountSelector, DateFilter global, balance, mode.
 */

import { SignalIcon } from '@heroicons/react/24/outline';
import { AccountSelector } from './AccountSelector';
import { DateFilter } from '../DateFilter';
import { useDashboardContext } from '../../context/DashboardContext';

export function Topbar({ agentData, mode }) {
  const { globalFromDate, globalToDate, setGlobalDate } = useDashboardContext();

  return (
    <header className="sticky top-0 z-40 bg-tv-bg/90 backdrop-blur-xl border-b border-tv-border">
      <div className="px-3 md:px-4 h-12 flex items-center gap-3 md:gap-4">
        {/* Logo — solo mobile (en desktop ya está en sidebar) */}
        <div className="md:hidden flex items-center gap-2">
          <div className="w-7 h-7 bg-gradient-to-br from-tv-blue to-indigo-600 rounded-md flex items-center justify-center">
            <SignalIcon className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-xs font-bold text-tv-text">Agente</span>
        </div>

        {/* Account Selector (DEMO/LIVE) */}
        <AccountSelector />

        {/* DateFilter global — oculto en mobile pequeño */}
        <div className="hidden lg:flex items-center gap-2 border-l border-tv-border pl-3">
          <span className="text-[10px] text-tv-text-dim uppercase tracking-wider">Periodo</span>
          <DateFilter
            fromDate={globalFromDate}
            toDate={globalToDate}
            onChange={setGlobalDate}
            size="sm"
          />
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Balance compacto */}
        <div className="flex items-center gap-3 md:gap-4">
          <div className="text-right">
            <div className="text-[9px] text-tv-text-dim uppercase tracking-wider leading-none">
              Balance
            </div>
            <div className="text-sm font-bold text-tv-text font-mono tabular-nums">
              ${agentData?.capital_usd?.toFixed(2) || '0.00'}
            </div>
          </div>

          {/* Risk info */}
          {agentData?.base_capital_usd && (
            <div className="hidden md:block text-right border-l border-tv-border pl-3">
              <div className="text-[9px] text-tv-text-dim uppercase tracking-wider leading-none">
                Riesgo
              </div>
              <div className="text-xs font-semibold text-tv-text-dim font-mono tabular-nums">
                ${agentData.risk_per_trade_usd?.toFixed(2) || '—'}/trade
              </div>
            </div>
          )}

          {/* Mode badge */}
          <span
            className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold tracking-wider ${
              mode === 'LIVE'
                ? 'bg-tv-up/15 text-tv-up ring-1 ring-tv-up/30'
                : mode === 'SIMULATION'
                ? 'bg-tv-blue/15 text-tv-blue ring-1 ring-tv-blue/30'
                : mode === 'SHUTDOWN'
                ? 'bg-tv-down/15 text-tv-down ring-1 ring-tv-down/30'
                : 'bg-tv-panel-2 text-tv-text-dim'
            }`}
          >
            <span
              className={`w-1 h-1 rounded-full ${
                mode === 'LIVE'
                  ? 'bg-tv-up animate-pulse'
                  : mode === 'SIMULATION'
                  ? 'bg-tv-blue animate-pulse'
                  : 'bg-tv-text-dim'
              }`}
            />
            {mode || 'UNKNOWN'}
          </span>
        </div>
      </div>

      {/* DateFilter móvil: fila separada */}
      <div className="lg:hidden px-3 pb-2 flex items-center gap-2">
        <span className="text-[10px] text-tv-text-dim uppercase tracking-wider">Periodo</span>
        <DateFilter
          fromDate={globalFromDate}
          toDate={globalToDate}
          onChange={setGlobalDate}
          size="sm"
        />
      </div>
    </header>
  );
}
