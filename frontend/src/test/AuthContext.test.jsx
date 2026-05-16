/**
 * Section 5.2 — AuthContext.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';

// Helper: render a component that exposes auth context values
function AuthConsumer() {
    const { user, session, loading, signOut } = useAuth();
    return (
        <div>
            <span data-testid="loading">{String(loading)}</span>
            <span data-testid="user">{user ? user.email : 'null'}</span>
            <span data-testid="session">{session ? 'has-session' : 'no-session'}</span>
            <button onClick={signOut} data-testid="sign-out">Sign Out</button>
        </div>
    );
}

function renderAuth() {
    return render(
        <AuthProvider>
            <AuthConsumer />
        </AuthProvider>
    );
}

describe('AuthContext', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('starts with loading=true before INITIAL_SESSION fires', () => {
        // onAuthStateChange never fires → loading stays true
        supabase.auth.onAuthStateChange.mockReturnValue({
            data: { subscription: { unsubscribe: vi.fn() } },
        });

        const { getByTestId } = renderAuth();
        expect(getByTestId('loading').textContent).toBe('true');
    });

    it('sets loading=false and populates user after INITIAL_SESSION', async () => {
        const mockUser = { id: 'u1', email: 'mgr@example.com' };
        const mockSession = { user: mockUser, access_token: 'tok' };

        supabase.auth.onAuthStateChange.mockImplementation((cb) => {
            // Fire INITIAL_SESSION synchronously
            cb('INITIAL_SESSION', mockSession);
            return { data: { subscription: { unsubscribe: vi.fn() } } };
        });

        const { getByTestId } = renderAuth();

        await waitFor(() => {
            expect(getByTestId('loading').textContent).toBe('false');
            expect(getByTestId('user').textContent).toBe('mgr@example.com');
            expect(getByTestId('session').textContent).toBe('has-session');
        });
    });

    it('user is null when session is null', async () => {
        supabase.auth.onAuthStateChange.mockImplementation((cb) => {
            cb('INITIAL_SESSION', null);
            return { data: { subscription: { unsubscribe: vi.fn() } } };
        });

        const { getByTestId } = renderAuth();

        await waitFor(() => {
            expect(getByTestId('user').textContent).toBe('null');
            expect(getByTestId('session').textContent).toBe('no-session');
        });
    });

    it('calls signOut on Supabase when signOut() is invoked', async () => {
        const mockUser = { id: 'u1', email: 'mgr@example.com' };
        supabase.auth.onAuthStateChange.mockImplementation((cb) => {
            cb('INITIAL_SESSION', { user: mockUser, access_token: 'tok' });
            return { data: { subscription: { unsubscribe: vi.fn() } } };
        });

        const { getByTestId } = renderAuth();
        await waitFor(() => expect(getByTestId('loading').textContent).toBe('false'));

        await act(async () => {
            getByTestId('sign-out').click();
        });

        expect(supabase.auth.signOut).toHaveBeenCalled();
    });

    it('calls ensureManagerProfile on first sign-in via onAuthStateChange', async () => {
        const mockUser = { id: 'u-new', email: 'new@example.com', user_metadata: { full_name: 'New User' } };

        supabase.from.mockReturnValue({
            select: vi.fn().mockReturnThis(),
            eq: vi.fn().mockReturnThis(),
            maybeSingle: vi.fn().mockResolvedValue({ data: null, error: null }),
            insert: vi.fn().mockResolvedValue({ error: null }),
        });

        supabase.auth.onAuthStateChange.mockImplementation((cb) => {
            cb('INITIAL_SESSION', { user: mockUser, access_token: 'tok' });
            return { data: { subscription: { unsubscribe: vi.fn() } } };
        });

        renderAuth();

        await waitFor(() => {
            expect(supabase.from).toHaveBeenCalledWith('manager_profiles');
        });
    });

    it('unsubscribes from onAuthStateChange on unmount', () => {
        const unsubSpy = vi.fn();
        supabase.auth.onAuthStateChange.mockReturnValue({
            data: { subscription: { unsubscribe: unsubSpy } },
        });

        const { unmount } = renderAuth();
        unmount();

        expect(unsubSpy).toHaveBeenCalled();
    });

    it('throws if useAuth is used outside AuthProvider', () => {
        const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
        expect(() => render(<AuthConsumer />)).toThrow('useAuth must be used within an AuthProvider');
        spy.mockRestore();
    });
});
