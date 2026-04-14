import { motion } from 'framer-motion';
import {
  AcademicCapIcon,
  ChartBarIcon,
  AdjustmentsHorizontalIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline';
import { PageHeader } from '../Layout/PageHeader';
import {
  useLearningPerformance,
  useLearningSymbols,
  useLearningAdjustments,
  useLearningLog,
} from '../../hooks/useLearning';

function MetricCard({ label, value, subtext, color = 'text-fm-text', icon: Icon }) {
  return (
    <div className="rounded-xl border border-fm-border bg-fm-surface p-4 shadow-fm-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-fm-text-2">{label}</span>
        {Icon && <Icon className={`w-4 h-4 ${color}`} />}
      </div>
      <div className={`text-xl font-semibold font-mono tabular-nums ${color}`}>{value}</div>
      {subtext && <div className="text-xs text-fm-text-dim mt-0.5">{subtext}</div>}
    </div>
  );
}

function CalibrationBar({ bucket }) {
  const predicted = Math.round(bucket.predicted_win_rate * 100);
  const actual = Math.round(bucket.actual_win_rate * 100);

  return (
    <div className="flex items-center gap-3 py-2 border-b border-fm-border last:border-0">
      <div className="w-24 text-xs text-fm-text-2 shrink-0">{bucket.confidence_range}</div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <div className="flex-1 bg-fm-surface-2 rounded-full h-2 overflow-hidden">
            <div
              className="bg-fm-primary h-full rounded-full"
              style={{ width: `${Math.min(predicted, 100)}%` }}
            />
          </div>
          <span className="text-xs text-fm-primary w-8 text-right font-mono">{predicted}%</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-fm-surface-2 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full ${actual >= predicted ? 'bg-fm-success' : 'bg-fm-danger'}`}
              style={{ width: `${Math.min(actual, 100)}%` }}
            />
          </div>
          <span
            className={`text-xs w-8 text-right font-mono ${actual >= predicted ? 'text-fm-success' : 'text-fm-danger'}`}
          >
            {actual}%
          </span>
        </div>
      </div>
      <div className="w-16 text-right">
        <span className="text-xs text-fm-text-dim">{bucket.trade_count}t</span>
      </div>
    </div>
  );
}

function SymbolRow({ symbol, rank }) {
  const isPositive = symbol.total_pnl > 0;
  return (
    <motion.tr
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: rank * 0.02 }}
      className="border-b border-fm-border hover:bg-fm-surface-2 transition-colors"
    >
      <td className="py-2 px-3 text-sm font-mono text-fm-text">{symbol.symbol}</td>
      <td className="py-2 px-3 text-sm text-center text-fm-text-2">{symbol.total_trades}</td>
      <td className="py-2 px-3 text-sm text-center">
        <span className={symbol.win_rate >= 0.5 ? 'text-fm-success' : 'text-fm-danger'}>
          {Math.round(symbol.win_rate * 100)}%
        </span>
      </td>
      <td className={`py-2 px-3 text-sm text-right font-mono tabular-nums ${isPositive ? 'text-fm-success' : 'text-fm-danger'}`}>
        {isPositive ? '+' : ''}${symbol.total_pnl.toFixed(4)}
      </td>
      <td className="py-2 px-3 text-sm text-right text-fm-text-2 font-mono">
        {symbol.profit_factor === Infinity ? '—' : symbol.profit_factor.toFixed(2)}
      </td>
      <td className="py-2 px-3 text-sm text-right text-fm-text-2 font-mono">
        {Math.round(symbol.avg_hold_minutes)}m
      </td>
    </motion.tr>
  );
}

function AdjustmentCard({ adjustment }) {
  const typeConfig = {
    BLACKLIST_SYMBOL: { icon: XCircleIcon, classes: 'bg-fm-danger-soft text-fm-danger border-fm-danger/20' },
    BOOST_SYMBOL: { icon: CheckCircleIcon, classes: 'bg-fm-success-soft text-fm-success border-fm-success/20' },
    RAISE_MIN_CONFIDENCE: { icon: AdjustmentsHorizontalIcon, classes: 'bg-fm-warning-soft text-fm-warning border-fm-warning/20' },
    DIRECTION_BIAS: { icon: ArrowTrendingUpIcon, classes: 'bg-fm-primary-soft text-fm-primary border-fm-primary/20' },
    AVOID_HOUR: { icon: ClockIcon, classes: 'bg-fm-warning-soft text-fm-warning border-fm-warning/20' },
  };
  const config = typeConfig[adjustment.type] || typeConfig.RAISE_MIN_CONFIDENCE;
  const Icon = config.icon;

  return (
    <div className={`rounded-lg border p-3 ${config.classes}`}>
      <div className="flex items-start gap-3">
        <Icon className="w-5 h-5 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold">
            {adjustment.type.replace(/_/g, ' ')}
            {adjustment.symbol && ` — ${adjustment.symbol}`}
            {adjustment.direction && ` — ${adjustment.direction}`}
            {adjustment.hour >= 0 && adjustment.type === 'AVOID_HOUR' && ` — ${adjustment.hour}:00 UTC`}
          </div>
          <div className="text-xs text-fm-text-2 mt-1">{adjustment.reason}</div>
        </div>
      </div>
    </div>
  );
}

export function LearningPage() {
  const { data: performance, isLoading: perfLoading } = useLearningPerformance();
  const { data: symbols } = useLearningSymbols();
  const { data: adjustments } = useLearningAdjustments();
  const { data: logs } = useLearningLog();

  if (perfLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-fm-border border-t-fm-primary rounded-full animate-spin" />
      </div>
    );
  }

  const hasSufficientData = performance?.data_sufficient !== false;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Sistema de aprendizaje"
        description={
          hasSufficientData
            ? 'Análisis activo. El agente aprende de sus operaciones.'
            : `Recopilando datos... Se necesitan 30+ trades (actual: ${performance?.total_trades || 0}).`
        }
        actions={
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-medium ${
              hasSufficientData ? 'bg-fm-success-soft text-fm-success' : 'bg-fm-warning-soft text-fm-warning'
            }`}
          >
            {performance?.total_trades || 0} trades
          </span>
        }
      />

      {/* Métricas globales */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard
          label="Win Rate"
          value={`${Math.round((performance?.win_rate || 0) * 100)}%`}
          subtext={hasSufficientData ? 'tasa de acierto' : 'datos insuficientes'}
          color={(performance?.win_rate || 0) >= 0.5 ? 'text-fm-success' : 'text-fm-danger'}
          icon={ChartBarIcon}
        />
        <MetricCard
          label="Profit Factor"
          value={performance?.profit_factor === Infinity ? '—' : (performance?.profit_factor || 0).toFixed(2)}
          subtext={
            hasSufficientData
              ? performance?.profit_factor >= 1.5
                ? 'bueno'
                : performance?.profit_factor >= 1
                ? 'aceptable'
                : 'perdiendo'
              : ''
          }
          color={(performance?.profit_factor || 0) >= 1 ? 'text-fm-success' : 'text-fm-danger'}
          icon={ArrowTrendingUpIcon}
        />
        <MetricCard
          label="Sortino"
          value={(performance?.sortino_ratio || 0).toFixed(2)}
          subtext="riesgo bajista"
          color={(performance?.sortino_ratio || 0) > 0 ? 'text-fm-success' : 'text-fm-danger'}
          icon={BeakerIcon}
        />
        <MetricCard
          label="Expectancy"
          value={`$${(performance?.expectancy || 0).toFixed(4)}`}
          subtext="por trade"
          color={(performance?.expectancy || 0) > 0 ? 'text-fm-success' : 'text-fm-danger'}
          icon={ArrowTrendingUpIcon}
        />
        <MetricCard
          label="Trades"
          value={performance?.total_trades || 0}
          subtext="analizados"
          color="text-fm-primary"
          icon={AcademicCapIcon}
        />
      </div>

      {/* BUY vs SELL */}
      {hasSufficientData && (performance?.buy_stats || performance?.sell_stats) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {performance.buy_stats && (
            <div className="rounded-xl border border-fm-border bg-fm-surface p-5 shadow-fm-sm">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-fm-success flex items-center gap-1.5">
                  <ArrowTrendingUpIcon className="w-4 h-4" /> COMPRAS
                </span>
                <span className="text-xs text-fm-text-dim">
                  {performance.buy_stats.total_trades} trades
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-lg font-semibold text-fm-text font-mono tabular-nums">
                    {Math.round(performance.buy_stats.win_rate * 100)}%
                  </div>
                  <div className="text-xs text-fm-text-dim">Win Rate</div>
                </div>
                <div>
                  <div
                    className={`text-lg font-semibold font-mono tabular-nums ${
                      performance.buy_stats.total_pnl >= 0 ? 'text-fm-success' : 'text-fm-danger'
                    }`}
                  >
                    ${performance.buy_stats.total_pnl.toFixed(2)}
                  </div>
                  <div className="text-xs text-fm-text-dim">P&L</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-fm-text font-mono tabular-nums">
                    {performance.buy_stats.profit_factor === Infinity
                      ? '—'
                      : performance.buy_stats.profit_factor.toFixed(1)}
                  </div>
                  <div className="text-xs text-fm-text-dim">PF</div>
                </div>
              </div>
            </div>
          )}
          {performance.sell_stats && (
            <div className="rounded-xl border border-fm-border bg-fm-surface p-5 shadow-fm-sm">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-fm-danger flex items-center gap-1.5">
                  <ArrowTrendingDownIcon className="w-4 h-4" /> VENTAS
                </span>
                <span className="text-xs text-fm-text-dim">
                  {performance.sell_stats.total_trades} trades
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-lg font-semibold text-fm-text font-mono tabular-nums">
                    {Math.round(performance.sell_stats.win_rate * 100)}%
                  </div>
                  <div className="text-xs text-fm-text-dim">Win Rate</div>
                </div>
                <div>
                  <div
                    className={`text-lg font-semibold font-mono tabular-nums ${
                      performance.sell_stats.total_pnl >= 0 ? 'text-fm-success' : 'text-fm-danger'
                    }`}
                  >
                    ${performance.sell_stats.total_pnl.toFixed(2)}
                  </div>
                  <div className="text-xs text-fm-text-dim">P&L</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-fm-text font-mono tabular-nums">
                    {performance.sell_stats.profit_factor === Infinity
                      ? '—'
                      : performance.sell_stats.profit_factor.toFixed(1)}
                  </div>
                  <div className="text-xs text-fm-text-dim">PF</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Calibración */}
      {hasSufficientData && performance?.calibration?.length > 0 && (
        <div className="rounded-xl border border-fm-border bg-fm-surface p-6 shadow-fm-sm">
          <h3 className="text-sm font-semibold text-fm-text mb-1">Calibración de confianza</h3>
          <p className="text-xs text-fm-text-dim mb-4">
            Azul = confianza predicha por el LLM | Verde = LLM subestima, Rojo = LLM sobreestima.
          </p>
          <div className="space-y-1">
            {performance.calibration.map((bucket) => (
              <CalibrationBar key={bucket.confidence_range} bucket={bucket} />
            ))}
          </div>
        </div>
      )}

      {/* Ranking símbolos */}
      <div className="rounded-xl border border-fm-border bg-fm-surface p-6 shadow-fm-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-fm-text">Ranking de símbolos</h3>
          <span className="text-xs text-fm-text-dim">mín. 5 trades por símbolo</span>
        </div>
        {symbols && symbols.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-fm-border">
                  {['Símbolo', 'Trades', 'Win Rate', 'P&L', 'PF', 'Hold'].map((h, i) => (
                    <th
                      key={h}
                      className={`py-2 px-3 text-xs text-fm-text-2 font-semibold ${
                        i === 0 ? 'text-left' : i < 3 ? 'text-center' : 'text-right'
                      }`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {symbols.map((sym, i) => (
                  <SymbolRow key={sym.symbol} symbol={sym} rank={i} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-fm-text-dim text-sm">
            Sin datos suficientes
          </div>
        )}
      </div>

      {/* Ajustes adaptativos */}
      <div className="rounded-xl border border-fm-border bg-fm-surface p-6 shadow-fm-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-fm-text flex items-center gap-2">
            <AdjustmentsHorizontalIcon className="w-4 h-4 text-fm-warning" />
            Ajustes adaptativos
          </h3>
          <span className="text-xs text-fm-text-dim">recalculados cada hora</span>
        </div>
        {adjustments && adjustments.length > 0 ? (
          <div className="space-y-2">
            {adjustments.map((adj, i) => (
              <AdjustmentCard key={i} adjustment={adj} />
            ))}
          </div>
        ) : (
          <div className="text-center py-6 text-fm-text-dim text-sm">
            Sin ajustes activos (se calculan con 30+ trades)
          </div>
        )}
      </div>

      {/* Recomendaciones */}
      {performance?.recommendations?.length > 0 && (
        <div className="rounded-xl border border-fm-warning/30 bg-fm-warning-soft p-5">
          <h3 className="text-sm font-semibold text-fm-warning flex items-center gap-2 mb-3">
            <ExclamationTriangleIcon className="w-4 h-4" />
            Recomendaciones del sistema
          </h3>
          <ul className="space-y-1.5">
            {performance.recommendations.map((rec, i) => (
              <li key={i} className="text-sm text-fm-text-2 flex gap-2">
                <span className="text-fm-warning">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Log */}
      {logs && logs.length > 0 && (
        <div className="rounded-xl border border-fm-border bg-fm-surface p-6 shadow-fm-sm">
          <h3 className="text-sm font-semibold text-fm-text mb-4">Log de aprendizaje</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {logs.map((log) => (
              <div key={log.id} className="flex items-start gap-3 py-2 border-b border-fm-border last:border-0">
                <div className="text-xs text-fm-text-dim w-32 shrink-0">
                  {new Date(log.created_at).toLocaleString('es', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
                <div className="flex-1">
                  <span className="text-xs font-semibold text-fm-primary">
                    {log.adjustment_type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-fm-text-2 ml-2">{log.parameter}</span>
                  <div className="text-xs text-fm-text-dim mt-0.5">{log.reason}</div>
                </div>
                <div className="text-xs text-fm-text-dim">{log.trades_analyzed}t</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
