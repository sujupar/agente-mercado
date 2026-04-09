/**
 * RegimeBanner
 *
 * Banner que muestra el régimen macro actual clasificado por el LLM.
 * Se muestra debajo del header, encima del main content.
 *
 * Estados visuales:
 * - RISK_ON: verde (trending bullish)
 * - RISK_OFF: rojo (flight to safety)
 * - TRANSITION: amarillo (cambiando)
 * - UNCLEAR: gris (sin señal clara)
 */

import { useRegime } from '../hooks/useRegime';

const REGIME_STYLES = {
  RISK_ON: {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    dot: 'bg-emerald-400',
    text: 'text-emerald-300',
    label: 'RISK ON',
  },
  RISK_OFF: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    dot: 'bg-red-400',
    text: 'text-red-300',
    label: 'RISK OFF',
  },
  TRANSITION: {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    dot: 'bg-amber-400',
    text: 'text-amber-300',
    label: 'TRANSITION',
  },
  UNCLEAR: {
    bg: 'bg-gray-500/10',
    border: 'border-gray-500/30',
    dot: 'bg-gray-400',
    text: 'text-gray-300',
    label: 'UNCLEAR',
  },
};

const STRATEGY_LABELS = {
  s1_pullback_20_up: 'S1',
  s2_pullback_20_down: 'S2',
  s3_smc_sensei: 'S3',
  s4_turtle_breakout: 'S4',
  s5_connors_rsi2: 'S5',
};

export function RegimeBanner() {
  const { data: regime, isLoading } = useRegime();

  if (isLoading || !regime) return null;
  if (!regime.enabled) return null;  // no mostrar si el LLM no está configurado

  const style = REGIME_STYLES[regime.regime] || REGIME_STYLES.UNCLEAR;
  const confidencePct = Math.round((regime.confidence || 0) * 100);
  const multiplier = (regime.risk_multiplier || 0).toFixed(1);
  const activeStrats = (regime.active_strategies || []).map(
    (s) => STRATEGY_LABELS[s] || s,
  );

  return (
    <div className={`${style.bg} border-b ${style.border}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center space-x-3">
            <span className={`w-2 h-2 rounded-full ${style.dot} animate-pulse`} />
            <span className={`text-xs font-bold ${style.text}`}>
              {style.label}
            </span>
            <span className="text-[10px] text-gray-500 uppercase">Régimen macro</span>
            <span className={`text-xs ${style.text}`}>
              Confianza: <span className="font-semibold">{confidencePct}%</span>
            </span>
            <span className={`text-xs ${style.text}`}>
              Riesgo: <span className="font-semibold">{multiplier}x</span>
            </span>
            {activeStrats.length > 0 && (
              <span className="text-xs text-gray-400">
                Activas: <span className="font-semibold text-gray-200">{activeStrats.join(', ')}</span>
              </span>
            )}
          </div>
          {regime.reasoning && (
            <p className="text-[11px] text-gray-400 italic max-w-xl truncate" title={regime.reasoning}>
              {regime.reasoning}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
