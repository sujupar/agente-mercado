import { useState } from 'react';
import { motion } from 'framer-motion';
import { useStrategies } from '../../hooks/useStrategies';
import { StrategyCard } from './StrategyCard';
import { StrategyDetail } from './StrategyDetail';
import { DateFilter } from '../DateFilter';
import { PageHeader } from '../Layout/PageHeader';
import { useDashboardContext } from '../../context/DashboardContext';

export function StrategiesPage() {
  const { globalFromDate, globalToDate, setGlobalDate } = useDashboardContext();
  const fromDate = globalFromDate;
  const toDate = globalToDate;

  const { data: strategies, isLoading } = useStrategies({ fromDate, toDate });
  const [selectedStrategy, setSelectedStrategy] = useState(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-fm-border border-t-fm-primary rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-fm-text-2">Cargando estrategias...</p>
        </div>
      </div>
    );
  }

  if (!strategies?.length) {
    return (
      <>
        <PageHeader title="Estrategias" description="Estrategias activas del agente" />
        <div className="text-center py-20 bg-fm-surface border border-fm-border rounded-xl">
          <p className="text-fm-text-2">No hay estrategias configuradas</p>
          <p className="text-xs text-fm-text-dim mt-1">
            Las estrategias se crean automáticamente al iniciar el agente
          </p>
        </div>
      </>
    );
  }

  // Detail view
  if (selectedStrategy) {
    const current = strategies.find((s) => s.id === selectedStrategy);
    if (current) {
      return <StrategyDetail strategy={current} onBack={() => setSelectedStrategy(null)} />;
    }
  }

  // Summary stats
  const brokerBalance = strategies.reduce(
    (max, s) => Math.max(max, s.broker_balance || 0),
    0,
  );
  const totalCapital = brokerBalance;
  const totalPnl = strategies.reduce((sum, s) => sum + (s.total_pnl || 0), 0);
  const totalTrades = strategies.reduce(
    (sum, s) => sum + s.trades_won + s.trades_lost,
    0,
  );
  const totalOpen = strategies.reduce((sum, s) => sum + (s.positions_open || 0), 0);

  const metrics = [
    { label: 'Capital total', value: `$${totalCapital.toFixed(2)}`, color: 'text-fm-text' },
    {
      label: 'P&L total',
      value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`,
      color: totalPnl > 0 ? 'text-fm-success' : totalPnl < 0 ? 'text-fm-danger' : 'text-fm-text',
    },
    { label: 'Trades totales', value: totalTrades, color: 'text-fm-text' },
    { label: 'Posiciones abiertas', value: totalOpen, color: 'text-fm-accent' },
  ];

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-5">
      <PageHeader
        title="Estrategias"
        description={`${strategies.length} estrategias configuradas · aprendizaje automático activo`}
        actions={
          <DateFilter
            fromDate={fromDate}
            toDate={toDate}
            onChange={setGlobalDate}
            size="sm"
          />
        }
      />

      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m) => (
          <div
            key={m.label}
            className="bg-fm-surface border border-fm-border rounded-xl p-4 shadow-fm-sm"
          >
            <p className="text-xs text-fm-text-2">{m.label}</p>
            <p className={`text-xl font-semibold font-mono tabular-nums mt-1 ${m.color}`}>
              {m.value}
            </p>
          </div>
        ))}
      </div>

      {/* Strategy grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {strategies.map((strategy, i) => (
          <StrategyCard
            key={strategy.id}
            strategy={strategy}
            index={i}
            onClick={() => setSelectedStrategy(strategy.id)}
          />
        ))}
      </div>
    </motion.div>
  );
}
