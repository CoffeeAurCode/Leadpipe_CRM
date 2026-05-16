/**
 * Section 5.11 — SettingsPage.jsx
 * This is a hierarchical property/unit feature-settings page (NOT a manager profile page).
 * It renders: property groups → buildings → units → feature toggles.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../services/apiService', () => ({
    fetchPropertyGroups: vi.fn(),
    fetchPropertySettings: vi.fn(),
    fetchBuildingSettings: vi.fn(),
    fetchUnitSettings: vi.fn(),
    updatePropertySettings: vi.fn(),
    updateBuildingSettings: vi.fn(),
    updateUnitSettings: vi.fn(),
    fetchPropertyBuildings: vi.fn(),
    fetchBuildingUnits: vi.fn(),
    fetchFlats: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({
        user: { id: 'u1', email: 'mgr@test.com', user_metadata: { full_name: 'Test Manager' } },
        session: { access_token: 'tok' },
    }),
}));

import {
    fetchPropertyGroups,
    fetchPropertyBuildings,
    fetchFlats,
} from '../services/apiService';

import SettingsPage from '../components/SettingsPage';

const MOCK_GROUPS = [
    { id: 'pg1', name: 'Sunrise Residency', address: '12 Park St' },
];

beforeEach(() => {
    vi.clearAllMocks();
    fetchPropertyGroups.mockResolvedValue(MOCK_GROUPS);
    fetchPropertyBuildings.mockResolvedValue([]);
    fetchFlats.mockResolvedValue([]);
});

function renderPage() {
    return render(<SettingsPage />);
}

describe('SettingsPage', () => {
    it('renders without crashing', async () => {
        renderPage();
        await waitFor(() => expect(fetchPropertyGroups).toHaveBeenCalled());
        expect(document.body).not.toBeEmptyDOMElement();
    });

    it('fetches property groups on mount', async () => {
        renderPage();
        await waitFor(() => {
            expect(fetchPropertyGroups).toHaveBeenCalled();
        });
    });

    it('renders Settings heading', async () => {
        renderPage();
        await waitFor(() => {
            const headings = screen.queryAllByText(/settings/i);
            expect(headings.length).toBeGreaterThan(0);
        });
    });

    it('lists property groups after load', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('Sunrise Residency')).toBeInTheDocument();
        });
    });

    it('shows empty state when no property groups', async () => {
        fetchPropertyGroups.mockResolvedValue([]);
        renderPage();
        await waitFor(() => expect(fetchPropertyGroups).toHaveBeenCalled());
        expect(screen.queryByText('Sunrise Residency')).not.toBeInTheDocument();
    });

    it('drills into a property group on click', async () => {
        const user = userEvent.setup();
        fetchPropertyBuildings.mockResolvedValue([{ id: 'b1', name: 'Block A' }]);
        renderPage();
        await waitFor(() => screen.getByText('Sunrise Residency'));

        await user.click(screen.getByText('Sunrise Residency'));

        await waitFor(() => {
            expect(fetchPropertyBuildings).toHaveBeenCalledWith('pg1');
        });
    });
});
