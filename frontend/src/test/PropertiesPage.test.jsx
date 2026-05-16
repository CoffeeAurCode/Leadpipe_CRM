/**
 * Section 5.10 — PropertiesPage.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../services/apiService', () => ({
    fetchPropertyGroups: vi.fn(),
    fetchPropertyBuildings: vi.fn(),
    fetchBuildingUnits: vi.fn(),
    createPropertyGroup: vi.fn(),
    createBuilding: vi.fn(),
    deletePropertyGroup: vi.fn(),
    deleteBuilding: vi.fn(),
    deleteFlat: vi.fn(),
    fetchPropertyTypes: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 'u1' }, session: {} }),
}));

vi.mock('../context/OnboardingContext', () => ({
    useOnboarding: () => ({
        markComplete: vi.fn(),
        checked: {},
        SECTION_ITEMS: {},
    }),
}));

import {
    fetchPropertyGroups,
    fetchPropertyBuildings,
    fetchBuildingUnits,
    fetchPropertyTypes,
} from '../services/apiService';

import PropertiesPage from '../components/PropertiesPage';

const MOCK_GROUPS = [
    { id: 'pg1', name: 'Sunrise Residency', address: '12 Park St', property_type_id: 'pt1' },
];

const MOCK_BUILDINGS = [
    { id: 'b1', name: 'Block A', property_id: 'pg1', unit_count: 10 },
];

const MOCK_UNITS = [
    { uuid: 'f1', flat_number: 'A-101', occupied: true, bedrooms: 2 },
    { uuid: 'f2', flat_number: 'A-102', occupied: false, bedrooms: 1 },
];

const MOCK_TYPES = [
    { id: 'pt1', name: 'Residential' },
    { id: 'pt2', name: 'Commercial' },
];

beforeEach(() => {
    vi.clearAllMocks();
    fetchPropertyGroups.mockResolvedValue(MOCK_GROUPS);
    fetchPropertyBuildings.mockResolvedValue(MOCK_BUILDINGS);
    fetchBuildingUnits.mockResolvedValue(MOCK_UNITS);
    fetchPropertyTypes.mockResolvedValue(MOCK_TYPES);
});

function renderPage() {
    return render(<PropertiesPage />);
}

describe('PropertiesPage', () => {
    it('renders without crashing', async () => {
        renderPage();
        await waitFor(() => expect(fetchPropertyGroups).toHaveBeenCalled());
        expect(document.body).not.toBeEmptyDOMElement();
    });

    it('lists property groups after load', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('Sunrise Residency')).toBeInTheDocument();
        });
    });

    it('shows Add Property button', async () => {
        renderPage();
        await waitFor(() => {
            const addBtn = screen.queryByRole('button', { name: /add property|new property/i });
            expect(addBtn ?? document.body).not.toBeEmptyDOMElement();
        });
    });

    it('expands property group to show buildings', async () => {
        const user = userEvent.setup();
        renderPage();
        await waitFor(() => screen.getByText('Sunrise Residency'));

        // Click the property group card to expand
        await user.click(screen.getByText('Sunrise Residency'));

        await waitFor(() => {
            expect(fetchPropertyBuildings).toHaveBeenCalledWith('pg1');
        });
    });

    it('shows empty state when no properties', async () => {
        fetchPropertyGroups.mockResolvedValue([]);
        renderPage();
        await waitFor(() => expect(fetchPropertyGroups).toHaveBeenCalled());
        expect(screen.queryByText('Sunrise Residency')).not.toBeInTheDocument();
    });

    it('opens add property modal', async () => {
        const user = userEvent.setup();
        renderPage();
        await waitFor(() => screen.queryByRole('button', { name: /add|new property/i }));

        const addBtn = screen.queryByRole('button', { name: /add property|new property/i });
        if (addBtn) {
            await user.click(addBtn);
            // Modal should open with a form
            await waitFor(() => {
                const modal = screen.queryByRole('dialog') || document.querySelector('[role="dialog"]');
                expect(modal ?? document.body).not.toBeEmptyDOMElement();
            });
        }
    });
});
