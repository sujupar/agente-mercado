import { motion } from 'framer-motion';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  SignalIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline';
import { useBrokerAccount, useBrokerPositions, useBrokerSync, useForceBrokerSync } from '../../hooks/useBroker';
import { useAllMarketStates } from '../../hooks/useMarketState';

function ConnectionBadge({ connected }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
      connected
        ? 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30'
        : 'bg-red-500/15 text-red-400 ring-1 ring-red-500/30'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
        connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
      }`} />
      {connected ? 'Conectado' : 'Desconectado'}
    </span>
  );
}

function AccountCard({ account, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5 animate-pulse">
        <div className="h-4 bg-gray-800 rounded w-32 mb-4" />
        <div className="grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-800 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!account) return null;

  const stats = [
    { label: 'Balance', value: `$${account.balance?.toFixed(2)}`, color: 'text-white' },
    { label: 'Equity', value: `$${account.equity?.toFixed(2)}`, color: 'text-white' },
    { label: 'P&L No Realizado', value: `$${account.unrealized_pnl?.toFixed(2)}`, color: account.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400' },
    { label: 'Margen Usado', value: `$${account.margin_used?.toFixed(2)}`, color: 'text-amber-400' },
    { label: 'Margen Disponible', value: `$${account.margin_available?.toFixed(2)}`, color: 'text-blue-400' },
    { label: 'Trades Abiertos', value: account.open_trades, color: 'text-white' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-300">Cuenta OANDA</h3>
        <ConnectionBadge connected={account.connected} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {stats.map(({ label, value, color }) => (
          <div key={label} className="bg-gray-800/40 rounded-xl p-3">
            <p className="text-[10px] md:text-xs text-gray-500 mb-1">{label}</p>
            <p className={`text-sm md:text-base font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function PositionCard({ position }) {
  const isBuy = position.direction === 'BUY';
  const pnlColor = position.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400';
  const DirIcon = isBuy ? ArrowTrendingUpIcon : ArrowTrendingDownIcon;

  return (
    <div className="bg-gray-800/40 rounded-xl p-4 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
          isBuy ? 'bg-emerald-500/15' : 'bg-red-500/15'
        }`}>
          <DirIcon className={`w-4 h-4 ${isBuy ? 'text-emerald-400' : 'text-red-400'}`} />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">{position.instrument.replace('_', '/')}</p>
          <p className="text-[10px] text-gray-500">
            {position.units} units @ {position.entry_price}
          </p>
        </div>
      </div>
      <div className="text-right">
        <p className={`text-sm font-bold ${pnlColor}`}>
          {position.unrealized_pnl >= 0 ? '+' : ''}{position.unrealized_pnl?.toFixed(2)}
        </p>
        <p className="text-[10px] text-gray-500">
          SL: {position.stop_loss || '—'} | TP: {position.take_profit || '—'}
        </p>
      </div>
    </div>
  );
}

function PositionsSection({ positions, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5 animate-pulse">
        <div className="h-4 bg-gray-800 rounded w-40 mb-4" />
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-800 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5"
    >
      <h3 className="text-sm font-semibold text-gray-300 mb-4">
        Posiciones Abiertas ({positions?.length || 0})
      </h3>
      {(!positions || positions.length === 0) ? (
        <div className="text-center py-8">
          <SignalIcon className="w-8 h-8 text-gray-700 mx-auto mb-2" />
          <p className="text-xs text-gray-600">Sin posiciones abiertas</p>
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
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-300">Sincronizacion</h3>
        <button
          onClick={onSync}
          disabled={isSyncing}
          className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-500/15 text-blue-400 hover:bg-blue-500/25 transition-colors disabled:opacity-50"
        >
          <ArrowPathIcon className={`w-3.5 h-3.5 mr-1.5 ${isSyncing ? 'animate-spin' : ''}`} />
          Sincronizar
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-8 bg-gray-800 rounded-xl" />
          <div className="h-8 bg-gray-800 rounded-xl" />
        </div>
      ) : syncData ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between bg-gray-800/40 rounded-xl p-3">
            <span className="text-xs text-gray-400">Estado</span>
            <span className={`inline-flex items-center text-xs font-semibold ${
              syncData.is_synced ? 'text-emerald-400' : 'text-amber-400'
            }`}>
              {syncData.is_synced ? (
                <><CheckCircleIcon className="w-4 h-4 mr-1" /> Sincronizado</>
              ) : (
                <><ExclamationTriangleIcon className="w-4 h-4 mr-1" /> Discrepancias</>
              )}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-gray-800/40 rounded-xl p-3">
              <p className="text-[10px] text-gray-500">Trades Locales</p>
              <p className="text-sm font-bold text-white">{syncData.local_open_trades}</p>
            </div>
            <div className="bg-gray-800/40 rounded-xl p-3">
              <p className="text-[10px] text-gray-500">Trades Broker</p>
              <p className="text-sm font-bold text-white">{syncData.broker_open_trades}</p>
            </div>
          </div>
          {syncData.discrepancies?.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs text-amber-400 font-medium">Discrepancias:</p>
              {syncData.discrepancies.map((d, i) => (
                <div key={i} className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-2">
                  <p className="text-[10px] text-amber-300">{d.sync_type}</p>
                  <p className="text-[10px] text-gray-400">Local: {d.local_value} | Broker: {d.broker_value}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <p className="text-xs text-gray-600 text-center py-4">Sin datos de sincronizacion</p>
      )}
    </motion.div>
  );
}

function MarketStateSection({ marketData, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5 animate-pulse">
        <div className="h-4 bg-gray-800 rounded w-40 mb-4" />
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-800 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!marketData) return null;

  const trendColors = {
    UP: 'text-emerald-400 bg-emerald-500/15',
    DOWN: 'text-red-400 bg-red-500/15',
    RANGE: 'text-amber-400 bg-amber-500/15',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-300">Estado del Mercado</h3>
        <div className="flex items-center space-x-2">
          {marketData.market_open ? (
            <span className="text-[10px] text-emerald-400 font-medium">Mercado Abierto</span>
          ) : (
            <span className="text-[10px] text-red-400 font-medium">Mercado Cerrado</span>
          )}
          {marketData.current_session && (
            <span className="text-[10px] bg-blue-500/15 text-blue-400 px-2 py-0.5 rounded-full">
              {marketData.current_session}
            </span>
          )}
        </div>
      </div>

      {(!marketData.instruments || marketData.instruments.length === 0) ? (
        <div className="text-center py-8">
          <SignalIcon className="w-8 h-8 text-gray-700 mx-auto mb-2" />
          <p className="text-xs text-gray-600">
            {marketData.market_open ? 'Cargando datos...' : 'Mercado cerrado — sin datos en tiempo real'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {marketData.instruments.map((inst) => (
            <div key={inst.instrument} className="bg-gray-800/40 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-bold text-white">{inst.instrument.replace('_', '/')}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${trendColors[inst.trend_state] || trendColors.RANGE}`}>
                    {inst.trend_state}
                  </span>
                </div>
                <span className="text-sm font-mono text-white">{inst.price}</span>
              </div>

              {/* Indicators */}
              <div className="grid grid-cols-3 gap-2 mb-3 text-[10px]">
                <div>
                  <span className="text-gray-500">SMA200</span>
                  <span className={`ml-1 font-medium ${inst.price_vs_sma200 === 'ABOVE' ? 'text-emerald-400' : 'text-red-400'}`}>
                    {inst.price_vs_sma200}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">MA State</span>
                  <span className={`ml-1 font-medium ${
                    inst.ma_state === 'WIDE' ? 'text-emerald-400' : inst.ma_state === 'NARROW' ? 'text-amber-400' : 'text-gray-300'
                  }`}>
                    {inst.ma_state}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Trampa</span>
                  <span className={`ml-1 font-medium ${inst.trap_zone ? 'text-red-400' : 'text-emerald-400'}`}>
                    {inst.trap_zone ? 'SI' : 'NO'}
                  </span>
                </div>
              </div>

              {/* Context Filters */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <p className="text-[10px] text-gray-500 mb-1">Filtros LONG</p>
                  <div className="flex flex-wrap gap-1">
                    {inst.filters_long?.map((f) => (
                      <span
                        key={f.name}
                        className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                          f.passed
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : 'bg-red-500/10 text-red-400'
                        }`}
                        title={f.name}
                      >
                        {f.passed ? '\u2713' : '\u2717'}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 mb-1">Filtros SHORT</p>
                  <div className="flex flex-wrap gap-1">
                    {inst.filters_short?.map((f) => (
                      <span
                        key={f.name}
                        className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                          f.passed
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : 'bg-red-500/10 text-red-400'
                        }`}
                        title={f.name}
                      >
                        {f.passed ? '\u2713' : '\u2717'}
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
  const syncMutation = useForceBrokerSync();

  return (
    <div className="space-y-4 md:space-y-6">
      <AccountCard account={account} isLoading={loadingAccount} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
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
  );
}
