/**
 * Full-CRM tour controller — a single Joyride instance that spans all pages.
 * Watches OnboardingContext for a tour trigger, auto-navigates between pages,
 * and ticks off checklist items as each section completes.
 *
 * Mount ONCE at the Dashboard level, outside the key={currentView} motion.div.
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { Joyride, STATUS, EVENTS, ACTIONS } from 'react-joyride';
import { ALL_STEPS, SECTION_CHECKLIST_IDS, SECTION_VIEW, getFirstStepIndex } from '../config/onboardingTours';
import { OnboardingTooltip } from './OnboardingTooltip';
import { useOnboarding } from '../context/OnboardingContext';

export function OnboardingTour({ onNavigate }) {
  const { markComplete, tourStartSection, clearTourTrigger } = useOnboarding();
  const [run, setRun] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const timerRef = useRef(null);
  const retryCountRef = useRef(0);

  // React to tourStartSection changes from context (set by the checklist's "Start Tour" button)
  useEffect(() => {
    if (!tourStartSection) return;

    const idx = getFirstStepIndex(tourStartSection);
    const view = SECTION_VIEW[tourStartSection];

    // Stop any existing tour
    setRun(false);

    // Navigate to the starting page
    onNavigate(view);

    // Set the starting step
    setStepIndex(idx >= 0 ? idx : 0);

    // Wait for the page to mount and data to load, then start
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setRun(true);
      clearTourTrigger(); // Clear trigger AFTER we start, so we don't accidentally cancel the timeout
    }, 1500);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [tourStartSection, onNavigate, clearTourTrigger]);

  const handleCallback = useCallback((data) => {
    const { action, index, status, type } = data;

    // Tour finished or skipped
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRun(false);
      if (status === STATUS.FINISHED) {
        Object.values(SECTION_CHECKLIST_IDS).forEach((ids) => markComplete(ids));
      } else {
        // Mark only visited sections
        const visited = new Set();
        for (let i = 0; i <= index && i < ALL_STEPS.length; i++) {
          visited.add(ALL_STEPS[i].section);
        }
        visited.forEach((sec) => markComplete(SECTION_CHECKLIST_IDS[sec]));
      }
      onNavigate('onboarding');
      return;
    }

    // User closed overlay
    if (action === ACTIONS.CLOSE) {
      setRun(false);
      const visited = new Set();
      for (let i = 0; i <= index && i < ALL_STEPS.length; i++) {
        visited.add(ALL_STEPS[i].section);
      }
      visited.forEach((sec) => markComplete(SECTION_CHECKLIST_IDS[sec]));
      return;
    }

    // Target not found — DOM hasn't settled yet (e.g. framer-motion still animating or data loading).
    // Retry the same step, but bail after 5 attempts to avoid an infinite loop.
    if (type === EVENTS.TARGET_NOT_FOUND) {
      retryCountRef.current += 1;
      if (retryCountRef.current <= 5) {
        setRun(false);
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => setRun(true), 800);
        return;
      }
      // Exceeded retries — reset counter and fall through to advance
      retryCountRef.current = 0;
    }

    // Step completed (or target permanently missing) — advance
    if (type === EVENTS.STEP_AFTER || type === EVENTS.TARGET_NOT_FOUND) {
      retryCountRef.current = 0;
      const nextIndex = index + (action === ACTIONS.PREV ? -1 : 1);

      if (nextIndex < 0 || nextIndex >= ALL_STEPS.length) {
        setRun(false);
        Object.values(SECTION_CHECKLIST_IDS).forEach((ids) => markComplete(ids));
        onNavigate('onboarding');
        return;
      }

      const currentSection = ALL_STEPS[index]?.section;
      const nextSection = ALL_STEPS[nextIndex].section;

      if (nextSection !== currentSection) {
        // Mark the section we're leaving complete (forward only)
        if (action !== ACTIONS.PREV && currentSection) {
          markComplete(SECTION_CHECKLIST_IDS[currentSection]);
        }

        // Navigate to the next page, pause, resume after DOM settles
        setRun(false);
        onNavigate(SECTION_VIEW[nextSection]);
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
          setStepIndex(nextIndex);
          setRun(true);
        }, 1200);
        return;
      }

      // Same page — just advance
      setStepIndex(nextIndex);
    }
  }, [markComplete, onNavigate]);

  return (
    <Joyride
      steps={ALL_STEPS}
      run={run}
      stepIndex={stepIndex}
      continuous
      scrollToFirstStep
      onEvent={handleCallback}
      tooltipComponent={OnboardingTooltip}
      options={{
        overlayClickAction: false,
      }}
      styles={{
        options: {
          zIndex: 10000,
          overlayColor: 'rgba(0, 0, 0, 0.55)',
        },
        spotlight: {
          borderRadius: '0.75rem',
        },
      }}
    />
  );
}
