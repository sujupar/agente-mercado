import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import {
  ExclamationTriangleIcon,
  XCircleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';

import { SimulationControls } from './components/SimulationControls';
import { RegimeBanner } from './components/RegimeBanner';
import { CapitalBreakdown } from './components/Dashboard/CapitalBreakdown';
import { StatsCards } from './components/Dashboard/StatsCards';
import { TradesTable } from './components/Dashboard/TradesTable';
import { SignalsPanel } from './components/Dashboard/SignalsPanel';
import { PnLChart } from './components/Dashboard/PnLChart';
import { LearningPage } from './components/Learning/LearningPage';
import { StrategiesPage } from './components/Strategies/StrategiesPage';
import { BrokerPage } from './components/Broker/BrokerPage';
import { Sidebar } from './components/Layout/Sidebar';
import { Topbar } from './components/Layout/Topbar';
import { PageHeader } from './components/Layout/PageHeader';
import { TABS } from './components/Layout/navConfig';
import { DateFilter } from './components/DateFilter';
import { DashboardProvider, useDashboardContext } from './context/DashboardContext';
import { SidebarProvider } from './context/SidebarContext';
import { useAgentData } from './hooks/useAgentData';
import { usePnLHistory } from './hooks/usePnLHistory';
import { useSignals } from './hooks/useSignals';
import { useTrades } from './hooks/useTrades';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,
      retry: 2,
    },
  },
});

function SurvivalBanner({ status, reason }) {
  if (!status || status === 'CONTINUE') return null;

  const config = {
    WARNING: {
      icon: ExclamationTriangleIcon,
      classes: 'bg-fm-warning-soft border-fm-warning/30 text-fm-warning',
    },
    SIMULATION: {
      icon: InformationCircleIcon,
      classes: 'bg-fm-primary-soft border-fm-primary/20 text-fm-primary',
    },
    SHUTDOWN: {
      icon: XCircleIcon,
      classes: 'bg-fm-danger-soft border-fm-danger/30 text-fm-danger',
    },
  };

  const c = config[status] || config.SIMULATION;
  const Icon = c.icon;

  return (
    <div className={`border rounded-lg p-3 flex items-start gap-2 ${c.classes}`}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <div className="text-sm font-semibold">{status}</div>
        {reason && <div className="text-xs mt-0.5 opacity-90">{reason}</div>}
      </div>
    </div>
  );
}

function DashboardTab({ agentData, pnlHistory, loadingPnL, trades, loadingTrades, signals, loadingSignals, handleUpdate }) {
  const { globalFromDate, globalToDate, setGlobalDate } = useDashboardContext();

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Métricas globales y rendimiento consolidado del agente."
        actions={
          <DateFilter
            fromDate={globalFromDate}
            toDate={globalToDate}
            onChange={setGlobalDate}
            size="sm"
          />
        }
      />

      <SurvivalBanner status={agentData?.survival_status} reason={agentData?.survival_reason} />

      <RegimeBanner />

      <StatsCards agentData={agentData} />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-2">
          <PnLChart pnlHistory={pnlHistory} loading={loadingPnL} />
        </div>
        <div>
          <SignalsPanel signals={signals} loading={loadingSignals} />
        </div>
      </div>

      <CapitalBreakdown agentData={agentData} />

      <TradesTable trades={trades} loading={loadingTrades} />

      <SimulationControls agentMode={agentData?.mode} onUpdate={handleUpdate} />
    </>
  );
}

function DashboardContent() {
  const [needsAuth, setNeedsAuth] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  const { data: agentData, isLoading: loadingAgent, error: agentError, refetch: refetchAgent } = useAgentData();
  const { data: pnlHistory, isLoading: loadingPnL } = usePnLHistory(30);
  const { data: trades, isLoading: loadingTrades, refetch: refetchTrades } = useTrades({ limit: 20 });
  const { data: signals, isLoading: loadingSignals, refetch: refetchSignals } = useSignals(20);

  const handleUpdate = () => {
    refetchAgent();
    refetchTrades();
    refetchSignals();
  };

  useEffect(() => {
    const handleAuthError = () => {
      if (agentData?.mode === 'LIVE') {
        setNeedsAuth(true);
      }
    };
    window.addEventListener('auth-error', handleAuthError);
    return () => window.removeEventListener('auth-error', handleAuthError);
  }, [agentData?.mode]);

  if (needsAuth && agentData?.mode === 'LIVE') {
    return (
      <div className="min-h-screen bg-fm-bg flex items-center justify-center p-6">
        <div className="bg-fm-surface border border-fm-border shadow-fm-lg p-8 rounded-2xl max-w-md w-full">
          <h2 className="text-2xl font-semibold text-fm-text mb-3">Login requerido</h2>
          <p className="text-fm-text-2 mb-6 text-sm">
            El agente está en modo LIVE. Necesitas autenticarte para continuar.
          </p>
          <button
            onClick={() => alert('Login no implementado aun')}
            className="w-full bg-fm-primary hover:bg-fm-primary-hover text-white font-semibold py-2.5 px-4 rounded-lg transition-colors focus-ring"
          >
            Iniciar sesión
          </button>
        </div>
      </div>
    );
  }

  if (loadingAgent) {
    return (
      <div className="min-h-screen bg-fm-bg flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-12 h-12 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-2 border-fm-border" />
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-fm-primary animate-spin" />
          </div>
          <p className="text-fm-text-2 text-sm">Conectando con el agente...</p>
        </div>
      </div>
    );
  }

  if (agentError) {
    return (
      <div className="min-h-screen bg-fm-bg flex items-center justify-center p-6">
        <div className="bg-fm-surface border border-fm-danger/30 shadow-fm-lg rounded-2xl p-8 max-w-md text-center">
          <XCircleIcon className="w-12 h-12 text-fm-danger mx-auto mb-3" />
          <h3 className="text-fm-text font-semibold text-lg mb-2">Error de conexión</h3>
          <p className="text-fm-text-2 text-sm mb-5">
            No se pudo conectar con el backend.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="bg-fm-danger hover:bg-fm-danger/90 text-white text-sm font-semibold py-2.5 px-6 rounded-lg transition-colors focus-ring"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const lastCycle = agentData?.last_cycle_at
    ? new Date(agentData.last_cycle_at).toLocaleString('es', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : 'Nunca';

  return (
    <div className="min-h-screen bg-fm-bg text-fm-text pb-20 md:pb-0">
      <div className="flex min-h-screen">
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          lastCycle={lastCycle}
          mode={agentData?.mode}
        />

        <div className="flex-1 flex flex-col min-w-0">
          <Topbar agentData={agentData} mode={agentData?.mode} activeTab={activeTab} />

          <main className="flex-1 px-5 md:px-8 py-6 md:py-8 space-y-5 max-w-[1400px] w-full mx-auto">
            {activeTab === 'dashboard' && (
              <DashboardTab
                agentData={agentData}
                pnlHistory={pnlHistory}
                loadingPnL={loadingPnL}
                trades={trades}
                loadingTrades={loadingTrades}
                signals={signals}
                loadingSignals={loadingSignals}
                handleUpdate={handleUpdate}
              />
            )}
            {activeTab === 'strategies' && <StrategiesPage />}
            {activeTab === 'broker' && <BrokerPage />}
            {activeTab === 'learning' && <LearningPage />}
          </main>
        </div>
      </div>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-fm-surface/95 backdrop-blur-xl border-t border-fm-border pb-[env(safe-area-inset-bottom)]">
        <div className="flex justify-around items-center h-16">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
                activeTab === id ? 'text-fm-primary' : 'text-fm-text-dim'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px] mt-1 font-medium">{label}</span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DashboardProvider>
        <SidebarProvider>
          <DashboardContent />
        </SidebarProvider>
      </DashboardProvider>
    </QueryClientProvider>
  );
}
