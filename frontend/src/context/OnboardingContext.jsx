import { createContext, useContext, useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { SECTION_ORDER, SECTION_CHECKLIST_IDS } from '../config/onboardingTours';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthContext';

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
  const { user } = useAuth();
  const [checked, setCheckedState] = useState(loadChecked);
  const [dbTourCompleted, setDbTourCompleted] = useState(false);
  // null = not running; string = section to start from (triggers OnboardingTour)
  const [tourStartSection, setTourStartSection] = useState(null);
  
  // Ref to prevent spamming backend when already updating
  const isUpdatingBackend = useRef(false);

  // Fetch db status on mount
  useEffect(() => {
    if (!user) return;
    const fetchStatus = async () => {
      const { data } = await supabase
        .from('manager_profiles')
        .select('tour_completed')
        .eq('user_id', user.id)
        .maybeSingle();

      if (data?.tour_completed) {
        setDbTourCompleted(true);
        // Force all local items complete if server says it's done
        const allChecked = {};
        Object.values(SECTION_ITEMS).flat().forEach((id) => { allChecked[id] = true; });
        setCheckedState(allChecked);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(allChecked));
      }
    };
    fetchStatus();
  }, [user]);

  const triggerTour = useCallback((section = 'dashboard') => {
    setTourStartSection(section);
  }, []);

  const clearTourTrigger = useCallback(() => {
    setTourStartSection(null);
  }, []);

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

  // Sync completion to backend when 100% checked locally
  useEffect(() => {
    if (!user || !isChecklistComplete || dbTourCompleted || isUpdatingBackend.current) return;

    const saveCompletion = async () => {
      isUpdatingBackend.current = true;
      try {
        await supabase
          .from('manager_profiles')
          .update({ tour_completed: true })
          .eq('user_id', user.id);
        
        setDbTourCompleted(true);
      } catch (err) {
        console.error('Failed to save tour completion to backend:', err);
        isUpdatingBackend.current = false;
      }
    };
    saveCompletion();
  }, [user, isChecklistComplete, dbTourCompleted]);

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
    tourStartSection,
    triggerTour,
    clearTourTrigger,
    dbTourCompleted,
    SECTION_ORDER,
    SECTION_META,
    SECTION_ITEMS,
  }), [checked, setChecked, toggle, markComplete, reset, isSectionComplete, isSectionUnlocked, isChecklistComplete, totalItems, completedItems, tourStartSection, triggerTour, clearTourTrigger, dbTourCompleted]);

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
