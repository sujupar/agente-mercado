import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  BookOpenIcon,
  ChartBarIcon,
  ChartBarSquareIcon,
  ClipboardDocumentListIcon,
  AcademicCapIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { TradeChart } from '../TradeChart';
import { PageHeader } from '../Layout/PageHeader';
import {
  useStrategyTrades,
  useStrategyBitacora,
  useStrategyReports,
  useStrategyPerformance,
  useImprovementCycles,
  useImprovementRules,
} from '../../hooks/useStrategies';

function DetailTab({ label, icon: Icon, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-colors focus-ring ${
        active
          ? 'bg-fm-primary-soft text-fm-primary'
          : 'text-fm-text-2 hover:text-fm-text hover:bg-fm-surface-2'
      }`}
    >
      <Icon className="w-3.5 h-3.5" />
      {label}
    </button>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-10">
      <div className="w-6 h-6 border-2 border-fm-border border-t-fm-primary rounded-full animate-spin" />
    </div>
  );
}

function EmptyState({ text }) {
  return (
    <div className="text-center py-10 bg-fm-surface border border-fm-border rounded-xl">
      <p className="text-sm text-fm-text-dim">{text}</p>
    </div>
  );
}

function DirectionPill({ direction }) {
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
        direction === 'BUY'
          ? 'bg-fm-success-soft text-fm-success'
          : 'bg-fm-danger-soft text-fm-danger'
      }`}
    >
      {direction}
    </span>
  );
}

function TradesSection({ strategyId }) {
  const { data: trades, isLoading } = useStrategyTrades(strategyId);
  const [chartTradeId, setChartTradeId] = useState(null);

  if (isLoading) return <LoadingSpinner />;
  if (!trades?.length) return <EmptyState text="Sin trades todavía" />;

  return (
    <>
      <div className="space-y-2">
        {trades.map((t) => (
          <div
            key={t.id}
            className="bg-fm-surface border border-fm-border rounded-lg p-3 cursor-pointer hover:border-fm-primary/30 transition-colors"
            onClick={() => setChartTradeId(t.id)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DirectionPill direction={t.direction} />
                <span className="text-sm font-medium text-fm-text">{t.symbol}</span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-sm font-semibold font-mono tabular-nums ${
                    t.pnl > 0 ? 'text-fm-success' : t.pnl < 0 ? 'text-fm-danger' : 'text-fm-text-dim'
                  }`}
                >
                  {t.pnl != null ? `${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(4)}` : '—'}
                </span>
                <ChartBarSquareIcon className="w-4 h-4 text-fm-text-dim" />
              </div>
            </div>
            <div className="flex items-center justify-between mt-2 text-xs text-fm-text-dim">
              <span>Size: ${t.size_usd?.toFixed(2)}</span>
              <span>
                {t.status === 'OPEN' ? (
                  <span className="text-fm-primary">Abierta</span>
                ) : (
                  new Date(t.closed_at).toLocaleString('es', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                )}
              </span>
            </div>
          </div>
        ))}
      </div>
      {chartTradeId && (
        <TradeChart tradeId={chartTradeId} onClose={() => setChartTradeId(null)} />
      )}
    </>
  );
}

function BitacoraSection({ strategyId }) {
  const { data: entries, isLoading } = useStrategyBitacora(strategyId);

  if (isLoading) return <LoadingSpinner />;
  if (!entries?.length) return <EmptyState text="Sin entradas de bitácora" />;

  return (
    <div className="space-y-3">
      {entries.map((b) => (
        <div
          key={b.id}
          className="bg-fm-surface border border-fm-border rounded-lg p-4 space-y-3 shadow-fm-sm"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <DirectionPill direction={b.direction} />
              <span className="text-sm font-medium text-fm-text">{b.symbol}</span>
            </div>
            <div className="flex items-center gap-2">
              {b.pnl != null && (
                <span
                  className={`text-sm font-semibold font-mono tabular-nums ${
                    b.pnl > 0 ? 'text-fm-success' : 'text-fm-danger'
                  }`}
                >
                  {b.pnl >= 0 ? '+' : ''}${b.pnl.toFixed(4)}
                </span>
              )}
              {b.exit_reason && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    b.exit_reason === 'TAKE_PROFIT'
                      ? 'bg-fm-success-soft text-fm-success'
                      : 'bg-fm-danger-soft text-fm-danger'
                  }`}
                >
                  {b.exit_reason === 'TAKE_PROFIT' ? 'TP' : 'SL'}
                </span>
              )}
            </div>
          </div>

          {b.entry_reasoning && (
            <div className="bg-fm-surface-2 rounded-lg p-3">
              <p className="text-xs text-fm-text-dim font-medium mb-1">Razonamiento</p>
              <p className="text-sm text-fm-text-2">{b.entry_reasoning}</p>
            </div>
          )}

          {b.lesson && (
            <div className="bg-fm-primary-soft border border-fm-primary/15 rounded-lg p-3">
              <p className="text-xs text-fm-primary font-medium mb-1">Lección</p>
              <p className="text-sm text-fm-text-2">{b.lesson}</p>
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-fm-text-dim">
            <span>
              {new Date(b.entry_time).toLocaleString('es', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
            {b.hold_duration_minutes != null && (
              <span>{Math.round(b.hold_duration_minutes)} min</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function ReportsSection({ strategyId }) {
  const { data: reports, isLoading } = useStrategyReports(strategyId);

  if (isLoading) return <LoadingSpinner />;
  if (!reports?.length)
    return <EmptyState text="Sin reportes (se generan cada 15 trades cerrados)" />;

  return (
    <div className="space-y-4">
      {reports.map((r) => (
        <div
          key={r.id}
          className="bg-fm-surface border border-fm-border rounded-lg p-5 shadow-fm-sm space-y-3"
        >
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-fm-text">Reporte #{r.report_number}</h4>
            <span className="text-xs text-fm-text-dim">{r.trades_analyzed} trades</span>
          </div>

          {r.analysis && (
            <div className="bg-fm-surface-2 rounded-lg p-3">
              <p className="text-sm text-fm-text-2 whitespace-pre-wrap leading-relaxed">
                {r.analysis}
              </p>
            </div>
          )}

          {r.recommendations?.length > 0 && (
            <div>
              <p className="text-xs text-fm-text-2 font-medium mb-1">Recomendaciones</p>
              <ul className="space-y-1">
                {r.recommendations.map((rec, i) => (
                  <li key={i} className="text-sm text-fm-text-2 flex gap-2">
                    <span className="text-fm-primary">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {r.stats_snapshot && (
            <div className="grid grid-cols-4 gap-2 pt-3 border-t border-fm-border">
              {[
                ['WR', `${((r.stats_snapshot.win_rate || 0) * 100).toFixed(0)}%`],
                ['PF', (r.stats_snapshot.profit_factor || 0).toFixed(2)],
                ['Sortino', (r.stats_snapshot.sortino || 0).toFixed(2)],
                ['Trades', r.stats_snapshot.total_trades || 0],
              ].map(([label, value]) => (
                <div key={label} className="text-center">
                  <p className="text-xs text-fm-text-dim">{label}</p>
                  <p className="text-sm font-semibold text-fm-text font-mono">{value}</p>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-fm-text-dim">
            {new Date(r.created_at).toLocaleString('es')}
          </p>
        </div>
      ))}
    </div>
  );
}

function PerformanceSection({ strategyId }) {
  const { data: perf, isLoading } = useStrategyPerformance(strategyId);

  if (isLoading) return <LoadingSpinner />;
  if (!perf || !perf.data_sufficient) {
    return (
      <EmptyState text={`Datos insuficientes: ${perf?.total_trades || 0}/30 trades necesarios`} />
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Win Rate', value: `${(perf.win_rate * 100).toFixed(0)}%` },
          { label: 'Profit Factor', value: perf.profit_factor.toFixed(2) },
          { label: 'Sortino', value: perf.sortino_ratio.toFixed(2) },
          { label: 'Expectancy', value: `$${perf.expectancy.toFixed(4)}` },
        ].map((m) => (
          <div
            key={m.label}
            className="bg-fm-surface border border-fm-border rounded-lg p-4 text-center shadow-fm-sm"
          >
            <p className="text-xs text-fm-text-dim">{m.label}</p>
            <p className="text-lg font-semibold text-fm-text font-mono tabular-nums mt-1">
              {m.value}
            </p>
          </div>
        ))}
      </div>

      {perf.best_symbols?.length > 0 && (
        <div>
          <p className="text-sm text-fm-text-2 font-medium mb-2">Mejores símbolos</p>
          <div className="space-y-1.5">
            {perf.best_symbols.map((s) => (
              <div
                key={s.symbol}
                className="flex items-center justify-between bg-fm-surface border border-fm-border rounded-lg px-4 py-2"
              >
                <span className="text-sm text-fm-text font-medium">{s.symbol}</span>
                <div className="flex items-center gap-4 text-sm font-mono">
                  <span className="text-fm-text-2">WR {(s.win_rate * 100).toFixed(0)}%</span>
                  <span
                    className={s.total_pnl >= 0 ? 'text-fm-success' : 'text-fm-danger'}
                  >
                    ${s.total_pnl.toFixed(4)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {perf.recommendations?.length > 0 && (
        <div className="bg-fm-warning-soft border border-fm-warning/20 rounded-lg p-4">
          <p className="text-sm text-fm-warning font-semibold mb-2">Recomendaciones</p>
          {perf.recommendations.map((r, i) => (
            <p key={i} className="text-sm text-fm-text-2 mb-1">
              • {r}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function RulesSection({ strategyId }) {
  const { data: rules, isLoading: loadingRules } = useImprovementRules(strategyId);
  const { data: cycles, isLoading: loadingCycles } = useImprovementCycles(strategyId);

  if (loadingRules || loadingCycles) return <LoadingSpinner />;

  return (
    <div className="space-y-5">
      <div>
        <h4 className="text-sm font-semibold text-fm-text mb-2">
          Reglas permanentes ({rules?.length || 0})
        </h4>
        {!rules?.length ? (
          <EmptyState text="Sin reglas todavía (se generan cada 20 trades cerrados)" />
        ) : (
          <div className="space-y-2">
            {rules.map((r) => (
              <div
                key={r.id}
                className="bg-fm-surface border border-fm-warning/30 rounded-lg p-4 space-y-2 shadow-fm-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-fm-warning">{r.pattern_name}</span>
                  <span className="text-xs text-fm-text-dim">Ciclo #{r.cycle_number}</span>
                </div>
                <p className="text-sm text-fm-text-2">{r.description}</p>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-fm-text-dim">
                  <span>Tipo: {r.rule_type}</span>
                  <span>WR antes: {(r.win_rate_before * 100).toFixed(0)}%</span>
                  <span>{r.trades_before_rule} trades</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h4 className="text-sm font-semibold text-fm-text mb-2">Historial de ciclos</h4>
        {!cycles?.length ? (
          <EmptyState text="Sin ciclos completados" />
        ) : (
          <div className="space-y-2">
            {cycles.map((c) => (
              <div
                key={c.id}
                className="bg-fm-surface border border-fm-border rounded-lg p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-fm-text">
                    Ciclo #{c.cycle_number}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      c.status === 'completed'
                        ? 'bg-fm-success-soft text-fm-success'
                        : c.status === 'analyzing'
                        ? 'bg-fm-warning-soft text-fm-warning'
                        : 'bg-fm-primary-soft text-fm-primary'
                    }`}
                  >
                    {c.status === 'completed'
                      ? 'Completado'
                      : c.status === 'analyzing'
                      ? 'Analizando'
                      : `${c.trades_in_cycle} trades`}
                  </span>
                </div>
                {c.loss_pattern_identified && (
                  <p className="text-xs text-fm-text-2 mt-2">{c.loss_pattern_identified}</p>
                )}
                {c.completed_at && (
                  <p className="text-xs text-fm-text-dim mt-1">
                    {new Date(c.completed_at).toLocaleString('es', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function StrategyDetail({ strategy, onBack }) {
  const [tab, setTab] = useState('bitacora');

  const pnl = strategy.total_pnl || 0;
  const totalTrades = strategy.trades_won + strategy.trades_lost;

  const metrics = [
    { label: 'Capital', value: `$${strategy.capital_usd?.toFixed(2)}`, color: 'text-fm-text' },
    {
      label: 'P&L',
      value: `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`,
      color: pnl > 0 ? 'text-fm-success' : pnl < 0 ? 'text-fm-danger' : 'text-fm-text',
    },
    {
      label: 'Win Rate',
      value: `${(strategy.win_rate * 100).toFixed(0)}%`,
      color: 'text-fm-text',
    },
    { label: 'Trades', value: totalTrades, color: 'text-fm-text' },
    { label: 'Abiertas', value: strategy.positions_open, color: 'text-fm-accent' },
  ];

  return (
    <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} className="space-y-5">
      <PageHeader
        title={strategy.name}
        description={strategy.description}
        onBack={onBack}
      />

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {metrics.map((m) => (
          <div
            key={m.label}
            className="bg-fm-surface border border-fm-border rounded-lg p-3 text-center shadow-fm-sm"
          >
            <p className="text-xs text-fm-text-dim">{m.label}</p>
            <p className={`text-sm font-semibold font-mono tabular-nums mt-0.5 ${m.color}`}>
              {m.value}
            </p>
          </div>
        ))}
      </div>

      <div className="inline-flex gap-1 bg-fm-surface border border-fm-border rounded-xl p-1 overflow-x-auto">
        <DetailTab label="Bitácora" icon={BookOpenIcon} active={tab === 'bitacora'} onClick={() => setTab('bitacora')} />
        <DetailTab label="Reglas" icon={ShieldCheckIcon} active={tab === 'rules'} onClick={() => setTab('rules')} />
        <DetailTab label="Reportes" icon={AcademicCapIcon} active={tab === 'reports'} onClick={() => setTab('reports')} />
        <DetailTab label="Trades" icon={ClipboardDocumentListIcon} active={tab === 'trades'} onClick={() => setTab('trades')} />
        <DetailTab label="Rendimiento" icon={ChartBarIcon} active={tab === 'performance'} onClick={() => setTab('performance')} />
      </div>

      <div>
        {tab === 'bitacora' && <BitacoraSection strategyId={strategy.id} />}
        {tab === 'rules' && <RulesSection strategyId={strategy.id} />}
        {tab === 'reports' && <ReportsSection strategyId={strategy.id} />}
        {tab === 'trades' && <TradesSection strategyId={strategy.id} />}
        {tab === 'performance' && <PerformanceSection strategyId={strategy.id} />}
      </div>
    </motion.div>
  );
}
