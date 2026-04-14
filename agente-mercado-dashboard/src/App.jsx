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
import { TABS } from './components/Layout/navConfig';
import { DashboardProvider } from './context/DashboardContext';
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
      bg: 'bg-tv-accent/10 border-tv-accent/30',
      text: 'text-tv-accent',
    },
    SIMULATION: {
      icon: InformationCircleIcon,
      bg: 'bg-tv-blue/10 border-tv-blue/30',
      text: 'text-tv-blue',
    },
    SHUTDOWN: {
      icon: XCircleIcon,
      bg: 'bg-tv-down/10 border-tv-down/30',
      text: 'text-tv-down',
    },
  };

  const c = config[status] || config.SIMULATION;
  const Icon = c.icon;

  return (
    <div className={`border rounded-lg p-3 flex items-start gap-2 ${c.bg}`}>
      <Icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${c.text}`} />
      <div className="flex-1">
        <div className={`text-xs font-semibold ${c.text}`}>{status}</div>
        {reason && <div className="text-xs text-tv-text-dim mt-0.5">{reason}</div>}
      </div>
    </div>
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
      <div className="min-h-[100dvh] bg-tv-bg flex items-center justify-center">
        <div className="bg-tv-panel border border-tv-border p-8 rounded-xl shadow-2xl max-w-md w-full">
          <h2 className="text-2xl font-bold text-tv-text mb-4">Login Requerido</h2>
          <p className="text-tv-text-dim mb-6 text-sm">
            El agente esta en modo LIVE. Necesitas autenticarte para continuar.
          </p>
          <button
            onClick={() => alert('Login no implementado aun')}
            className="w-full bg-tv-blue hover:bg-tv-blue/90 text-white font-semibold py-2.5 px-4 rounded-md transition-colors"
          >
            Iniciar Sesion
          </button>
        </div>
      </div>
    );
  }

  if (loadingAgent) {
    return (
      <div className="min-h-[100dvh] bg-tv-bg flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-2 border-tv-blue/20" />
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-tv-blue animate-spin" />
          </div>
          <p className="text-tv-text-dim text-sm">Conectando con el agente...</p>
        </div>
      </div>
    );
  }

  if (agentError) {
    return (
      <div className="min-h-[100dvh] bg-tv-bg flex items-center justify-center">
        <div className="bg-tv-down/10 border border-tv-down/30 rounded-xl p-8 max-w-md text-center">
          <XCircleIcon className="w-12 h-12 text-tv-down mx-auto mb-3" />
          <h3 className="text-tv-down font-semibold text-lg mb-2">Error de Conexion</h3>
          <p className="text-tv-text-dim text-sm mb-4">
            No se pudo conectar con el backend
          </p>
          <button
            onClick={() => window.location.reload()}
            className="bg-tv-down/20 hover:bg-tv-down/30 text-tv-down text-sm font-semibold py-2 px-6 rounded-md border border-tv-down/30 transition-colors"
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
    <div className="min-h-[100dvh] bg-tv-bg text-tv-text pb-20 md:pb-0">
      {/* Layout principal: sidebar (desktop) + main area */}
      <div className="flex min-h-[100dvh]">
        {/* Sidebar desktop */}
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          lastCycle={lastCycle}
          mode={agentData?.mode}
        />

        {/* Main area con topbar sticky */}
        <div className="flex-1 flex flex-col min-w-0">
          <Topbar agentData={agentData} mode={agentData?.mode} />

          {/* Regime Banner (slim) */}
          <RegimeBanner />

          {/* Contenido principal */}
          <main className="flex-1 px-3 md:px-4 py-3 md:py-4 space-y-3 md:space-y-4 max-w-[1600px] w-full mx-auto">
            {activeTab === 'dashboard' && (
              <>
                <SurvivalBanner
                  status={agentData?.survival_status}
                  reason={agentData?.survival_reason}
                />
                {/* Split-view: Stats + Chart, Capital + Signals, Trades full */}
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-3 md:gap-4">
                  <div className="xl:col-span-2">
                    <PnLChart pnlHistory={pnlHistory} loading={loadingPnL} />
                  </div>
                  <div>
                    <StatsCards agentData={agentData} orientation="vertical" />
                  </div>
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-3 gap-3 md:gap-4">
                  <div className="xl:col-span-2">
                    <CapitalBreakdown agentData={agentData} />
                  </div>
                  <div>
                    <SignalsPanel signals={signals} loading={loadingSignals} />
                  </div>
                </div>

                <TradesTable trades={trades} loading={loadingTrades} />

                <SimulationControls agentMode={agentData?.mode} onUpdate={handleUpdate} />
              </>
            )}
            {activeTab === 'strategies' && <StrategiesPage />}
            {activeTab === 'broker' && <BrokerPage />}
            {activeTab === 'learning' && <LearningPage />}
          </main>
        </div>
      </div>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-tv-bg/95 backdrop-blur-xl border-t border-tv-border pb-[env(safe-area-inset-bottom)]">
        <div className="flex justify-around items-center h-16">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex flex-col items-center justify-center flex-1 h-full transition-colors ${
                activeTab === id ? 'text-tv-blue' : 'text-tv-text-dim'
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
        <DashboardContent />
      </DashboardProvider>
    </QueryClientProvider>
  );
}
