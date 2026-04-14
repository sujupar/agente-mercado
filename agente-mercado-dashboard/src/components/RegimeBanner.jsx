/**
 * RegimeBanner — Variante slim 1 línea (estilo TradingView).
 *
 * Muestra el régimen macro clasificado por el LLM de forma densa,
 * debajo del topbar, encima del main content.
 */

import { useRegime } from '../hooks/useRegime';

const REGIME_STYLES = {
  RISK_ON: {
    bg: 'bg-tv-up/8',
    border: 'border-tv-up/25',
    dot: 'bg-tv-up',
    text: 'text-tv-up',
    label: 'RISK ON',
  },
  RISK_OFF: {
    bg: 'bg-tv-down/8',
    border: 'border-tv-down/25',
    dot: 'bg-tv-down',
    text: 'text-tv-down',
    label: 'RISK OFF',
  },
  TRANSITION: {
    bg: 'bg-tv-accent/8',
    border: 'border-tv-accent/25',
    dot: 'bg-tv-accent',
    text: 'text-tv-accent',
    label: 'TRANSITION',
  },
  UNCLEAR: {
    bg: 'bg-tv-panel-2',
    border: 'border-tv-border',
    dot: 'bg-tv-text-dim',
    text: 'text-tv-text-dim',
    label: 'UNCLEAR',
  },
};

const STRATEGY_LABELS = {
  s1_pullback_20_up: 'S1',
  s2_pullback_20_down: 'S2',
  s3_smc_sensei: 'S3',
  s4_turtle_breakout: 'S4',
  s5_connors_rsi2: 'S5',
  s6_pullback_m5: 'S6',
  s7_double_ema_trend: 'S7',
  s8_rsi_ema_pullback: 'S8',
  s9_momentum_breakout: 'S9',
  s10_session_reversal: 'S10',
};

export function RegimeBanner() {
  const { data: regime, isLoading } = useRegime();

  if (isLoading || !regime) return null;
  if (!regime.enabled) return null;

  const style = REGIME_STYLES[regime.regime] || REGIME_STYLES.UNCLEAR;
  const confidencePct = Math.round((regime.confidence || 0) * 100);
  const multiplier = (regime.risk_multiplier || 0).toFixed(1);
  const activeStrats = (regime.active_strategies || []).map(
    (s) => STRATEGY_LABELS[s] || s,
  );

  return (
    <div className={`${style.bg} border-b ${style.border}`}>
      <div className="px-3 md:px-4 h-7 flex items-center gap-3 text-[11px] max-w-[1600px] w-full mx-auto">
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${style.dot} animate-pulse`} />
          <span className={`font-bold tracking-wider ${style.text}`}>{style.label}</span>
        </div>
        <span className="text-tv-text-dim">
          Conf <span className={`font-semibold ${style.text}`}>{confidencePct}%</span>
        </span>
        <span className="text-tv-text-dim">
          Risk <span className={`font-semibold ${style.text}`}>{multiplier}x</span>
        </span>
        {activeStrats.length > 0 && (
          <span className="text-tv-text-dim hidden sm:inline">
            Activas <span className="font-semibold text-tv-text">{activeStrats.join(', ')}</span>
          </span>
        )}
        {regime.reasoning && (
          <span
            className="text-tv-text-dim italic truncate hidden md:inline ml-auto max-w-xl"
            title={regime.reasoning}
          >
            {regime.reasoning}
          </span>
        )}
      </div>
    </div>
  );
}
