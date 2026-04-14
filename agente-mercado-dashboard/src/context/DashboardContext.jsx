/**
 * DashboardContext — Estado global compartido entre páginas del dashboard.
 *
 * Provee:
 * - globalFromDate, globalToDate: fechas del filtro global (default HOY)
 * - setGlobalDate: setter que actualiza ambas fechas
 * - activeEnvironment: "DEMO" | "LIVE" — qué environment mostrar en dashboard
 * - setActiveEnvironment: cambiar environment visible
 */

import { createContext, useContext, useState, useMemo, useEffect } from 'react';
import { getTodayRange } from '../components/DateFilter';

const DashboardContext = createContext(null);

const ENV_KEY = 'agente.active-environment';

export function DashboardProvider({ children }) {
  const todayRange = getTodayRange();
  const [globalFromDate, setGlobalFromDate] = useState(todayRange.from);
  const [globalToDate, setGlobalToDate] = useState(todayRange.to);
  const [activeEnvironment, setActiveEnvironmentState] = useState(() => {
    if (typeof window === 'undefined') return 'DEMO';
    try {
      return window.localStorage.getItem(ENV_KEY) || 'DEMO';
    } catch {
      return 'DEMO';
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(ENV_KEY, activeEnvironment);
    } catch {
      // noop
    }
  }, [activeEnvironment]);

  const value = useMemo(
    () => ({
      globalFromDate,
      globalToDate,
      setGlobalDate: (from, to) => {
        setGlobalFromDate(from);
        setGlobalToDate(to);
      },
      activeEnvironment,
      setActiveEnvironment: (env) => {
        const normalized = (env || 'DEMO').toUpperCase();
        if (normalized === 'DEMO' || normalized === 'LIVE') {
          setActiveEnvironmentState(normalized);
        }
      },
    }),
    [globalFromDate, globalToDate, activeEnvironment],
  );

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboardContext() {
  const ctx = useContext(DashboardContext);
  if (!ctx) {
    throw new Error('useDashboardContext debe usarse dentro de DashboardProvider');
  }
  return ctx;
}
