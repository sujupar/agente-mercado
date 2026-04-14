/**
 * AccountSelector — Toggle DEMO/LIVE del broker con switch en runtime.
 *
 * Al cambiar a LIVE muestra modal de confirmación con checkbox de riesgos.
 * La mutación llama al backend que reconecta el singleton sin restart.
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-tv-panel border-2 border-tv-down/60 rounded-xl max-w-md w-full shadow-2xl shadow-tv-down/20"
      >
        <div className="flex items-center gap-2 px-5 py-3 border-b border-tv-down/30">
          <ExclamationTriangleIcon className="w-5 h-5 text-tv-down" />
          <h3 className="text-sm font-bold text-tv-down">
            Cambiar a CUENTA REAL
          </h3>
          <button
            onClick={onCancel}
            className="ml-auto p-1 rounded hover:bg-tv-panel-2"
          >
            <XMarkIcon className="w-4 h-4 text-tv-text-dim" />
          </button>
        </div>

        <div className="p-5 space-y-3">
          <p className="text-sm text-tv-text">
            Estas a punto de operar con <strong className="text-tv-down">DINERO REAL</strong>.
            Estas son las implicaciones:
          </p>

          <ul className="text-xs text-tv-text-dim space-y-1.5 ml-4 list-disc">
            <li>Las ordenes se ejecutaran con fondos reales de Capital.com.</li>
            <li>El bot puede abrir trades en los proximos 60 segundos.</li>
            <li>Solo la estrategia S1 Pullback EMA20 operara en LIVE.</li>
            <li>Maximo 1 posicion abierta simultanea (vs 3 en demo).</li>
            <li>Los stop loss reales aplican con posible slippage en news.</li>
          </ul>

          <label className="flex items-start gap-2 cursor-pointer mt-4">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              className="mt-0.5 accent-tv-down"
            />
            <span className="text-xs text-tv-text">
              Entiendo los riesgos y autorizo el cambio a cuenta real
            </span>
          </label>
        </div>

        <div className="flex gap-2 px-5 py-3 border-t border-tv-border">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 px-4 py-2 rounded-md text-sm font-medium text-tv-text-dim hover:text-tv-text hover:bg-tv-panel-2 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={!checked || isLoading}
            className="flex-1 px-4 py-2 rounded-md text-sm font-bold bg-tv-down text-white hover:bg-tv-down/90 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Cambiando...' : 'CAMBIAR A LIVE'}
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
      // Cambiar a DEMO no requiere confirmación
      setEnv.mutate(
        { environment: 'DEMO', confirm_live: false },
        {
          onError: (e) => setError(e.response?.data?.detail || e.message),
        },
      );
    } else {
      // Cambiar a LIVE requiere modal
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
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-tv-panel-2 border border-tv-border">
        <div className="w-1.5 h-1.5 rounded-full bg-tv-text-dim animate-pulse" />
        <span className="text-[11px] text-tv-text-dim">Cargando...</span>
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center gap-2">
        <button
          onClick={handleToggle}
          disabled={setEnv.isPending}
          title={`Cambiar a ${isLive ? 'DEMO' : 'LIVE'}`}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border transition-all disabled:opacity-50 ${
            isLive
              ? 'bg-tv-down/15 border-tv-down/40 text-tv-down hover:bg-tv-down/20'
              : 'bg-tv-blue/15 border-tv-blue/40 text-tv-blue hover:bg-tv-blue/20'
          }`}
        >
          {isLive ? (
            <ExclamationTriangleIcon className="w-3.5 h-3.5" />
          ) : (
            <ShieldCheckIcon className="w-3.5 h-3.5" />
          )}
          <span className="text-[11px] font-bold tracking-wider">
            {setEnv.isPending ? '...' : currentEnv}
          </span>
          {envData?.connected && (
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isLive ? 'bg-tv-down animate-pulse' : 'bg-tv-blue animate-pulse'
              }`}
            />
          )}
        </button>

        {error && (
          <div className="text-[10px] text-tv-down max-w-xs truncate" title={error}>
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
