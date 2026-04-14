/**
 * Configuración de navegación — tabs compartidos entre Sidebar (desktop)
 * y Bottom Nav (mobile).
 */

import {
  ChartBarIcon,
  AcademicCapIcon,
  BeakerIcon,
  BanknotesIcon,
} from '@heroicons/react/24/outline';

export const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: ChartBarIcon },
  { id: 'strategies', label: 'Estrategias', icon: BeakerIcon },
  { id: 'broker', label: 'Broker', icon: BanknotesIcon },
  { id: 'learning', label: 'Aprendizaje', icon: AcademicCapIcon },
];
