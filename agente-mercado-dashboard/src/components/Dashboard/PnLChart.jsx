import { motion } from 'framer-motion';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  const data = payload[0].payload;
  return (
    <div className="bg-fm-surface border border-fm-border rounded-lg p-3 shadow-fm-lg">
      <p className="text-xs text-fm-text-dim mb-2">{label}</p>
      <div className="space-y-1">
        <div className="flex justify-between gap-6">
          <span className="text-xs text-fm-text-2">Capital</span>
          <span className="text-xs font-semibold text-fm-text font-mono">${data.capital?.toFixed(2)}</span>
        </div>
        <div className="flex justify-between gap-6">
          <span className="text-xs text-fm-text-2">Ganancia</span>
          <span className={`text-xs font-semibold font-mono ${data.pnl >= 0 ? 'text-fm-success' : 'text-fm-danger'}`}>
            {data.pnl >= 0 ? '+' : ''}${data.pnl?.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between gap-6">
          <span className="text-xs text-fm-text-2">Neto</span>
          <span className={`text-xs font-semibold font-mono ${data.net >= 0 ? 'text-fm-success' : 'text-fm-danger'}`}>
            {data.net >= 0 ? '+' : ''}${data.net?.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between gap-6">
          <span className="text-xs text-fm-text-2">Operaciones</span>
          <span className="text-xs text-fm-text font-mono">{data.trades_count}</span>
        </div>
      </div>
    </div>
  );
}

export function PnLChart({ pnlHistory, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-fm-border bg-fm-surface shadow-fm-sm p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-fm-surface-2 rounded w-56 mb-4" />
          <div className="h-64 bg-fm-surface-2 rounded" />
        </div>
      </div>
    );
  }

  const data = pnlHistory?.history || [];
  const hasData = data.some((d) => d.trades_count > 0 || d.pnl !== 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-xl border border-fm-border bg-fm-surface shadow-fm-sm overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-fm-border">
        <h2 className="text-base font-semibold text-fm-text">Capital histórico</h2>
        <p className="text-xs text-fm-text-dim mt-0.5">Últimos 30 días</p>
      </div>

      <div className="p-4">
        {!hasData ? (
          <div className="h-64 flex items-center justify-center">
            <p className="text-fm-text-dim text-sm">
              Los datos del gráfico aparecerán cuando se ejecuten operaciones
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCapital" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#635bff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#635bff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f2" />
              <XAxis
                dataKey="date"
                stroke="#d2d2d7"
                tick={{ fill: '#86868b', fontSize: 11 }}
                tickFormatter={(val) => {
                  const parts = val.split('-');
                  return `${parts[1]}/${parts[2]}`;
                }}
              />
              <YAxis
                stroke="#d2d2d7"
                tick={{ fill: '#86868b', fontSize: 11 }}
                tickFormatter={(val) => `$${val}`}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#635bff', strokeDasharray: '3 3' }} />
              <Area
                type="monotone"
                dataKey="capital"
                stroke="#635bff"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorCapital)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </motion.div>
  );
}
