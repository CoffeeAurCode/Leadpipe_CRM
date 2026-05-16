/**
 * Section 5.16 — AuthPage.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AuthPage from '../components/AuthPage';
import { supabase } from '../lib/supabase';

vi.mock('../components/icon.svg', () => ({ default: '' }));

beforeEach(() => {
    vi.clearAllMocks();
});

function renderAuthPage() {
    return render(<AuthPage />);
}

describe('AuthPage', () => {
    it('renders the Google sign-in button', () => {
        renderAuthPage();
        expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
    });

    it('renders the Sign In heading by default', () => {
        renderAuthPage();
        expect(screen.getByText(/sign in to leadpipe/i)).toBeInTheDocument();
    });

    it('renders email and password fields', () => {
        renderAuthPage();
        expect(screen.getByPlaceholderText('name@example.com')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    });

    it('switches to Sign Up mode when link is clicked', async () => {
        const user = userEvent.setup();
        renderAuthPage();

        await user.click(screen.getByRole('button', { name: /sign up/i }));

        expect(screen.getByText(/create your account/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText('John Doe')).toBeInTheDocument(); // Name field appears
    });

    it('clicking Google button triggers supabase.auth.signInWithOAuth', async () => {
        const user = userEvent.setup();
        supabase.auth.signInWithOAuth.mockResolvedValue({ error: null });

        renderAuthPage();
        await user.click(screen.getByRole('button', { name: /continue with google/i }));

        expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith(
            expect.objectContaining({ provider: 'google' })
        );
    });

    it('shows loading spinner on Google button while connecting', async () => {
        const user = userEvent.setup();
        // Never resolves — stays loading
        supabase.auth.signInWithOAuth.mockReturnValue(new Promise(() => {}));

        renderAuthPage();
        await user.click(screen.getByRole('button', { name: /continue with google/i }));

        expect(screen.getByText(/connecting to google/i)).toBeInTheDocument();
    });

    it('shows error message when Google OAuth fails', async () => {
        const user = userEvent.setup();
        supabase.auth.signInWithOAuth.mockResolvedValue({ error: { message: 'OAuth failed' } });

        renderAuthPage();
        await user.click(screen.getByRole('button', { name: /continue with google/i }));

        await waitFor(() => {
            expect(screen.getByText('OAuth failed')).toBeInTheDocument();
        });
    });

    it('sign in form submits via supabase.auth.signInWithPassword', async () => {
        const user = userEvent.setup();
        supabase.auth.signInWithPassword.mockResolvedValue({ error: null });

        renderAuthPage();

        await user.type(screen.getByPlaceholderText('name@example.com'), 'test@example.com');
        await user.type(screen.getByPlaceholderText('••••••••'), 'password123');
        await user.click(screen.getByRole('button', { name: /^sign in$/i }));

        expect(supabase.auth.signInWithPassword).toHaveBeenCalledWith({
            email: 'test@example.com',
            password: 'password123',
        });
    });

    it('shows error message when sign in fails', async () => {
        const user = userEvent.setup();
        supabase.auth.signInWithPassword.mockResolvedValue({ error: { message: 'Invalid credentials' } });

        renderAuthPage();
        await user.type(screen.getByPlaceholderText('name@example.com'), 'bad@example.com');
        await user.type(screen.getByPlaceholderText('••••••••'), 'wrongpass');
        await user.click(screen.getByRole('button', { name: /^sign in$/i }));

        await waitFor(() => {
            expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
        });
    });

    it('sign up mode requires name field — shows error via fireEvent.submit', async () => {
        const user = userEvent.setup();
        renderAuthPage();

        await user.click(screen.getByRole('button', { name: /sign up/i }));

        // Fill email & password but leave name empty
        await user.type(screen.getByPlaceholderText('name@example.com'), 'new@example.com');
        await user.type(screen.getByPlaceholderText('••••••••'), 'Password123');

        // Use fireEvent.submit to bypass native HTML5 required validation in jsdom
        const form = document.querySelector('form');
        fireEvent.submit(form);

        await waitFor(() => {
            expect(screen.getByText('Name is required')).toBeInTheDocument();
        });
        expect(supabase.auth.signUp).not.toHaveBeenCalled();
    });

    it('sign up creates manager profile after successful sign up', async () => {
        const user = userEvent.setup();
        supabase.auth.signUp.mockResolvedValue({
            data: { user: { id: 'u-new' } },
            error: null,
        });
        const insertMock = vi.fn().mockResolvedValue({ error: null });
        supabase.from.mockReturnValue({
            insert: insertMock,
        });

        renderAuthPage();
        await user.click(screen.getByRole('button', { name: /sign up/i }));

        await user.type(screen.getByPlaceholderText('John Doe'), 'Jane Doe');
        await user.type(screen.getByPlaceholderText('name@example.com'), 'jane@example.com');
        await user.type(screen.getByPlaceholderText('••••••••'), 'secure123');
        await user.click(screen.getByRole('button', { name: /create account/i }));

        await waitFor(() => {
            expect(supabase.auth.signUp).toHaveBeenCalled();
        });
        expect(insertMock).toHaveBeenCalled();
    });
});
