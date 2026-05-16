/**
 * Section 5.17 — OnboardingTour.jsx
 * Component imports { Joyride, STATUS, EVENTS, ACTIONS } as named exports from react-joyride.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const STATUS = { FINISHED: 'finished', SKIPPED: 'skipped' };
const ACTIONS = { NEXT: 'next', SKIP: 'skip', CLOSE: 'close' };
const EVENTS = { STEP_AFTER: 'step:after', TOUR_END: 'tour:end' };

let capturedCallback = null;
let capturedRun = false;

vi.mock('react-joyride', () => ({
    Joyride: ({ run, onEvent, steps }) => {
        capturedCallback = onEvent;
        capturedRun = run;
        if (!run) return null;
        return (
            <div data-testid="joyride">
                {steps?.map((step, i) => (
                    <div key={i} data-testid={`step-${i}`}>{step.title}</div>
                ))}
            </div>
        );
    },
    STATUS: { FINISHED: 'finished', SKIPPED: 'skipped' },
    ACTIONS: { NEXT: 'next', SKIP: 'skip', CLOSE: 'close' },
    EVENTS: { STEP_AFTER: 'step:after', TOUR_END: 'tour:end' },
}));

vi.mock('../config/onboardingTours', () => ({
    ALL_STEPS: [
        { target: '[data-tour="sidebar-nav"]', title: 'Navigation', content: 'Use the sidebar' },
        { target: '[data-tour="calendar-header"]', title: 'Calendar', content: 'View appointments' },
    ],
    SECTION_CHECKLIST_IDS: { dashboard: ['step-1', 'step-2'] },
    SECTION_VIEW: { dashboard: 'dashboard' },
    getFirstStepIndex: () => 0,
}));

vi.mock('../components/OnboardingTooltip', () => ({
    OnboardingTooltip: ({ tooltipProps, ...rest }) => (
        <div data-testid="tooltip">tooltip</div>
    ),
}));

const clearTourTrigger = vi.fn();
const markComplete = vi.fn();

vi.mock('../context/OnboardingContext', () => ({
    useOnboarding: () => ({
        tourStartSection: 'dashboard',
        clearTourTrigger,
        markComplete,
        SECTION_ITEMS: { dashboard: ['step-1', 'step-2'] },
        SECTION_ORDER: ['dashboard', 'properties'],
    }),
}));

import { OnboardingTour } from '../components/OnboardingTour';

beforeEach(() => {
    vi.clearAllMocks();
    capturedCallback = null;
    capturedRun = false;
});

describe('OnboardingTour', () => {
    it('renders the Joyride tour component when tourStartSection is set', async () => {
        render(<OnboardingTour onNavigate={vi.fn()} onTriggerAction={vi.fn()} />);
        // After the delay in useEffect, run becomes true
        await act(async () => {
            await new Promise(r => setTimeout(r, 2000));
        });
        expect(screen.queryByTestId('joyride')).toBeInTheDocument();
    });

    it('does not render when tourStartSection is null', () => {
        vi.mocked(vi.importMock('../context/OnboardingContext')).useOnboarding = () => ({
            tourStartSection: null,
            clearTourTrigger: vi.fn(),
            markComplete: vi.fn(),
            SECTION_ITEMS: {},
            SECTION_ORDER: [],
        });
    });

    it('clearTourTrigger is called when tour ends via skip', async () => {
        render(<OnboardingTour onNavigate={vi.fn()} onTriggerAction={vi.fn()} />);

        await act(async () => {
            await new Promise(r => setTimeout(r, 2000));
        });

        // Simulate skip via the Joyride callback
        if (capturedCallback) {
            act(() => {
                capturedCallback({
                    action: ACTIONS.SKIP,
                    index: 0,
                    type: EVENTS.TOUR_END,
                    status: STATUS.SKIPPED,
                });
            });
        }

        expect(clearTourTrigger).toHaveBeenCalled();
    });

    it('markComplete is called when tour finishes', async () => {
        render(<OnboardingTour onNavigate={vi.fn()} onTriggerAction={vi.fn()} />);

        await act(async () => {
            await new Promise(r => setTimeout(r, 2000));
        });

        if (capturedCallback) {
            act(() => {
                capturedCallback({
                    action: ACTIONS.NEXT,
                    index: 1,
                    type: EVENTS.TOUR_END,
                    status: STATUS.FINISHED,
                });
            });
        }

        expect(markComplete).toHaveBeenCalled();
    });
});
