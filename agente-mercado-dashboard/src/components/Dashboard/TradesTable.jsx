import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChartBarSquareIcon } from '@heroicons/react/24/outline';
import { InfoTooltip } from '../ui/InfoTooltip';
import { TradeChart } from '../TradeChart';

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return (
    d.toLocaleDateString('es', { day: '2-digit', month: 'short' }) +
    ' ' +
    d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
  );
}

export function TradesTable({ trades, loading }) {
  const [chartTradeId, setChartTradeId] = useState(null);
  if (loading) {
    return (
      <div className="rounded-xl border border-fm-border bg-fm-surface shadow-fm-sm p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-fm-surface-2 rounded w-48" />
          <div className="h-4 bg-fm-surface-2 rounded w-full" />
          <div className="h-4 bg-fm-surface-2 rounded w-full" />
          <div className="h-4 bg-fm-surface-2 rounded w-full" />
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-xl border border-fm-border bg-fm-surface shadow-fm-sm overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-fm-border flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-fm-text">Operaciones recientes</h2>
          <p className="text-xs text-fm-text-dim mt-0.5">Historial de trades del agente</p>
        </div>
        <span className="text-xs text-fm-text-2 bg-fm-surface-2 px-2.5 py-1 rounded-full">
          {trades?.length || 0} operaciones
        </span>
      </div>

      {!trades || trades.length === 0 ? (
        <div className="p-10 text-center">
          <p className="text-fm-text-2">No hay operaciones todavía</p>
          <p className="text-xs text-fm-text-dim mt-1">Ejecuta un ciclo para generar operaciones</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-fm-surface-2">
              <tr className="border-b border-fm-border">
                {['Fecha', 'Par', 'Dir.', 'Entrada', 'Tamaño', 'Resultado', 'Estado', 'Chart'].map((h, i) => (
                  <th
                    key={h}
                    className={`px-4 py-3 text-xs font-semibold text-fm-text-2 ${
                      i === 7 ? 'text-center' : 'text-left'
                    }`}
                  >
                    {h === 'Tamaño' ? (
                      <span className="inline-flex items-center">
                        Tamaño
                        <InfoTooltip text="Cuánto dinero se invirtió en esta operación." />
                      </span>
                    ) : (
                      h
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-fm-border">
              <AnimatePresence>
                {trades.slice(0, 15).map((trade, idx) => {
                  const isClosed = trade.status === 'CLOSED';
                  const isWinner = isClosed && trade.pnl > 0;
                  const isLoser = isClosed && trade.pnl !== null && trade.pnl < 0;

                  return (
                    <motion.tr
                      key={trade.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.2, delay: idx * 0.02 }}
                      className="transition-colors hover:bg-fm-surface-2"
                    >
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-xs text-fm-text-dim">{formatDate(trade.created_at)}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-sm font-medium text-fm-text">{trade.symbol}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                            trade.direction === 'BUY'
                              ? 'bg-fm-success-soft text-fm-success'
                              : 'bg-fm-danger-soft text-fm-danger'
                          }`}
                        >
                          {trade.direction === 'BUY' ? 'COMPRA' : 'VENTA'}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-fm-text-2 font-mono tabular-nums">
                        ${trade.entry_price?.toFixed(trade.entry_price >= 1 ? 2 : 6)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-fm-text-2 font-mono tabular-nums">
                        ${trade.size_usd?.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {trade.pnl !== null && trade.pnl !== undefined ? (
                          <span
                            className={`text-sm font-semibold font-mono tabular-nums ${
                              trade.pnl > 0
                                ? 'text-fm-success'
                                : trade.pnl < 0
                                ? 'text-fm-danger'
                                : 'text-fm-text-dim'
                            }`}
                          >
                            {trade.pnl > 0 && '+'}${trade.pnl.toFixed(trade.pnl === 0 ? 2 : 4)}
                          </span>
                        ) : (
                          <span className="text-xs text-fm-text-dim">Esperando TP/SL</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {trade.status === 'OPEN' ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-fm-primary-soft text-fm-primary">
                            <span className="w-1.5 h-1.5 bg-fm-primary rounded-full mr-1.5 animate-pulse" />
                            Abierta
                          </span>
                        ) : isWinner ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-fm-success-soft text-fm-success">
                            Ganada
                          </span>
                        ) : isLoser ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-fm-danger-soft text-fm-danger">
                            Perdida
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-fm-surface-2 text-fm-text-dim">
                            Cerrada
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => setChartTradeId(trade.id)}
                          className="p-1.5 rounded hover:bg-fm-surface-2 transition-colors focus-ring"
                          title="Ver gráfico"
                        >
                          <ChartBarSquareIcon className="w-4 h-4 text-fm-text-dim hover:text-fm-primary" />
                        </button>
                      </td>
                    </motion.tr>
                  );
                })}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      )}

      {chartTradeId && <TradeChart tradeId={chartTradeId} onClose={() => setChartTradeId(null)} />}
    </motion.div>
  );
}
