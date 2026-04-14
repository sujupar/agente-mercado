import { motion } from 'framer-motion';
import {
  BanknotesIcon,
  ArrowTrendingDownIcon,
  LockClosedIcon,
  WalletIcon,
} from '@heroicons/react/24/outline';

export function CapitalBreakdown({ agentData }) {
  const initial = agentData?.initial_capital_usd || 50;
  const available = agentData?.capital_usd || 0;
  const inPositions = agentData?.capital_in_positions || 0;
  const totalPnl = agentData?.total_pnl || 0;
  const positionsOpen = agentData?.positions_open || 0;
  const won = agentData?.trades_won || 0;
  const lost = agentData?.trades_lost || 0;
  const totalTrades = won + lost;
  const cycleMinutes = agentData?.cycle_interval_minutes || 10;

  const totalAccount = available + inPositions;
  const availablePct = totalAccount > 0 ? (available / initial) * 100 : 0;
  const inPositionsPct = totalAccount > 0 ? (inPositions / initial) * 100 : 0;
  const lostPct = totalPnl < 0 ? (Math.abs(totalPnl) / initial) * 100 : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-xl border border-fm-border bg-fm-surface shadow-fm-sm overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-fm-border">
        <h2 className="text-base font-semibold text-fm-text">Dónde está tu dinero</h2>
        <p className="text-xs text-fm-text-dim mt-0.5">
          Desglose de tu capital de ${initial.toFixed(2)}
        </p>
      </div>

      <div className="p-6 space-y-5">
        {/* Barra visual */}
        <div className="space-y-3">
          <div className="flex h-3 rounded-full overflow-hidden bg-fm-surface-2">
            {availablePct > 0 && (
              <div
                className="bg-fm-primary transition-all duration-500"
                style={{ width: `${Math.min(availablePct, 100)}%` }}
              />
            )}
            {inPositionsPct > 0 && (
              <div
                className="bg-fm-accent transition-all duration-500"
                style={{ width: `${Math.min(inPositionsPct, 100)}%` }}
              />
            )}
            {lostPct > 0 && (
              <div
                className="bg-fm-danger/50 transition-all duration-500"
                style={{ width: `${Math.min(lostPct, 100)}%` }}
              />
            )}
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-fm-primary" />
              <span className="text-fm-text-2">Disponible</span>
            </span>
            {inPositionsPct > 0 && (
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-fm-accent" />
                <span className="text-fm-text-2">En posiciones</span>
              </span>
            )}
            {lostPct > 0 && (
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-fm-danger/50" />
                <span className="text-fm-text-2">Perdido</span>
              </span>
            )}
          </div>
        </div>

        {/* Detalle numérico */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { icon: BanknotesIcon, label: 'Capital inicial', value: `$${initial.toFixed(2)}`, color: 'text-fm-text' },
            { icon: WalletIcon, label: 'Disponible', value: `$${available.toFixed(2)}`, color: 'text-fm-primary' },
            {
              icon: LockClosedIcon,
              label: 'En posiciones',
              value: `$${inPositions.toFixed(2)}`,
              sub: positionsOpen > 0 ? `${positionsOpen} ${positionsOpen === 1 ? 'abierta' : 'abiertas'}` : null,
              color: 'text-fm-accent',
            },
            {
              icon: ArrowTrendingDownIcon,
              label: 'Ganado / Perdido',
              value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`,
              color: totalPnl >= 0 ? 'text-fm-success' : 'text-fm-danger',
            },
          ].map(({ icon: Icon, label, value, sub, color }) => (
            <div key={label} className="bg-fm-surface-2 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1.5">
                <Icon className="w-4 h-4 text-fm-text-dim" />
                <span className="text-xs text-fm-text-2">{label}</span>
              </div>
              <p className={`text-lg font-semibold font-mono tabular-nums ${color}`}>
                {value}
                {sub && <span className="text-xs font-normal text-fm-text-dim ml-1.5">{sub}</span>}
              </p>
            </div>
          ))}
        </div>

        {/* Explicación */}
        <div className="bg-fm-surface-2 rounded-lg p-4">
          <p className="text-sm text-fm-text-2 leading-relaxed">
            {totalPnl < 0 && inPositions === 0 && (
              <>
                Empezaste con <span className="text-fm-text font-semibold">${initial.toFixed(2)}</span>. Las operaciones cerradas perdieron{' '}
                <span className="text-fm-danger font-semibold">${Math.abs(totalPnl).toFixed(2)}</span>. Te quedan{' '}
                <span className="text-fm-primary font-semibold">${available.toFixed(2)}</span> disponibles.
                {totalTrades > 0 && <> De {totalTrades} operaciones: {won} ganadas, {lost} perdidas.</>}
              </>
            )}
            {totalPnl < 0 && inPositions > 0 && (
              <>
                Empezaste con <span className="text-fm-text font-semibold">${initial.toFixed(2)}</span>. Tienes{' '}
                <span className="text-fm-accent font-semibold">${inPositions.toFixed(2)}</span> en {positionsOpen} {positionsOpen === 1 ? 'posición abierta' : 'posiciones abiertas'}. Las operaciones cerradas perdieron{' '}
                <span className="text-fm-danger font-semibold">${Math.abs(totalPnl).toFixed(2)}</span>. Te quedan{' '}
                <span className="text-fm-primary font-semibold">${available.toFixed(2)}</span> libres.
              </>
            )}
            {totalPnl >= 0 && inPositions === 0 && (
              <>
                Empezaste con <span className="text-fm-text font-semibold">${initial.toFixed(2)}</span>. Has ganado{' '}
                <span className="text-fm-success font-semibold">+${totalPnl.toFixed(2)}</span>. Tienes{' '}
                <span className="text-fm-primary font-semibold">${available.toFixed(2)}</span> disponibles.
              </>
            )}
            {totalPnl >= 0 && inPositions > 0 && (
              <>
                Empezaste con <span className="text-fm-text font-semibold">${initial.toFixed(2)}</span>. Has ganado{' '}
                <span className="text-fm-success font-semibold">+${totalPnl.toFixed(2)}</span>. Tienes{' '}
                <span className="text-fm-accent font-semibold">${inPositions.toFixed(2)}</span> en {positionsOpen} posiciones abiertas y{' '}
                <span className="text-fm-primary font-semibold">${available.toFixed(2)}</span> libres.
              </>
            )}
          </p>
          <p className="text-xs text-fm-text-dim mt-2">
            El agente revisa precios cada {cycleMinutes} minutos. Si una posición llega a su objetivo (TP) o límite de pérdida (SL), se cierra automáticamente.
          </p>
        </div>
      </div>
    </motion.div>
  );
}
