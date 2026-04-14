/**
 * Topbar — barra superior simplificada estilo fintech.
 * Contiene: breadcrumb (título tab actual), balance y mode badge (display-only).
 * NO incluye AccountSelector ni DateFilter (esos viven en PageHeader).
 */

import { TABS } from './navConfig';

const TAB_NAMES = Object.fromEntries(TABS.map((t) => [t.id, t.label]));

export function Topbar({ agentData, mode, activeTab }) {
  const tabName = TAB_NAMES[activeTab] || '';

  return (
    <header className="sticky top-0 z-30 bg-fm-surface/85 backdrop-blur-xl border-b border-fm-border">
      <div className="px-4 md:px-8 h-16 flex items-center gap-4">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm min-w-0">
          <span className="text-fm-text-dim hidden sm:inline">Agente</span>
          <span className="text-fm-text-dim hidden sm:inline">/</span>
          <span className="text-fm-text font-semibold truncate">{tabName}</span>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Balance */}
        <div className="text-right">
          <div className="text-[11px] text-fm-text-dim leading-tight">Balance</div>
          <div className="text-sm font-semibold text-fm-text font-mono tabular-nums">
            ${agentData?.capital_usd?.toFixed(2) || '0.00'}
          </div>
        </div>

        {/* Mode badge (display-only) */}
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${
            mode === 'LIVE'
              ? 'bg-fm-danger-soft text-fm-danger'
              : mode === 'SIMULATION'
              ? 'bg-fm-primary-soft text-fm-primary'
              : mode === 'SHUTDOWN'
              ? 'bg-fm-danger-soft text-fm-danger'
              : 'bg-fm-surface-2 text-fm-text-dim'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              mode === 'LIVE'
                ? 'bg-fm-danger animate-pulse'
                : mode === 'SIMULATION'
                ? 'bg-fm-primary animate-pulse'
                : 'bg-fm-text-dim'
            }`}
          />
          {mode || 'UNKNOWN'}
        </span>
      </div>
    </header>
  );
}
