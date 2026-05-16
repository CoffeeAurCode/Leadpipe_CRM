/**
 * Section 5.3 — OnboardingContext.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { OnboardingProvider, useOnboarding } from '../context/OnboardingContext';
import { AuthProvider } from '../context/AuthContext';
import { supabase } from '../lib/supabase';

const TEST_USER = { id: 'u1', email: 'mgr@test.com' };

// Wrap OnboardingProvider inside AuthProvider (it uses useAuth internally)
function Wrapper({ children }) {
    return (
        <AuthProvider>
            <OnboardingProvider>{children}</OnboardingProvider>
        </AuthProvider>
    );
}

// Expose key values from context for assertions
function OnboardingConsumer() {
    const {
        checked,
        isChecklistComplete,
        totalItems,
        completedItems,
        tourStartSection,
        triggerTour,
        clearTourTrigger,
        dbTourCompleted,
    } = useOnboarding();

    return (
        <div>
            <span data-testid="complete">{String(isChecklistComplete)}</span>
            <span data-testid="total">{totalItems}</span>
            <span data-testid="done">{completedItems}</span>
            <span data-testid="tour-section">{tourStartSection ?? 'none'}</span>
            <span data-testid="db-done">{String(dbTourCompleted)}</span>
            <button onClick={() => triggerTour('dashboard')} data-testid="trigger">Trigger</button>
            <button onClick={clearTourTrigger} data-testid="clear">Clear</button>
        </div>
    );
}

function setupAuthMock(userOrNull = TEST_USER) {
    supabase.auth.onAuthStateChange.mockImplementation((cb) => {
        if (userOrNull) {
            cb('INITIAL_SESSION', { user: userOrNull, access_token: 'tok' });
        } else {
            cb('INITIAL_SESSION', null);
        }
        return { data: { subscription: { unsubscribe: vi.fn() } } };
    });
}

function setupDbMock(tourCompleted = false) {
    supabase.from.mockReturnValue({
        select: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
        maybeSingle: vi.fn().mockResolvedValue({ data: { tour_completed: tourCompleted }, error: null }),
        update: vi.fn().mockReturnThis(),
        insert: vi.fn().mockResolvedValue({ error: null }),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    setupAuthMock();
    setupDbMock(false);
});

describe('OnboardingContext', () => {
    it('loads initial state from localStorage when present', async () => {
        const key = `crm-onboarding-checklist-${TEST_USER.id}`;
        localStorage.setItem(key, JSON.stringify({ 'step-1': true }));

        const { getByTestId } = render(
            <Wrapper>
                <OnboardingConsumer />
            </Wrapper>
        );

        await waitFor(() => expect(getByTestId('total').textContent).not.toBe('0'));
        // checklist is not complete because not all items are checked
        expect(getByTestId('complete').textContent).toBe('false');
    });

    it('triggerTour sets tourStartSection', async () => {
        const { getByTestId } = render(
            <Wrapper>
                <OnboardingConsumer />
            </Wrapper>
        );

        await waitFor(() => expect(getByTestId('tour-section').textContent).toBe('none'));

        act(() => { getByTestId('trigger').click(); });
        expect(getByTestId('tour-section').textContent).toBe('dashboard');
    });

    it('clearTourTrigger resets tourStartSection to null', async () => {
        const { getByTestId } = render(
            <Wrapper>
                <OnboardingConsumer />
            </Wrapper>
        );

        act(() => { getByTestId('trigger').click(); });
        expect(getByTestId('tour-section').textContent).toBe('dashboard');

        act(() => { getByTestId('clear').click(); });
        expect(getByTestId('tour-section').textContent).toBe('none');
    });

    it('when DB says tour_completed=true, dbTourCompleted becomes true', async () => {
        setupDbMock(true);

        const { getByTestId } = render(
            <Wrapper>
                <OnboardingConsumer />
            </Wrapper>
        );

        await waitFor(() => {
            expect(getByTestId('db-done').textContent).toBe('true');
        });
    });

    it('DB is authority: forces local complete state when tour_completed=true in DB', async () => {
        setupDbMock(true);

        const { getByTestId } = render(
            <Wrapper>
                <OnboardingConsumer />
            </Wrapper>
        );

        await waitFor(() => {
            expect(getByTestId('complete').textContent).toBe('true');
        });
    });

    it('throws if useOnboarding used outside provider', () => {
        const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
        expect(() => render(<OnboardingConsumer />)).toThrow('useOnboarding must be used within OnboardingProvider');
        spy.mockRestore();
    });
});
