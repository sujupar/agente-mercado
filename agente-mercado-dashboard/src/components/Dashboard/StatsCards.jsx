import { motion } from 'framer-motion';
import {
  CurrencyDollarIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  BoltIcon,
  SignalIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { InfoTooltip } from '../ui/InfoTooltip';

export function StatsCards({ agentData }) {
  const totalPnl = agentData?.total_pnl || 0;
  const netProfit = agentData?.net_profit || 0;
  const drawdown = agentData?.drawdown_pct || 0;
  const winRate = agentData?.win_rate || 0;

  const stats = [
    {
      title: 'Capital disponible',
      tooltip: 'Dinero libre para abrir nuevas operaciones. El resto está invertido en posiciones abiertas.',
      value: `$${agentData?.capital_usd?.toFixed(2) || '0.00'}`,
      subtitle: `Pico: $${agentData?.peak_capital_usd?.toFixed(2) || '0.00'}`,
      icon: CurrencyDollarIcon,
      accent: 'primary',
    },
    {
      title: 'Ganancia / Pérdida',
      tooltip: 'Cuánto has ganado o perdido en total con todas las operaciones cerradas.',
      value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`,
      subtitle: `Neto (− costos): $${netProfit.toFixed(2)}`,
      icon: ArrowTrendingUpIcon,
      accent: totalPnl >= 0 ? 'success' : 'danger',
    },
    {
      title: 'Tasa de acierto',
      tooltip: 'Porcentaje de operaciones ganadoras. Con R:R 2.0 necesitas ≥33% para break-even.',
      value: `${winRate.toFixed(1)}%`,
      subtitle: `Caída máx: ${(drawdown * 100).toFixed(1)}%`,
      icon: ChartBarIcon,
      accent: winRate >= 50 ? 'success' : winRate >= 33 ? 'warning' : 'danger',
    },
    {
      title: 'Posiciones abiertas',
      tooltip: 'Operaciones activas ahora mismo. Cada una tiene objetivo (TP) y límite de pérdida (SL).',
      value: agentData?.positions_open || 0,
      subtitle: `Total: ${agentData?.trades_executed_total || 0} operaciones`,
      icon: BoltIcon,
      accent: 'accent',
    },
    {
      title: 'Neto 7 días',
      tooltip: 'Ganancias menos costos de la última semana.',
      value: `${(agentData?.net_7d || 0) >= 0 ? '+' : ''}$${agentData?.net_7d?.toFixed(2) || '0.00'}`,
      subtitle: `14 días: $${agentData?.net_14d?.toFixed(2) || '0.00'}`,
      icon: SignalIcon,
      accent: (agentData?.net_7d || 0) >= 0 ? 'success' : 'danger',
    },
    {
      title: 'Uso de IA hoy',
      tooltip: 'Consultas al modelo de IA hoy. Límite: 95/día, 5/minuto.',
      value: `${agentData?.llm_usage?.rpd || 0}/${agentData?.llm_usage?.rpd_limit || 95}`,
      subtitle: `Por minuto: ${agentData?.llm_usage?.rpm || 0}/${agentData?.llm_usage?.rpm_limit || 5}`,
      icon: ClockIcon,
      accent: 'primary',
    },
  ];

  const accentMap = {
    primary: { bg: 'bg-fm-primary-soft', text: 'text-fm-primary' },
    success: { bg: 'bg-fm-success-soft', text: 'text-fm-success' },
    danger: { bg: 'bg-fm-danger-soft', text: 'text-fm-danger' },
    warning: { bg: 'bg-fm-warning-soft', text: 'text-fm-warning' },
    accent: { bg: 'bg-fm-primary-soft', text: 'text-fm-accent' },
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {stats.map((stat, i) => {
        const a = accentMap[stat.accent] || accentMap.primary;
        return (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.04 }}
            className="bg-fm-surface border border-fm-border rounded-xl p-5 shadow-fm-sm hover:shadow-fm-md transition-shadow"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-fm-text-2 inline-flex items-center">
                  {stat.title}
                  <InfoTooltip text={stat.tooltip} />
                </div>
                <div className={`text-2xl font-semibold mt-1 font-mono tabular-nums ${a.text}`}>
                  {stat.value}
                </div>
                <div className="text-xs text-fm-text-dim mt-1">{stat.subtitle}</div>
              </div>
              <div className={`${a.bg} rounded-lg p-2.5 flex-shrink-0`}>
                <stat.icon className={`w-5 h-5 ${a.text}`} />
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
