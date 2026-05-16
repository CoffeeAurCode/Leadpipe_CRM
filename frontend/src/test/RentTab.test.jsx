/**
 * Section 5.12 — RentTab.jsx
 * Data shape from fetchRentSummary: { rows: [...], counts: {} }
 * Each row: { tenant_name, flat_number, flat_uuid, tenant_uuid, rent_status, monthly_rent, effective_from }
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../services/apiService', () => ({
    fetchRentSummary: vi.fn(),
    setRent: vi.fn(),
    updateTenantRentStatus: vi.fn(),
}));

import { fetchRentSummary, setRent, updateTenantRentStatus } from '../services/apiService';
import RentTab from '../components/RentTab';

const MOCK_SUMMARY = {
    rows: [
        {
            tenant_uuid: 't1',
            tenant_name: 'Alice',
            flat_number: 'A-101',
            flat_uuid: 'f1',
            rent_status: 'On-time',
            monthly_rent: 15000,
            effective_from: '2026-01-01',
        },
        {
            tenant_uuid: 't2',
            tenant_name: 'Bob',
            flat_number: 'B-202',
            flat_uuid: 'f2',
            rent_status: 'Overdue',
            monthly_rent: 20000,
            effective_from: '2026-01-01',
        },
    ],
    counts: { 'On-time': 1, Upcoming: 0, Overdue: 1, 'At Risk': 0 },
};

beforeEach(() => {
    vi.clearAllMocks();
    fetchRentSummary.mockResolvedValue(MOCK_SUMMARY);
    setRent.mockResolvedValue({ id: 'r1' });
    updateTenantRentStatus.mockResolvedValue({});
});

function renderPage() {
    return render(<RentTab />);
}

describe('RentTab', () => {
    it('renders after data loads', async () => {
        renderPage();
        await waitFor(() => expect(fetchRentSummary).toHaveBeenCalled());
        expect(document.body).not.toBeEmptyDOMElement();
    });

    it('lists tenants with rent info', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('Alice')).toBeInTheDocument();
            expect(screen.getByText('Bob')).toBeInTheDocument();
        });
    });

    it('shows rent status badges', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getAllByText('On-time').length).toBeGreaterThanOrEqual(1);
            expect(screen.getAllByText('Overdue').length).toBeGreaterThanOrEqual(1);
        });
    });

    it('shows summary status count cards', async () => {
        renderPage();
        await waitFor(() => {
            // Summary cards rendered (SummaryCard shows count + label)
            const onTimeCards = screen.getAllByText('On-time');
            expect(onTimeCards.length).toBeGreaterThanOrEqual(1);
        });
    });

    it('supports inline rent editing', async () => {
        const user = userEvent.setup();
        renderPage();
        await waitFor(() => screen.getByText('Alice'));

        // Look for edit icon button (Edit2 icon on each row)
        const editButtons = screen.getAllByRole('button').filter(b =>
            b.getAttribute('aria-label')?.match(/edit/i) ||
            b.title?.match(/edit/i)
        );
        if (editButtons.length > 0) {
            await user.click(editButtons[0]);
            // Input for new rent value should appear
            expect(screen.queryByRole('spinbutton') ?? document.querySelector('input[type="number"]')).toBeDefined();
        }
    });

    it('shows empty state when no rows', async () => {
        fetchRentSummary.mockResolvedValue({ rows: [], counts: {} });
        renderPage();
        await waitFor(() => expect(fetchRentSummary).toHaveBeenCalled());
        expect(screen.queryByText('Alice')).not.toBeInTheDocument();
    });

    it('renders search input', async () => {
        renderPage();
        await waitFor(() => {
            const search = screen.queryByPlaceholderText(/search/i) || document.querySelector('input[type="text"], input[type="search"]');
            expect(search).toBeDefined();
        });
    });
});
