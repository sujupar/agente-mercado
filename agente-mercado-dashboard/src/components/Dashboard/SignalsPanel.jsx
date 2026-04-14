import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';
import { InfoTooltip } from '../ui/InfoTooltip';

function formatSignalDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return (
    d.toLocaleDateString('es', { day: '2-digit', month: 'short' }) +
    ' ' +
    d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
  );
}

function SignalItem({ signal, index }) {
  const [isOpen, setIsOpen] = useState(false);
  const isBuy = signal.direction === 'BUY';
  const confidencePct = (signal.confidence * 100).toFixed(0);

  const confidenceLabel =
    signal.confidence >= 0.75
      ? 'Muy segura'
      : signal.confidence >= 0.65
      ? 'Segura'
      : signal.confidence >= 0.55
      ? 'Moderada'
      : 'Baja';

  const confColor =
    signal.confidence >= 0.7
      ? 'bg-fm-success'
      : signal.confidence >= 0.5
      ? 'bg-fm-warning'
      : 'bg-fm-danger';
  const confSoft =
    signal.confidence >= 0.7
      ? 'bg-fm-success-soft text-fm-success'
      : signal.confidence >= 0.5
      ? 'bg-fm-warning-soft text-fm-warning'
      : 'bg-fm-danger-soft text-fm-danger';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
      className="border border-fm-border rounded-lg overflow-hidden hover:border-fm-border-strong transition-colors"
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-fm-surface-2 transition-colors focus-ring"
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <span className="text-sm font-semibold text-fm-text">{signal.symbol}</span>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
              isBuy ? 'bg-fm-success-soft text-fm-success' : 'bg-fm-danger-soft text-fm-danger'
            }`}
          >
            {isBuy ? 'COMPRA' : 'VENTA'}
          </span>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="w-14 h-1.5 bg-fm-surface-2 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${confColor}`}
              style={{ width: `${confidencePct}%` }}
            />
          </div>
          <span className="text-xs text-fm-text-2 font-mono w-8 text-right">{confidencePct}%</span>
          <ChevronDownIcon
            className={`w-4 h-4 text-fm-text-dim transition-transform duration-200 ${
              isOpen ? 'rotate-180' : ''
            }`}
          />
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-fm-border"
          >
            <div className="px-4 py-3 space-y-3 bg-fm-surface-2/40">
              <div className="flex items-center gap-2 text-xs">
                <span className={`px-2 py-0.5 rounded-full font-medium ${confSoft}`}>
                  {confidenceLabel} ({confidencePct}%)
                </span>
                <span className="text-fm-text-dim">
                  La IA está {confidencePct}% segura
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="bg-fm-surface rounded-md p-2.5 border border-fm-border">
                  <p className="text-xs text-fm-text-dim">Objetivo</p>
                  <p className="text-sm text-fm-success font-semibold">
                    +{(signal.take_profit_pct * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="bg-fm-surface rounded-md p-2.5 border border-fm-border">
                  <p className="text-xs text-fm-text-dim">Límite</p>
                  <p className="text-sm text-fm-danger font-semibold">
                    -{(signal.stop_loss_pct * 100).toFixed(1)}%
                  </p>
                </div>
              </div>

              <div className="text-xs text-fm-text-dim">
                <span className="font-medium text-fm-text-2">{signal.llm_model}</span>
                {' · '}
                {formatSignalDate(signal.created_at)}
              </div>

              {signal.llm_response_summary && (
                <div className="bg-fm-surface rounded-md p-3 border border-fm-border">
                  <p className="text-xs text-fm-text-dim mb-1 font-medium">Razonamiento</p>
                  <p className="text-sm text-fm-text-2 leading-relaxed">
                    {signal.llm_response_summary}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export function SignalsPanel({ signals, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-fm-border bg-fm-surface shadow-fm-sm p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-fm-surface-2 rounded w-40" />
          <div className="h-16 bg-fm-surface-2 rounded w-full" />
          <div className="h-16 bg-fm-surface-2 rounded w-full" />
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
          <h2 className="text-base font-semibold text-fm-text inline-flex items-center">
            Señales de la IA
            <InfoTooltip text="Ideas de trading que la IA genera. No todas se ejecutan — solo las que cumplen los criterios de riesgo." />
          </h2>
          <p className="text-xs text-fm-text-dim mt-0.5">
            El % indica la confianza del modelo
          </p>
        </div>
        <span className="text-xs text-fm-text-2 bg-fm-surface-2 px-2.5 py-1 rounded-full">
          {signals?.length || 0}
        </span>
      </div>

      <div className="p-4 space-y-2 max-h-[480px] overflow-y-auto">
        {!signals || signals.length === 0 ? (
          <div className="p-6 text-center">
            <p className="text-fm-text-2 text-sm">No hay señales todavía</p>
          </div>
        ) : (
          signals.slice(0, 10).map((signal, index) => (
            <SignalItem key={signal.id} signal={signal} index={index} />
          ))
        )}
      </div>
    </motion.div>
  );
}
