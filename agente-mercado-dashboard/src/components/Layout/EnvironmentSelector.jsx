/**
 * EnvironmentSelector — Toggle DEMO/LIVE para visualización.
 *
 * En dual-mode, ambos ambientes corren en paralelo en el backend.
 * Este selector solo filtra los DATOS mostrados en el dashboard.
 * No activa ni desactiva ningún ambiente (esa configuración vive
 * en las env vars de Railway).
 */

import { useDashboardContext } from '../../context/DashboardContext';
import { useBrokerEnvironments } from '../../hooks/useBrokerEnvironments';

export function EnvironmentSelector() {
  const { activeEnvironment, setActiveEnvironment } = useDashboardContext();
  const { data: envs } = useBrokerEnvironments();

  const demoConfigured = envs?.environments?.find((e) => e.environment === 'DEMO')?.configured ?? true;
  const liveConfigured = envs?.environments?.find((e) => e.environment === 'LIVE')?.configured ?? false;
  const demoConnected = envs?.environments?.find((e) => e.environment === 'DEMO')?.connected ?? false;
  const liveConnected = envs?.environments?.find((e) => e.environment === 'LIVE')?.connected ?? false;

  const opts = [
    { value: 'DEMO', label: 'Demo', configured: demoConfigured, connected: demoConnected },
    { value: 'LIVE', label: 'Real', configured: liveConfigured, connected: liveConnected },
  ];

  return (
    <div className="inline-flex items-center gap-1 bg-fm-surface border border-fm-border rounded-lg p-1">
      {opts.map((opt) => {
        const active = activeEnvironment === opt.value;
        const disabled = !opt.configured;
        return (
          <button
            key={opt.value}
            onClick={() => !disabled && setActiveEnvironment(opt.value)}
            disabled={disabled}
            title={
              disabled
                ? `${opt.label} no está configurado en el backend`
                : opt.connected
                ? `${opt.label} · conectado`
                : `${opt.label} · desconectado`
            }
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors focus-ring ${
              active
                ? opt.value === 'LIVE'
                  ? 'bg-fm-danger text-white'
                  : 'bg-fm-primary-soft text-fm-primary ring-1 ring-fm-primary/20'
                : disabled
                ? 'text-fm-text-dim/50 cursor-not-allowed'
                : 'text-fm-text-2 hover:text-fm-text hover:bg-fm-surface-2'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                !opt.configured
                  ? 'bg-fm-text-dim/30'
                  : opt.connected
                  ? active
                    ? 'bg-white animate-pulse'
                    : opt.value === 'LIVE'
                    ? 'bg-fm-danger animate-pulse'
                    : 'bg-fm-success animate-pulse'
                  : 'bg-fm-text-dim'
              }`}
            />
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
