/**
 * Full-CRM tour controller — a single Joyride instance that spans all pages.
 * Listens for "start-tour" custom event, auto-navigates between pages,
 * and ticks off checklist items as each section completes.
 *
 * Mount ONCE at the Dashboard level, outside the key={currentView} motion.div.
 */
import { useState, useCallback, useEffect } from 'react';
import { Joyride, STATUS, EVENTS, ACTIONS } from 'react-joyride';
import { ALL_STEPS, SECTION_CHECKLIST_IDS, SECTION_VIEW, getFirstStepIndex } from '../config/onboardingTours';
import { OnboardingTooltip } from './OnboardingTooltip';
import { useOnboarding } from '../context/OnboardingContext';

export function OnboardingTour({ onNavigate }) {
  const { markComplete } = useOnboarding();
  const [run, setRun] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);

  // Listen for "start-tour" events from the checklist
  useEffect(() => {
    const handler = (e) => {
      const startSection = e.detail?.section || 'dashboard';
      const idx = getFirstStepIndex(startSection);
      const view = SECTION_VIEW[startSection];

      // Navigate to the starting page
      onNavigate(view);

      // Reset state
      setRun(false);
      setStepIndex(idx >= 0 ? idx : 0);

      // Wait for page + data to load, then start
      setTimeout(() => {
        setRun(true);
      }, 1500);
    };

    window.addEventListener('start-tour', handler);
    return () => window.removeEventListener('start-tour', handler);
  }, [onNavigate]);

  const handleCallback = useCallback((data) => {
    const { action, index, status, type } = data;

    // ── Tour ended ──
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRun(false);
      // Mark everything complete on finish, or just visited sections on skip
      if (status === STATUS.FINISHED) {
        Object.values(SECTION_CHECKLIST_IDS).forEach((ids) => markComplete(ids));
      } else {
        for (let i = 0; i <= index && i < ALL_STEPS.length; i++) {
          markComplete(SECTION_CHECKLIST_IDS[ALL_STEPS[i].section]);
        }
      }
      onNavigate('onboarding');
      return;
    }

    // ── User closed ──
    if (action === ACTIONS.CLOSE) {
      setRun(false);
      for (let i = 0; i <= index && i < ALL_STEPS.length; i++) {
        markComplete(SECTION_CHECKLIST_IDS[ALL_STEPS[i].section]);
      }
      return;
    }

    // ── Step completed OR target missing — advance ──
    if (type === EVENTS.STEP_AFTER || type === EVENTS.TARGET_NOT_FOUND) {
      const nextIndex = index + (action === ACTIONS.PREV ? -1 : 1);

      // Bounds check
      if (nextIndex < 0 || nextIndex >= ALL_STEPS.length) return;

      const currentSection = ALL_STEPS[index]?.section;
      const nextSection = ALL_STEPS[nextIndex].section;

      // Cross-page transition needed
      if (nextSection !== currentSection) {
        // Mark section we're leaving as complete (only on forward movement)
        if (action !== ACTIONS.PREV && currentSection) {
          markComplete(SECTION_CHECKLIST_IDS[currentSection]);
        }

        // Pause tour, navigate, wait for DOM, resume
        setRun(false);
        onNavigate(SECTION_VIEW[nextSection]);
        setTimeout(() => {
          setStepIndex(nextIndex);
          setRun(true);
        }, 1200);
        return;
      }

      // Same page — just advance the step index
      setStepIndex(nextIndex);
    }
  }, [markComplete, onNavigate]);

  return (
    <Joyride
      steps={ALL_STEPS}
      run={run}
      stepIndex={stepIndex}
      continuous
      showSkipButton
      scrollToFirstStep
      disableOverlayClose
      spotlightClicks={false}
      callback={handleCallback}
      tooltipComponent={OnboardingTooltip}
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
