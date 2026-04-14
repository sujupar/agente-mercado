import { motion } from 'framer-motion';
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';

export function StrategyCard({ strategy, onClick, index }) {
  const pnl = strategy.total_pnl || 0;
  const totalTrades = strategy.trades_won + strategy.trades_lost;
  const winRate = (strategy.win_rate || 0) * 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      onClick={onClick}
      className="relative overflow-hidden rounded-xl border border-fm-border bg-fm-surface shadow-fm-sm hover:shadow-fm-md hover:border-fm-primary/30 cursor-pointer transition-all duration-200"
    >
      <div className="p-5 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="text-fm-text font-semibold text-base truncate">{strategy.name}</h3>
            <p className="text-fm-text-dim text-xs mt-1 line-clamp-2">{strategy.description}</p>
          </div>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold flex-shrink-0 ${
              strategy.enabled
                ? 'bg-fm-success-soft text-fm-success'
                : 'bg-fm-surface-2 text-fm-text-dim'
            }`}
          >
            {strategy.enabled ? 'Activa' : 'Inactiva'}
          </span>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-3 gap-3 pt-2 border-t border-fm-border">
          <div>
            <p className="text-[11px] text-fm-text-dim">Capital</p>
            <p className="text-sm font-semibold text-fm-text font-mono tabular-nums">
              ${strategy.capital_usd?.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-[11px] text-fm-text-dim">P&L</p>
            <p
              className={`text-sm font-semibold font-mono tabular-nums ${
                pnl > 0 ? 'text-fm-success' : pnl < 0 ? 'text-fm-danger' : 'text-fm-text'
              }`}
            >
              {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-[11px] text-fm-text-dim">Win Rate</p>
            <p className="text-sm font-semibold text-fm-text font-mono tabular-nums">
              {winRate.toFixed(0)}%
            </p>
          </div>
        </div>

        {/* Bottom row */}
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-3 text-fm-text-2">
            <span>{totalTrades} trades</span>
            <span>{strategy.positions_open} abiertas</span>
          </div>
          <div>
            {pnl > 0 ? (
              <ArrowTrendingUpIcon className="w-4 h-4 text-fm-success" />
            ) : pnl < 0 ? (
              <ArrowTrendingDownIcon className="w-4 h-4 text-fm-danger" />
            ) : (
              <CurrencyDollarIcon className="w-4 h-4 text-fm-text-dim" />
            )}
          </div>
        </div>

        {/* Improvement cycle */}
        {strategy.improvement_cycle && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-fm-text-2">
                Ciclo #{strategy.improvement_cycle.cycle_number}
              </span>
              <span className="text-fm-text-dim font-mono">
                {strategy.improvement_cycle.trades_in_cycle}/
                {strategy.improvement_cycle.trades_needed}
              </span>
            </div>
            <div className="w-full h-1.5 bg-fm-surface-2 rounded-full overflow-hidden">
              <div
                className="h-full bg-fm-primary rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(
                    (strategy.improvement_cycle.trades_in_cycle /
                      strategy.improvement_cycle.trades_needed) *
                      100,
                    100,
                  )}%`,
                }}
              />
            </div>
            {strategy.active_rules_count > 0 && (
              <p className="text-[11px] text-fm-warning">
                {strategy.active_rules_count} regla{strategy.active_rules_count !== 1 ? 's' : ''}{' '}
                activa{strategy.active_rules_count !== 1 ? 's' : ''}
              </p>
            )}
          </div>
        )}

        {/* Status text */}
        {strategy.status_text && (
          <div className="bg-fm-surface-2 rounded-lg p-2.5">
            <p className="text-xs text-fm-text-2 italic">{strategy.status_text}</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
