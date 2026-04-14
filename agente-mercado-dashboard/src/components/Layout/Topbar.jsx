/**
 * Topbar — barra superior simplificada estilo fintech con selector DEMO/LIVE.
 * NO duplica AccountSelector ni DateFilter (viven en cada PageHeader).
 *
 * El balance se obtiene del broker singleton (fuente de verdad), no del
 * agentData (que puede tener desfase si el sync no ha corrido).
 */

import { TABS } from './navConfig';
import { EnvironmentSelector } from './EnvironmentSelector';
import { useDashboardContext } from '../../context/DashboardContext';
import { useBrokerEnvironments } from '../../hooks/useBrokerEnvironments';

const TAB_NAMES = Object.fromEntries(TABS.map((t) => [t.id, t.label]));

export function Topbar({ activeTab }) {
  const { activeEnvironment } = useDashboardContext();
  const { data: envs } = useBrokerEnvironments();
  const tabName = TAB_NAMES[activeTab] || '';
  const isLive = activeEnvironment === 'LIVE';

  // Balance directo del broker (fuente de verdad), no de agentData
  const envState = envs?.environments?.find((e) => e.environment === activeEnvironment);
  const balance = envState?.balance;

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

        {/* Environment Selector (DEMO / LIVE visualización) */}
        <EnvironmentSelector />

        {/* Balance del env activo (desde broker, no desde agentData) */}
        <div className="text-right hidden sm:block">
          <div className="text-[11px] text-fm-text-dim leading-tight">
            Balance {isLive ? 'REAL' : 'DEMO'}
          </div>
          <div
            className={`text-sm font-semibold font-mono tabular-nums ${
              isLive ? 'text-fm-danger' : 'text-fm-text'
            }`}
          >
            {balance != null ? `$${balance.toFixed(2)}` : '—'}
          </div>
        </div>
      </div>
    </header>
  );
}
