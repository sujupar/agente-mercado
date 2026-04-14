import { motion } from 'framer-motion';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  SignalIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline';
import {
  useBrokerAccount,
  useBrokerPositions,
  useBrokerSync,
  useForceBrokerSync,
} from '../../hooks/useBroker';
import { useAllMarketStates } from '../../hooks/useMarketState';
import { useBrokerEnvironment } from '../../hooks/useBrokerEnvironment';
import { AccountSelector } from '../Layout/AccountSelector';
import { PageHeader } from '../Layout/PageHeader';

function ConnectionBadge({ connected }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
        connected ? 'bg-fm-success-soft text-fm-success' : 'bg-fm-danger-soft text-fm-danger'
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
          connected ? 'bg-fm-success animate-pulse' : 'bg-fm-danger'
        }`}
      />
      {connected ? 'Conectado' : 'Desconectado'}
    </span>
  );
}

function AccountCard({ account, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-fm-surface border border-fm-border shadow-fm-sm rounded-xl p-6 animate-pulse">
        <div className="h-4 bg-fm-surface-2 rounded w-32 mb-4" />
        <div className="grid grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 bg-fm-surface-2 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!account) return null;

  const stats = [
    { label: 'Balance', value: `$${account.balance?.toFixed(2)}`, color: 'text-fm-text' },
    { label: 'Equity', value: `$${account.equity?.toFixed(2)}`, color: 'text-fm-text' },
    {
      label: 'P&L no realizado',
      value: `$${account.unrealized_pnl?.toFixed(2)}`,
      color: account.unrealized_pnl >= 0 ? 'text-fm-success' : 'text-fm-danger',
    },
    { label: 'Margen usado', value: `$${account.margin_used?.toFixed(2)}`, color: 'text-fm-warning' },
    {
      label: 'Margen disponible',
      value: `$${account.margin_available?.toFixed(2)}`,
      color: 'text-fm-primary',
    },
    { label: 'Trades abiertos', value: account.open_trades, color: 'text-fm-text' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-fm-surface border border-fm-border shadow-fm-sm rounded-xl p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base font-semibold text-fm-text">Cuenta Capital.com</h3>
        <ConnectionBadge connected={account.connected} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {stats.map(({ label, value, color }) => (
          <div key={label} className="bg-fm-surface-2 rounded-lg p-4">
            <p className="text-xs text-fm-text-2 mb-1">{label}</p>
            <p className={`text-base font-semibold font-mono tabular-nums ${color}`}>{value}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function PositionCard({ position }) {
  const isBuy = position.direction === 'BUY';
  const pnlColor = position.unrealized_pnl >= 0 ? 'text-fm-success' : 'text-fm-danger';
  const DirIcon = isBuy ? ArrowTrendingUpIcon : ArrowTrendingDownIcon;

  return (
    <div className="bg-fm-surface-2 rounded-lg p-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div
          className={`w-9 h-9 rounded-lg flex items-center justify-center ${
            isBuy ? 'bg-fm-success-soft' : 'bg-fm-danger-soft'
          }`}
        >
          <DirIcon className={`w-4 h-4 ${isBuy ? 'text-fm-success' : 'text-fm-danger'}`} />
        </div>
        <div>
          <p className="text-sm font-semibold text-fm-text">
            {position.instrument.replace('_', '/')}
          </p>
          <p className="text-xs text-fm-text-dim">
            {position.units} units @ {position.entry_price}
          </p>
        </div>
      </div>
      <div className="text-right">
        <p className={`text-sm font-semibold font-mono tabular-nums ${pnlColor}`}>
          {position.unrealized_pnl >= 0 ? '+' : ''}
          {position.unrealized_pnl?.toFixed(2)}
        </p>
        <p className="text-xs text-fm-text-dim font-mono">
          SL: {position.stop_loss || '—'} | TP: {position.take_profit || '—'}
        </p>
      </div>
    </div>
  );
}

function PositionsSection({ positions, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-fm-surface border border-fm-border shadow-fm-sm rounded-xl p-6 animate-pulse">
        <div className="h-4 bg-fm-surface-2 rounded w-40 mb-4" />
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-16 bg-fm-surface-2 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 }}
      className="bg-fm-surface border border-fm-border shadow-fm-sm rounded-xl p-6"
    >
      <h3 className="text-base font-semibold text-fm-text mb-4">
        Posiciones abiertas{' '}
        <span className="text-fm-text-dim font-normal">({positions?.length || 0})</span>
      </h3>
      {!positions || positions.length === 0 ? (
        <div className="text-center py-10">
          <SignalIcon className="w-10 h-10 text-fm-text-dim/50 mx-auto mb-2" />
          <p className="text-sm text-fm-text-dim">Sin posiciones abiertas</p>
        </div>
      ) : (
        <div className="space-y-2">
          {positions.map((p) => (
            <PositionCard key={p.trade_id} position={p} />
          ))}
        </div>
      )}
    </motion.div>
  );
}

function SyncSection({ syncData, isLoading, onSync, isSyncing }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-fm-surface border border-fm-border shadow-fm-sm rounded-xl p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-fm-text">Sincronización</h3>
        <button
          onClick={onSync}
          disabled={isSyncing}
          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-fm-primary-soft text-fm-primary hover:bg-fm-primary/15 transition-colors disabled:opacity-50 focus-ring"
        >
          <ArrowPathIcon className={`w-3.5 h-3.5 mr-1.5 ${isSyncing ? 'animate-spin' : ''}`} />
          Sincronizar
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-8 bg-fm-surface-2 rounded-lg" />
          <div className="h-8 bg-fm-surface-2 rounded-lg" />
        </div>
      ) : syncData ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between bg-fm-surface-2 rounded-lg p-3">
            <span className="text-xs text-fm-text-2">Estado</span>
            <span
              className={`inline-flex items-center text-xs font-semibold ${
                syncData.is_synced ? 'text-fm-success' : 'text-fm-warning'
              }`}
            >
              {syncData.is_synced ? (
                <>
                  <CheckCircleIcon className="w-4 h-4 mr-1" /> Sincronizado
                </>
              ) : (
                <>
                  <ExclamationTriangleIcon className="w-4 h-4 mr-1" /> Discrepancias
                </>
              )}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-fm-surface-2 rounded-lg p-3">
              <p className="text-xs text-fm-text-dim">Trades locales</p>
              <p className="text-base font-semibold text-fm-text font-mono">
                {syncData.local_open_trades}
              </p>
            </div>
            <div className="bg-fm-surface-2 rounded-lg p-3">
              <p className="text-xs text-fm-text-dim">Trades broker</p>
              <p className="text-base font-semibold text-fm-text font-mono">
                {syncData.broker_open_trades}
              </p>
            </div>
          </div>
          {syncData.discrepancies?.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs text-fm-warning font-medium">Discrepancias:</p>
              {syncData.discrepancies.map((d, i) => (
                <div
                  key={i}
                  className="bg-fm-warning-soft border border-fm-warning/20 rounded-lg p-2"
                >
                  <p className="text-xs text-fm-warning">{d.sync_type}</p>
                  <p className="text-xs text-fm-text-dim">
                    Local: {d.local_value} | Broker: {d.broker_value}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-fm-text-dim text-center py-4">Sin datos de sincronización</p>
      )}
    </motion.div>
  );
}

function MarketStateSection({ marketData, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-fm-surface border border-fm-border shadow-fm-sm rounded-xl p-6 animate-pulse">
        <div className="h-4 bg-fm-surface-2 rounded w-40 mb-4" />
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-fm-surface-2 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!marketData) return null;

  const trendColors = {
    UP: 'text-fm-success bg-fm-success-soft',
    DOWN: 'text-fm-danger bg-fm-danger-soft',
    RANGE: 'text-fm-warning bg-fm-warning-soft',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="bg-fm-surface border border-fm-border shadow-fm-sm rounded-xl p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base font-semibold text-fm-text">Estado del mercado</h3>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-medium ${
              marketData.market_open ? 'text-fm-success' : 'text-fm-danger'
            }`}
          >
            {marketData.market_open ? 'Mercado abierto' : 'Mercado cerrado'}
          </span>
          {marketData.current_session && (
            <span className="text-xs bg-fm-primary-soft text-fm-primary px-2 py-0.5 rounded-full font-medium">
              {marketData.current_session}
            </span>
          )}
        </div>
      </div>

      {!marketData.instruments || marketData.instruments.length === 0 ? (
        <div className="text-center py-10">
          <SignalIcon className="w-10 h-10 text-fm-text-dim/50 mx-auto mb-2" />
          <p className="text-sm text-fm-text-dim">
            {marketData.market_open
              ? 'Cargando datos...'
              : 'Mercado cerrado — sin datos en tiempo real'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {marketData.instruments.map((inst) => (
            <div key={inst.instrument} className="bg-fm-surface-2 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-fm-text">
                    {inst.instrument.replace('_', '/')}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                      trendColors[inst.trend_state] || trendColors.RANGE
                    }`}
                  >
                    {inst.trend_state}
                  </span>
                </div>
                <span className="text-sm font-mono tabular-nums text-fm-text">{inst.price}</span>
              </div>

              <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
                <div>
                  <span className="text-fm-text-dim">SMA200 </span>
                  <span
                    className={`font-medium ${
                      inst.price_vs_sma200 === 'ABOVE' ? 'text-fm-success' : 'text-fm-danger'
                    }`}
                  >
                    {inst.price_vs_sma200}
                  </span>
                </div>
                <div>
                  <span className="text-fm-text-dim">MA </span>
                  <span
                    className={`font-medium ${
                      inst.ma_state === 'WIDE'
                        ? 'text-fm-success'
                        : inst.ma_state === 'NARROW'
                        ? 'text-fm-warning'
                        : 'text-fm-text-2'
                    }`}
                  >
                    {inst.ma_state}
                  </span>
                </div>
                <div>
                  <span className="text-fm-text-dim">Trampa </span>
                  <span
                    className={`font-medium ${inst.trap_zone ? 'text-fm-danger' : 'text-fm-success'}`}
                  >
                    {inst.trap_zone ? 'Sí' : 'No'}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[11px] text-fm-text-dim mb-1">Filtros LONG</p>
                  <div className="flex flex-wrap gap-1">
                    {inst.filters_long?.map((f) => (
                      <span
                        key={f.name}
                        className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${
                          f.passed
                            ? 'bg-fm-success-soft text-fm-success'
                            : 'bg-fm-danger-soft text-fm-danger'
                        }`}
                        title={f.name}
                      >
                        {f.passed ? '✓' : '✗'}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[11px] text-fm-text-dim mb-1">Filtros SHORT</p>
                  <div className="flex flex-wrap gap-1">
                    {inst.filters_short?.map((f) => (
                      <span
                        key={f.name}
                        className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${
                          f.passed
                            ? 'bg-fm-success-soft text-fm-success'
                            : 'bg-fm-danger-soft text-fm-danger'
                        }`}
                        title={f.name}
                      >
                        {f.passed ? '✓' : '✗'}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

export function BrokerPage() {
  const { data: account, isLoading: loadingAccount } = useBrokerAccount();
  const { data: positions, isLoading: loadingPositions } = useBrokerPositions();
  const { data: syncData, isLoading: loadingSync } = useBrokerSync();
  const { data: marketData, isLoading: loadingMarket } = useAllMarketStates();
  const { data: envData } = useBrokerEnvironment();
  const syncMutation = useForceBrokerSync();

  const isLive = envData?.environment === 'LIVE';

  return (
    <>
      <PageHeader
        title="Broker"
        description={
          isLive
            ? 'Operando con cuenta REAL de Capital.com. Solo S1 ejecuta trades.'
            : 'Operando con cuenta DEMO. Todas las estrategias activas.'
        }
        actions={<AccountSelector />}
      />

      <div className="space-y-5">
        <AccountCard account={account} isLoading={loadingAccount} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <PositionsSection positions={positions} isLoading={loadingPositions} />
          <SyncSection
            syncData={syncData}
            isLoading={loadingSync}
            onSync={() => syncMutation.mutate()}
            isSyncing={syncMutation.isPending}
          />
        </div>

        <MarketStateSection marketData={marketData} isLoading={loadingMarket} />
      </div>
    </>
  );
}
