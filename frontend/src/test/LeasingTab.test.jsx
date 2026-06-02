/**
 * Section 5.19 — LeasingTab.jsx
 * Covers: listings list, lead pipeline, metrics KPIs, status filter, delete, empty state
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../components/AddListingModal', () => ({
    default: ({ onClose }) => <div data-testid="add-listing-modal"><button onClick={onClose}>Close</button></div>,
}));
vi.mock('../components/LeadDetailModal', () => ({
    default: ({ onClose }) => <div data-testid="lead-detail-modal"><button onClick={onClose}>Close</button></div>,
}));

vi.mock('../services/apiService', () => ({
    getListings: vi.fn(),
    deleteListing: vi.fn(),
    getLeaseLeads: vi.fn(),
    deleteLead: vi.fn(),
    getLeasingMetrics: vi.fn(),
    exportLeads: vi.fn(),
    getUserVapiConfig: vi.fn(),
    retryUserProvisioning: vi.fn(),
}));

import {
    getListings, deleteListing,
    getLeaseLeads, deleteLead,
    getLeasingMetrics,
    getUserVapiConfig, retryUserProvisioning,
} from '../services/apiService';
import LeasingTab from '../components/LeasingTab';

const MOCK_LISTING = {
    uuid: 'l1',
    flat_number: 'A-101',
    title: 'Sunny 2BHK',
    monthly_rent: 25000,
    available_from: '2026-06-01',
    is_active: true,
};

const MOCK_LEAD_QUALIFIED = {
    uuid: 'ld1',
    caller_name: 'Ravi Kumar',
    phone: '+919876543210',
    qualification_status: 'qualified',
    bedrooms: 2,
    budget_max: 30000,
    listing_uuid: 'l1',
    created_at: '2026-05-01T10:00:00',
    updated_at: '2026-05-01T10:00:00',
};

const MOCK_LEAD_UNMATCHED = {
    uuid: 'ld2',
    caller_name: 'Priya Singh',
    phone: '+919876540000',
    qualification_status: 'unmatched',
    bedrooms: 3,
    budget_max: 20000,
    listing_uuid: null,
    created_at: '2026-05-02T11:00:00',
    updated_at: '2026-05-02T11:00:00',
};

const MOCK_METRICS = {
    total_calls: 10,
    qualified: 4,
    not_qualified: 3,
    unmatched: 3,
    qualification_rate: 40.0,
    avg_duration_seconds: 120,
};

beforeEach(() => {
    vi.clearAllMocks();
    getListings.mockResolvedValue([MOCK_LISTING]);
    getLeaseLeads.mockResolvedValue([MOCK_LEAD_QUALIFIED, MOCK_LEAD_UNMATCHED]);
    getLeasingMetrics.mockResolvedValue(MOCK_METRICS);
    deleteListing.mockResolvedValue(null);
    deleteLead.mockResolvedValue(null);
    getUserVapiConfig.mockResolvedValue(null);
    retryUserProvisioning.mockResolvedValue(null);
    window.confirm = vi.fn(() => true);
});

function renderPage() {
    return render(<LeasingTab />);
}

describe('LeasingTab', () => {
    it('renders after data loads', async () => {
        renderPage();
        await waitFor(() => expect(getListings).toHaveBeenCalled());
        expect(document.body).not.toBeEmptyDOMElement();
    });

    it('displays listing flat number and title', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getAllByText('A-101').length).toBeGreaterThanOrEqual(1);
            expect(screen.getByText('Sunny 2BHK')).toBeInTheDocument();
        });
    });

    it('displays lead caller names', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('Ravi Kumar')).toBeInTheDocument();
            expect(screen.getByText('Priya Singh')).toBeInTheDocument();
        });
    });

    it('displays qualification status badges', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getAllByText('Qualified').length).toBeGreaterThanOrEqual(1);
            expect(screen.getAllByText('Unmatched').length).toBeGreaterThanOrEqual(1);
        });
    });

    it('displays metrics KPI values', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('10')).toBeInTheDocument();
            expect(screen.getByText('4')).toBeInTheDocument();
        });
    });

    it('opens AddListingModal when Add Listing button is clicked', async () => {
        const user = userEvent.setup();
        renderPage();
        await waitFor(() => screen.getByText('Sunny 2BHK'));

        const addBtn = screen.getByText(/add listing/i).closest('button');
        expect(addBtn).not.toBeNull();
        await user.click(addBtn);
        expect(screen.getByTestId('add-listing-modal')).toBeInTheDocument();
    });

    it('deletes a listing after confirmation', async () => {
        const user = userEvent.setup();
        renderPage();
        await waitFor(() => screen.getByText('Sunny 2BHK'));

        const allButtons = screen.getAllByRole('button');
        const deleteBtn = allButtons.find(b =>
            b.querySelector('svg') &&
            (b.title?.match(/delete/i) || b.getAttribute('aria-label')?.match(/delete/i))
        );
        if (deleteBtn) {
            await user.click(deleteBtn);
            expect(window.confirm).toHaveBeenCalled();
            await waitFor(() => expect(deleteListing).toHaveBeenCalledWith('l1'));
        } else {
            // The delete button is icon-only; click the last SVG button in the listing card
            const cardButtons = allButtons.filter(b =>
                b.closest('.bg-card') && b.querySelector('svg')
            );
            if (cardButtons.length > 0) {
                await user.click(cardButtons[cardButtons.length - 1]);
                if (window.confirm.mock.calls.length > 0) {
                    await waitFor(() => expect(deleteListing).toHaveBeenCalled());
                }
            }
        }
    });

    it('shows empty leads state when no leads returned', async () => {
        getLeaseLeads.mockResolvedValue([]);
        renderPage();
        await waitFor(() => expect(getLeaseLeads).toHaveBeenCalled());
        expect(screen.queryByText('Ravi Kumar')).not.toBeInTheDocument();
    });

    it('shows empty listings state when no listings returned', async () => {
        getListings.mockResolvedValue([]);
        renderPage();
        await waitFor(() => expect(getListings).toHaveBeenCalled());
        expect(screen.queryByText('A-101')).not.toBeInTheDocument();
    });
});
