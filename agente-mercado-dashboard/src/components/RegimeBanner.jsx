/**
 * RegimeBanner — variante slim clara (fintech light).
 */

import { useRegime } from '../hooks/useRegime';

const REGIME_STYLES = {
  RISK_ON: {
    bg: 'bg-fm-success-soft',
    border: 'border-fm-success/20',
    dot: 'bg-fm-success',
    text: 'text-fm-success',
    label: 'Mercado favorable',
  },
  RISK_OFF: {
    bg: 'bg-fm-danger-soft',
    border: 'border-fm-danger/20',
    dot: 'bg-fm-danger',
    text: 'text-fm-danger',
    label: 'Mercado defensivo',
  },
  TRANSITION: {
    bg: 'bg-fm-warning-soft',
    border: 'border-fm-warning/20',
    dot: 'bg-fm-warning',
    text: 'text-fm-warning',
    label: 'Mercado en transición',
  },
  UNCLEAR: {
    bg: 'bg-fm-surface-2',
    border: 'border-fm-border',
    dot: 'bg-fm-text-dim',
    text: 'text-fm-text-2',
    label: 'Sin señal clara',
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
    <div className={`rounded-lg border ${style.bg} ${style.border} px-4 py-2.5 flex items-center flex-wrap gap-x-4 gap-y-1 text-xs`}>
      <div className="flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full ${style.dot} animate-pulse`} />
        <span className={`font-semibold ${style.text}`}>{style.label}</span>
      </div>
      <span className="text-fm-text-2">
        Confianza <span className={`font-semibold ${style.text}`}>{confidencePct}%</span>
      </span>
      <span className="text-fm-text-2">
        Riesgo <span className={`font-semibold ${style.text}`}>{multiplier}×</span>
      </span>
      {activeStrats.length > 0 && (
        <span className="text-fm-text-2 hidden sm:inline">
          Activas <span className="font-semibold text-fm-text">{activeStrats.join(', ')}</span>
        </span>
      )}
      {regime.reasoning && (
        <span
          className="text-fm-text-dim italic truncate hidden lg:inline ml-auto max-w-xl"
          title={regime.reasoning}
        >
          {regime.reasoning}
        </span>
      )}
    </div>
  );
}
