/**
 * Section 5.9 — TenantManagement.jsx
 * Filtering is server-side via fetchTenants params (no local text search).
 * Rent/lease filters are <select> dropdowns that re-call fetchTenants.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../services/apiService', () => ({
    fetchTenants: vi.fn(),
    deleteTenant: vi.fn(),
    updateTenantRentStatus: vi.fn(),
    fetchVacantFlats: vi.fn(),
    createTenant: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 'u1', email: 'mgr@test.com' }, session: { access_token: 'tok' } }),
}));

vi.mock('../context/OnboardingContext', () => ({
    useOnboarding: () => ({
        markComplete: vi.fn(),
        isChecklistComplete: true,
        checked: {},
        SECTION_ITEMS: {},
    }),
}));

import {
    fetchTenants,
    deleteTenant,
    fetchVacantFlats,
} from '../services/apiService';

import TenantManagement from '../components/TenantManagement';

const MOCK_TENANTS = [
    {
        uuid: 't1',
        name: 'Alice Smith',
        phone: '+919876543210',
        email: 'alice@example.com',
        rent_status: 'On-time',
        lease_status: 'Active',
        flat_number: 'A-101',
        flat_uuid: 'f1',
    },
    {
        uuid: 't2',
        name: 'Bob Jones',
        phone: '+919999999999',
        email: 'bob@example.com',
        rent_status: 'Overdue',
        lease_status: 'Active',
        flat_number: 'B-202',
        flat_uuid: 'f2',
    },
];

beforeEach(() => {
    vi.clearAllMocks();
    fetchTenants.mockResolvedValue(MOCK_TENANTS);
    fetchVacantFlats.mockResolvedValue([]);
});

function renderPage() {
    return render(<TenantManagement />);
}

describe('TenantManagement', () => {
    it('calls fetchTenants on mount', async () => {
        renderPage();
        await waitFor(() => expect(fetchTenants).toHaveBeenCalled());
    });

    it('renders list of tenants after load', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('Alice Smith')).toBeInTheDocument();
            expect(screen.getByText('Bob Jones')).toBeInTheDocument();
        });
    });

    it('shows tenant flat number', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('A-101')).toBeInTheDocument();
        });
    });

    it('filters by rent_status by selecting from dropdown — calls API with param', async () => {
        const user = userEvent.setup();
        renderPage(); // initial load uses beforeEach mock (both tenants)
        await waitFor(() => screen.getByText('Alice Smith'));

        // Override mock for the next call, then select Overdue
        fetchTenants.mockResolvedValue([MOCK_TENANTS[1]]);
        const rentSelect = screen.getByDisplayValue('All Rent Statuses');
        await user.selectOptions(rentSelect, 'Overdue');

        await waitFor(() => {
            expect(fetchTenants).toHaveBeenCalledWith(
                expect.objectContaining({ rent_status: 'Overdue' })
            );
        });
    });

    it('shows Tenant Management heading', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('Tenant Management')).toBeInTheDocument();
        });
    });

    it('renders rent status badges', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getAllByText('Overdue').length).toBeGreaterThanOrEqual(1);
            expect(screen.getAllByText('On-time').length).toBeGreaterThanOrEqual(1);
        });
    });

    it('shows "Add Tenant" button', async () => {
        renderPage();
        await waitFor(() => {
            const addBtn = screen.queryByText(/add tenant/i);
            expect(addBtn).toBeInTheDocument();
        });
    });

    it('shows Import CSV button', async () => {
        renderPage();
        await waitFor(() => {
            const importBtn = screen.queryByText(/import csv/i);
            expect(importBtn).toBeInTheDocument();
        });
    });

    it('shows empty state when no tenants returned', async () => {
        fetchTenants.mockResolvedValue([]);
        renderPage();
        await waitFor(() => expect(fetchTenants).toHaveBeenCalled());
        expect(screen.queryByText('Alice Smith')).not.toBeInTheDocument();
    });

    it('shows error message on fetch failure', async () => {
        fetchTenants.mockRejectedValue(new Error('Network error'));
        renderPage();
        await waitFor(() => {
            expect(screen.getByText(/failed to load tenants/i)).toBeInTheDocument();
        });
    });
});
