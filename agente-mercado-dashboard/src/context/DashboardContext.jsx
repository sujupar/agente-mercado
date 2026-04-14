/**
 * DashboardContext — Estado global compartido entre páginas del dashboard.
 *
 * Provee:
 * - globalFromDate, globalToDate: fechas del filtro global (default HOY)
 * - setGlobalDate: setter que actualiza ambas fechas
 * - accountType: "DEMO" | "LIVE" (derivado del backend)
 */

import { createContext, useContext, useState, useMemo } from 'react';
import { getTodayRange } from '../components/DateFilter';

const DashboardContext = createContext(null);

export function DashboardProvider({ children }) {
  const todayRange = getTodayRange();
  const [globalFromDate, setGlobalFromDate] = useState(todayRange.from);
  const [globalToDate, setGlobalToDate] = useState(todayRange.to);

  const value = useMemo(
    () => ({
      globalFromDate,
      globalToDate,
      setGlobalDate: (from, to) => {
        setGlobalFromDate(from);
        setGlobalToDate(to);
      },
    }),
    [globalFromDate, globalToDate],
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
