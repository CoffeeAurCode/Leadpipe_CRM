/**
 * Onboarding Checklist — the central hub showing all tutorial sections
 * with progress tracking, sequential unlocking, and navigation.
 */
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Circle, Lock, ChevronDown, ChevronRight, RotateCcw, Sparkles, Play, Rocket } from 'lucide-react';
import { useState } from 'react';
import { useOnboarding } from '../context/OnboardingContext';

export default function OnboardingChecklist() {
  const {
    checked,
    isSectionComplete,
    isSectionUnlocked,
    isChecklistComplete,
    totalItems,
    completedItems,
    reset,
    triggerTour,
    SECTION_ORDER,
    SECTION_META,
    SECTION_ITEMS,
  } = useOnboarding();

  const [expandedSection, setExpandedSection] = useState(
    () => SECTION_ORDER.find((id) => !isSectionComplete(id)) || SECTION_ORDER[0]
  );

  const progressPercent = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

  const startTour = (fromSection = 'dashboard') => {
    triggerTour(fromSection);
  };

  if (isChecklistComplete) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-6">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15 }}
        >
          <Sparkles className="w-16 h-16 text-primary mx-auto" />
        </motion.div>
        <h1 className="text-3xl font-bold text-foreground">You're all set!</h1>
        <p className="text-muted-foreground text-lg">
          You've completed the CRM tour. You're ready to manage your properties like a pro.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => startTour('dashboard')}
            className="px-6 py-2.5 border border-border rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            Replay Tour
          </button>
        </div>
      </div>
    );
  }

  // Find the first incomplete section to start the full tour from
  const firstIncomplete = SECTION_ORDER.find((id) => !isSectionComplete(id)) || 'dashboard';

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Welcome to your CRM</h1>
          <p className="text-muted-foreground mt-1">
            Take a quick tour to learn the key features. It only takes a minute.
          </p>
        </div>
        <button
          onClick={() => startTour(firstIncomplete)}
          className="flex-shrink-0 flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors shadow-sm"
        >
          <Rocket className="w-4 h-4" />
          Start Full Tour
        </button>
      </div>

      {/* Progress bar */}
      <div className="bg-card border border-border rounded-xl p-4 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-foreground">
            {completedItems} of {totalItems} complete
          </span>
          <span className="text-muted-foreground">{progressPercent}%</span>
        </div>
        <div className="w-full bg-secondary rounded-full h-2.5 overflow-hidden">
          <motion.div
            className="h-full bg-primary rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Section cards */}
      <div className="space-y-3">
        {SECTION_ORDER.map((sectionId, index) => {
          const meta = SECTION_META[sectionId];
          const items = SECTION_ITEMS[sectionId];
          const complete = isSectionComplete(sectionId);
          const unlocked = isSectionUnlocked(index);
          const isExpanded = expandedSection === sectionId;

          return (
            <motion.div
              key={sectionId}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`border rounded-xl overflow-hidden transition-colors ${
                complete
                  ? 'border-primary/30 bg-primary/5'
                  : unlocked
                  ? 'border-border bg-card'
                  : 'border-border/50 bg-card/50'
              }`}
            >
              {/* Section header */}
              <button
                onClick={() => unlocked && setExpandedSection(isExpanded ? null : sectionId)}
                disabled={!unlocked}
                className={`w-full flex items-center gap-3 p-4 text-left transition-colors ${
                  unlocked ? 'hover:bg-secondary/50 cursor-pointer' : 'cursor-not-allowed'
                }`}
              >
                {complete ? (
                  <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0" />
                ) : !unlocked ? (
                  <Lock className="w-5 h-5 text-muted-foreground/40 flex-shrink-0" />
                ) : (
                  <Circle className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                )}

                <div className={`flex-1 min-w-0 ${!unlocked ? 'opacity-40' : ''}`}>
                  <div className="font-medium text-foreground text-sm">{meta.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{meta.description}</div>
                </div>

                {unlocked && (
                  <div className="flex-shrink-0">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    )}
                  </div>
                )}
              </button>

              {/* Expanded content */}
              <AnimatePresence>
                {isExpanded && unlocked && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="px-4 pb-4 space-y-3">
                      <div className="space-y-1.5">
                        {items.map((itemId) => (
                          <div key={itemId} className="flex items-center gap-2 text-sm">
                            {checked[itemId] ? (
                              <CheckCircle2 className="w-4 h-4 text-primary" />
                            ) : (
                              <Circle className="w-4 h-4 text-muted-foreground" />
                            )}
                            <span className={checked[itemId] ? 'text-muted-foreground line-through' : 'text-foreground'}>
                              Take the {meta.label.toLowerCase()} tour
                            </span>
                          </div>
                        ))}
                      </div>

                      {!complete && (
                        <button
                          onClick={() => startTour(sectionId)}
                          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                        >
                          <Play className="w-3.5 h-3.5" />
                          Start from here
                        </button>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>

      {/* Reset button */}
      <div className="flex justify-end">
        <button
          onClick={reset}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5"
        >
          <RotateCcw className="w-3 h-3" />
          Reset progress
        </button>
      </div>
    </div>
  );
}
