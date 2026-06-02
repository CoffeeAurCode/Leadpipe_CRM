/**
 * Section 5.5 — Chatbot.jsx
 *
 * Button DOM order when dialog is CLOSED: [FAB]
 * Button DOM order when dialog is OPEN:   [header-X, send, FAB]
 * (AnimatePresence renders dialog before FAB in JSX)
 *
 * user.type() only commits the first character in React controlled inputs due to
 * React 18 concurrent mode batching. user.keyboard() has the same issue.
 *
 * Fix: RTL's fireEvent.input(el, { target: { value } }) calls setNativeValue then
 * dispatches an InputEvent that React processes as onChange. After await act() flushes
 * the state update, user.click(sendBtn) fires handleSend with the committed input value.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Chatbot from '../components/Chatbot';

vi.mock('../services/apiService', () => ({
    sendChatMessage: vi.fn(),
}));

import { sendChatMessage } from '../services/apiService';

function renderChatbot() {
    return render(<Chatbot />);
}

// Open chatbot by clicking FAB, then return the input element.
async function openChatbot(user) {
    await user.click(screen.getByRole('button')); // click FAB — only button when closed
    return screen.getByPlaceholderText('Ask me anything about your properties…');
}

// Set input value via RTL's fireEvent.input (triggers React onChange),
// flush state with act, then click the Send button (index 1: header-X=0, send=1, FAB=2).
async function typeAndSend(user, inputEl, text) {
    fireEvent.input(inputEl, { target: { value: text } });
    await act(async () => {});
    const sendBtn = screen.getAllByRole('button')[1];
    await user.click(sendBtn);
}

describe('Chatbot', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders the FAB button when closed', () => {
        renderChatbot();
        expect(screen.getAllByRole('button').length).toBe(1);
    });

    it('chat dialog is hidden by default', () => {
        renderChatbot();
        expect(screen.queryByPlaceholderText('Ask me anything about your properties…')).not.toBeInTheDocument();
    });

    it('opens the dialog when FAB is clicked', async () => {
        const user = userEvent.setup();
        renderChatbot();
        await openChatbot(user);
        expect(screen.getByPlaceholderText('Ask me anything about your properties…')).toBeInTheDocument();
    });

    it('shows 3 buttons when dialog is open: header-X, send, FAB', async () => {
        const user = userEvent.setup();
        renderChatbot();
        await openChatbot(user);
        expect(screen.getAllByRole('button').length).toBe(3);
    });

    it('closes dialog when the header X button is clicked', async () => {
        const user = userEvent.setup();
        renderChatbot();
        await openChatbot(user);
        expect(screen.getByPlaceholderText('Ask me anything about your properties…')).toBeInTheDocument();

        const buttons = screen.getAllByRole('button');
        await user.click(buttons[0]); // header X (0=header-X, 1=send, 2=FAB)

        expect(screen.queryByPlaceholderText('Ask me anything about your properties…')).not.toBeInTheDocument();
    });

    it('sends a message on Enter and shows user message', async () => {
        const user = userEvent.setup();
        sendChatMessage.mockResolvedValue({ reply: 'Hi there!', refresh_needed: false });

        renderChatbot();
        const input = await openChatbot(user);
        await typeAndSend(user, input, 'Hello');

        await waitFor(() => {
            expect(screen.getByText('Hello')).toBeInTheDocument();
        }, { timeout: 3000 });
    });

    it('shows bot reply in the chat window', async () => {
        const user = userEvent.setup();
        sendChatMessage.mockResolvedValue({ reply: 'Bot reply here!', refresh_needed: false });

        renderChatbot();
        const input = await openChatbot(user);
        await typeAndSend(user, input, 'Test message');

        await waitFor(() => {
            expect(screen.getByText('Bot reply here!')).toBeInTheDocument();
        }, { timeout: 3000 });

        expect(sendChatMessage).toHaveBeenCalledTimes(1);
    });

    it('shows "Thinking…" indicator while loading', async () => {
        const user = userEvent.setup();
        sendChatMessage.mockReturnValue(new Promise(() => {}));

        renderChatbot();
        const input = await openChatbot(user);
        await typeAndSend(user, input, 'Hello');

        await waitFor(() => {
            expect(screen.getByText('Thinking…')).toBeInTheDocument();
        });
    });

    it('disables input while loading', async () => {
        const user = userEvent.setup();
        sendChatMessage.mockReturnValue(new Promise(() => {}));

        renderChatbot();
        const input = await openChatbot(user);
        await typeAndSend(user, input, 'Hello');

        await waitFor(() => {
            expect(screen.getByPlaceholderText('Ask me anything about your properties…')).toBeDisabled();
        });
    });

    it('shows error message on API failure', async () => {
        const user = userEvent.setup();
        sendChatMessage.mockRejectedValue(new Error('Network error'));

        renderChatbot();
        const input = await openChatbot(user);
        await typeAndSend(user, input, 'Hello');

        await waitFor(() => {
            expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
        }, { timeout: 3000 });
    });

    it('dispatches refresh-appointments event when refresh_needed=true', async () => {
        const user = userEvent.setup();
        sendChatMessage.mockResolvedValue({ reply: 'Done!', refresh_needed: true });

        const dispatchSpy = vi.spyOn(window, 'dispatchEvent');

        renderChatbot();
        const input = await openChatbot(user);
        await typeAndSend(user, input, 'Book appointment');

        await waitFor(() => {
            const refreshEvents = dispatchSpy.mock.calls.filter(([e]) => e.type === 'refresh-appointments');
            expect(refreshEvents.length).toBeGreaterThan(0);
        }, { timeout: 3000 });
    });

    it('does not dispatch refresh event when refresh_needed=false', async () => {
        const user = userEvent.setup();
        sendChatMessage.mockResolvedValue({ reply: 'OK', refresh_needed: false });

        const dispatchSpy = vi.spyOn(window, 'dispatchEvent');

        renderChatbot();
        const input = await openChatbot(user);
        await typeAndSend(user, input, 'Hello');

        await waitFor(() => expect(screen.getByText('OK')).toBeInTheDocument(), { timeout: 3000 });

        const refreshEvents = dispatchSpy.mock.calls.filter(([e]) => e.type === 'refresh-appointments');
        expect(refreshEvents).toHaveLength(0);
    });

    it('does not send empty message', async () => {
        const user = userEvent.setup();
        renderChatbot();
        const input = await openChatbot(user);
        fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' }); // empty input
        expect(sendChatMessage).not.toHaveBeenCalled();
    });
});
