/**
 * Section 5.20 — OutboundCallButton.jsx
 * Covers: toggle open/close, agent selector, E.164 validation, call dispatch
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../services/apiService', () => ({
    makeOutboundCall: vi.fn(),
}));

import { makeOutboundCall } from '../services/apiService';
import OutboundCallButton from '../components/OutboundCallButton';

beforeEach(() => {
    vi.clearAllMocks();
    makeOutboundCall.mockResolvedValue({ call_id: 'call-123', status: 'initiated', agent: 'complaint' });
});

function renderButton() {
    return render(<OutboundCallButton />);
}

describe('OutboundCallButton', () => {
    it('renders the FAB toggle button', () => {
        renderButton();
        expect(screen.getByTitle(/outbound call/i)).toBeInTheDocument();
    });

    it('opens the panel when FAB is clicked', async () => {
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));
        expect(screen.getByText('Outbound Call')).toBeInTheDocument();
    });

    it('shows both Complaint and Lease agent buttons after opening', async () => {
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));
        expect(screen.getByRole('button', { name: /complaint/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /lease/i })).toBeInTheDocument();
    });

    it('defaults to complaint agent', async () => {
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));
        const complaintBtn = screen.getByRole('button', { name: /^complaint$/i });
        expect(complaintBtn.className).toMatch(/bg-primary/);
    });

    it('switches active agent to lease when clicked', async () => {
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));

        await user.click(screen.getByRole('button', { name: /^lease$/i }));

        const leaseBtn = screen.getByRole('button', { name: /^lease$/i });
        expect(leaseBtn.className).toMatch(/bg-primary/);
        expect(screen.getByText(/leasing inquiry/i)).toBeInTheDocument();
    });

    async function setPhoneAndCall(user, phone) {
        const input = screen.getByPlaceholderText('+919876543210');
        fireEvent.change(input, { target: { value: phone } });
        await act(async () => {});
        await user.click(screen.getByRole('button', { name: 'Call' }));
    }

    it('shows validation error for invalid E.164 number', async () => {
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));
        await setPhoneAndCall(user, '12345');
        expect(await screen.findByText(/valid number/i)).toBeInTheDocument();
    });

    it('calls makeOutboundCall with complaint agent by default', async () => {
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));
        await setPhoneAndCall(user, '+919876543210');
        await waitFor(() => expect(makeOutboundCall).toHaveBeenCalledWith('+919876543210', 'complaint'));
    });

    it('calls makeOutboundCall with lease agent when lease is selected', async () => {
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));
        await user.click(screen.getByRole('button', { name: /^lease$/i }));
        await setPhoneAndCall(user, '+919876543210');
        await waitFor(() => expect(makeOutboundCall).toHaveBeenCalledWith('+919876543210', 'lease'));
    });

    it('shows success message after successful call', async () => {
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));
        await setPhoneAndCall(user, '+919876543210');
        await waitFor(() => expect(screen.getByText(/agent is dialling/i)).toBeInTheDocument());
    });

    it('shows error message when makeOutboundCall rejects', async () => {
        makeOutboundCall.mockRejectedValue(new Error('VAPI timed out'));
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));
        await setPhoneAndCall(user, '+919876543210');
        await waitFor(() => expect(screen.getByText(/VAPI timed out/i)).toBeInTheDocument());
    });

    it('closes the panel when X button is clicked', async () => {
        const user = userEvent.setup();
        renderButton();
        await user.click(screen.getByTitle(/outbound call/i));
        expect(screen.getByText('Outbound Call')).toBeInTheDocument();

        // X button is the only button inside the header that has no text
        const header = screen.getByText('Outbound Call').closest('div');
        const closeBtn = header?.parentElement?.querySelector('button:last-child') ??
            screen.getAllByRole('button').find(b => b.textContent?.trim() === '');
        if (closeBtn) {
            await user.click(closeBtn);
            await waitFor(() => expect(screen.queryByText('Outbound Call')).not.toBeInTheDocument());
        }
    });
});
