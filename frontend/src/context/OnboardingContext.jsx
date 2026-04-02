import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { SECTION_ORDER, SECTION_CHECKLIST_IDS } from '../config/onboardingTours';

const STORAGE_KEY = 'crm-onboarding-checklist';

/** Human-readable section metadata */
const SECTION_META = {
  dashboard:  { label: 'Dashboard',     view: 'dashboard',   description: 'Get familiar with your key metrics and charts' },
  properties: { label: 'Properties',    view: 'properties',  description: 'Learn how to manage property groups, buildings, and units' },
  tenants:    { label: 'Tenants',       view: 'tenants',     description: 'Explore the tenant management table' },
  complaints: { label: 'Complaints',    view: 'complaints',  description: 'See how complaints are tracked and filtered' },
  calendar:   { label: 'Calendar',      view: 'calendar',    description: 'View and manage appointments on the calendar' },
  workflow:   { label: 'SMS Workflow',   view: 'workflow',    description: 'Learn how to send bulk SMS to your tenants' },
};

/** Items within each section — re-exported from tour config as single source of truth */
const SECTION_ITEMS = SECTION_CHECKLIST_IDS;

const OnboardingContext = createContext(null);

function loadChecked() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function OnboardingProvider({ children }) {
  const [checked, setCheckedState] = useState(loadChecked);

  const setChecked = useCallback((updater) => {
    setCheckedState((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const toggle = useCallback((id) => {
    setChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  }, [setChecked]);

  const markComplete = useCallback((ids) => {
    setChecked((prev) => {
      const next = { ...prev };
      ids.forEach((id) => { next[id] = true; });
      return next;
    });
  }, [setChecked]);

  const reset = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setCheckedState({});
  }, []);

  const isSectionComplete = useCallback((sectionId) => {
    const items = SECTION_ITEMS[sectionId] || [];
    return items.every((id) => checked[id]);
  }, [checked]);

  const isSectionUnlocked = useCallback((sectionIndex) => {
    if (sectionIndex === 0) return true;
    for (let i = 0; i < sectionIndex; i++) {
      if (!isSectionComplete(SECTION_ORDER[i])) return false;
    }
    return true;
  }, [isSectionComplete]);

  const totalItems = useMemo(() =>
    Object.values(SECTION_ITEMS).flat().length
  , []);

  const completedItems = useMemo(() =>
    Object.values(SECTION_ITEMS).flat().filter((id) => checked[id]).length
  , [checked]);

  const isChecklistComplete = completedItems === totalItems;

  const value = useMemo(() => ({
    checked,
    setChecked,
    toggle,
    markComplete,
    reset,
    isSectionComplete,
    isSectionUnlocked,
    isChecklistComplete,
    totalItems,
    completedItems,
    SECTION_ORDER,
    SECTION_META,
    SECTION_ITEMS,
  }), [checked, setChecked, toggle, markComplete, reset, isSectionComplete, isSectionUnlocked, isChecklistComplete, totalItems, completedItems]);

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  );
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error('useOnboarding must be used within OnboardingProvider');
  return ctx;
}
