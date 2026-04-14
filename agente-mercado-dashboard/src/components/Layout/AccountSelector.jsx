/**
 * AccountSelector — Toggle DEMO/LIVE del broker con confirmación modal.
 * Fintech light style.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import {
  useBrokerEnvironment,
  useSetBrokerEnvironment,
} from '../../hooks/useBrokerEnvironment';

function ConfirmLiveModal({ onConfirm, onCancel, isLoading }) {
  const [checked, setChecked] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <motion.div
        initial={{ scale: 0.96, opacity: 0, y: 10 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.96, opacity: 0 }}
        className="bg-fm-surface border border-fm-border rounded-2xl max-w-lg w-full shadow-fm-lg overflow-hidden"
      >
        <div className="flex items-center gap-3 px-6 py-4 border-b border-fm-border bg-fm-danger-soft">
          <ExclamationTriangleIcon className="w-6 h-6 text-fm-danger" />
          <h3 className="text-base font-semibold text-fm-danger flex-1">
            Cambiar a cuenta real
          </h3>
          <button
            onClick={onCancel}
            className="p-1 rounded hover:bg-white/50 transition-colors focus-ring"
          >
            <XMarkIcon className="w-5 h-5 text-fm-text-2" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <p className="text-sm text-fm-text">
            Estás a punto de operar con{' '}
            <strong className="text-fm-danger">dinero real</strong>. Estas son las implicaciones:
          </p>

          <ul className="text-sm text-fm-text-2 space-y-2">
            {[
              'Las órdenes se ejecutarán con fondos reales de Capital.com',
              'El bot puede abrir trades en los próximos 60 segundos',
              'Solo la estrategia S1 Pullback EMA20 operará en LIVE',
              'Máximo 1 posición abierta simultánea (vs 3 en demo)',
              'Los stop loss reales aplican con posible slippage en noticias',
            ].map((t) => (
              <li key={t} className="flex gap-2">
                <span className="text-fm-danger mt-0.5">•</span>
                <span>{t}</span>
              </li>
            ))}
          </ul>

          <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg bg-fm-surface-2 hover:bg-fm-border/30 transition-colors">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              className="mt-0.5 w-4 h-4 accent-fm-danger"
            />
            <span className="text-sm text-fm-text">
              Entiendo los riesgos y autorizo el cambio a cuenta real
            </span>
          </label>
        </div>

        <div className="flex gap-2 px-6 py-4 border-t border-fm-border bg-fm-surface-2">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-fm-text-2 hover:text-fm-text hover:bg-fm-border/30 transition-colors focus-ring"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={!checked || isLoading}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold bg-fm-danger text-white hover:bg-fm-danger/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors focus-ring"
          >
            {isLoading ? 'Cambiando...' : 'Cambiar a LIVE'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export function AccountSelector() {
  const { data: envData, isLoading: envLoading } = useBrokerEnvironment();
  const setEnv = useSetBrokerEnvironment();
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState(null);

  const currentEnv = envData?.environment || 'DEMO';
  const isLive = currentEnv === 'LIVE';

  const handleToggle = () => {
    setError(null);
    if (isLive) {
      setEnv.mutate(
        { environment: 'DEMO', confirm_live: false },
        { onError: (e) => setError(e.response?.data?.detail || e.message) },
      );
    } else {
      setShowModal(true);
    }
  };

  const handleConfirmLive = () => {
    setError(null);
    setEnv.mutate(
      { environment: 'LIVE', confirm_live: true },
      {
        onSuccess: () => setShowModal(false),
        onError: (e) => {
          setError(e.response?.data?.detail || e.message);
          setShowModal(false);
        },
      },
    );
  };

  if (envLoading) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-fm-surface-2 border border-fm-border">
        <div className="w-2 h-2 rounded-full bg-fm-text-dim animate-pulse" />
        <span className="text-sm text-fm-text-dim">Cargando...</span>
      </div>
    );
  }

  return (
    <>
      <div className="inline-flex items-center gap-3">
        <div className="inline-flex items-center gap-2">
          <span className="text-xs text-fm-text-2">Cuenta</span>
          <button
            onClick={handleToggle}
            disabled={setEnv.isPending}
            title={`Cambiar a ${isLive ? 'DEMO' : 'LIVE'}`}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border font-semibold text-sm transition-all disabled:opacity-50 focus-ring ${
              isLive
                ? 'bg-fm-danger text-white border-fm-danger hover:bg-fm-danger/90 shadow-fm-sm'
                : 'bg-fm-primary-soft text-fm-primary border-fm-primary/30 hover:bg-fm-primary-soft/70'
            }`}
          >
            {isLive ? (
              <ExclamationTriangleIcon className="w-4 h-4" />
            ) : (
              <ShieldCheckIcon className="w-4 h-4" />
            )}
            <span>{setEnv.isPending ? 'Cambiando...' : isLive ? 'REAL' : 'DEMO'}</span>
            {envData?.connected && (
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isLive ? 'bg-white animate-pulse' : 'bg-fm-primary animate-pulse'
                }`}
              />
            )}
          </button>
        </div>

        {error && (
          <div className="text-xs text-fm-danger max-w-xs truncate" title={error}>
            {error}
          </div>
        )}
      </div>

      <AnimatePresence>
        {showModal && (
          <ConfirmLiveModal
            onConfirm={handleConfirmLive}
            onCancel={() => setShowModal(false)}
            isLoading={setEnv.isPending}
          />
        )}
      </AnimatePresence>
    </>
  );
}
