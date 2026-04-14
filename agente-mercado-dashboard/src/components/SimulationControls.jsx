import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowPathIcon, PlusCircleIcon } from '@heroicons/react/24/outline';
import { api } from '../api/endpoints';

export function SimulationControls({ agentMode, onUpdate }) {
  const [amount, setAmount] = useState(100);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  if (agentMode !== 'SIMULATION') {
    return null;
  }

  const showMessage = (text, type) => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(''), 5000);
  };

  const handleAddCapital = async () => {
    if (amount <= 0) {
      showMessage('La cantidad debe ser mayor a 0', 'warning');
      return;
    }
    setLoading(true);
    try {
      const response = await api.addCapital(amount);
      showMessage(response.data.message, 'success');
      if (onUpdate) onUpdate();
    } catch (error) {
      showMessage(`Error: ${error.response?.data?.detail || error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleForceCycle = async () => {
    setLoading(true);
    showMessage('Ejecutando ciclo... esto puede tomar 2-3 minutos', 'info');
    try {
      await api.forceCycle();
      showMessage('Ciclo completado. Datos actualizándose...', 'success');
      setTimeout(() => { if (onUpdate) onUpdate(); }, 3000);
    } catch (error) {
      showMessage(`Error: ${error.response?.data?.detail || error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const msgClass =
    messageType === 'success' ? 'bg-fm-success-soft border-fm-success/20 text-fm-success'
    : messageType === 'error' ? 'bg-fm-danger-soft border-fm-danger/20 text-fm-danger'
    : messageType === 'warning' ? 'bg-fm-warning-soft border-fm-warning/20 text-fm-warning'
    : 'bg-fm-primary-soft border-fm-primary/20 text-fm-primary';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-xl border border-fm-border bg-fm-surface shadow-fm-sm p-6"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2 bg-fm-primary rounded-full animate-pulse" />
        <h3 className="text-sm font-semibold text-fm-text">Controles de simulación</h3>
        <span className="text-xs text-fm-text-dim">Solo en modo SIMULATION</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-fm-surface-2 rounded-lg p-4">
          <label className="block text-xs text-fm-text-2 mb-2 font-medium">
            Recargar saldo (USD)
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              min="1"
              className="flex-1 bg-fm-surface border border-fm-border rounded-lg px-3 py-2 text-fm-text text-sm focus:outline-none focus:border-fm-primary focus:shadow-fm-focus transition-all"
              disabled={loading}
            />
            <button
              onClick={handleAddCapital}
              disabled={loading}
              className="inline-flex items-center bg-fm-primary hover:bg-fm-primary-hover disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors focus-ring"
            >
              <PlusCircleIcon className="w-4 h-4 mr-1.5" />
              {loading ? '...' : 'Recargar'}
            </button>
          </div>
        </div>

        <div className="bg-fm-surface-2 rounded-lg p-4">
          <label className="block text-xs text-fm-text-2 mb-2 font-medium">
            Ejecutar ciclo manual
          </label>
          <button
            onClick={handleForceCycle}
            disabled={loading}
            className="w-full inline-flex items-center justify-center bg-fm-accent hover:bg-fm-primary disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors focus-ring"
          >
            <ArrowPathIcon className={`w-4 h-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Ejecutando...' : 'Forzar ciclo ahora'}
          </button>
          <p className="text-xs text-fm-text-dim mt-2">
            Ejecuta un ciclo de trading sin esperar el intervalo
          </p>
        </div>
      </div>

      <AnimatePresence>
        {message && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className={`mt-4 p-3 rounded-lg border text-sm ${msgClass}`}
          >
            {message}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
