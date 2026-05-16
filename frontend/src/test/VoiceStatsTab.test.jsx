/**
 * Section 5.13 — VoiceStatsTab.jsx
 * Uses fetchCallStats only (recent calls embedded in the stats response).
 * Data shape: { total, resolved, escalated, by_date: {}, recent: [] }
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

vi.mock('../services/apiService', () => ({
    fetchCallStats: vi.fn(),
}));

import { fetchCallStats } from '../services/apiService';
import VoiceStatsTab from '../components/VoiceStatsTab';

const MOCK_STATS = {
    total: 42,
    resolved: 30,
    escalated: 5,
    by_date: {
        '2026-05-01': 5,
        '2026-05-02': 8,
    },
    recent: [
        {
            id: 'log1',
            phone_number: '+919876543210',
            flat_number: 'A-101',
            complaint_status: 'resolved',
            created_at: '2026-05-01T10:00:00',
        },
    ],
};

beforeEach(() => {
    vi.clearAllMocks();
    fetchCallStats.mockResolvedValue(MOCK_STATS);
});

function renderPage() {
    return render(<VoiceStatsTab />);
}

describe('VoiceStatsTab', () => {
    it('renders without crashing', async () => {
        renderPage();
        await waitFor(() => expect(fetchCallStats).toHaveBeenCalled());
        expect(document.body).not.toBeEmptyDOMElement();
    });

    it('fetches call stats on mount', async () => {
        renderPage();
        await waitFor(() => {
            expect(fetchCallStats).toHaveBeenCalled();
        });
    });

    it('renders the Voice Agent Stats heading', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('Voice Agent Stats')).toBeInTheDocument();
        });
    });

    it('shows total call count after data loads', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('42')).toBeInTheDocument();
        });
    });

    it('shows stat cards for Resolved and Escalated', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('Resolved')).toBeInTheDocument();
            expect(screen.getByText('Escalated')).toBeInTheDocument();
        });
    });

    it('shows recent call log when data.recent is populated', async () => {
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('+919876543210')).toBeInTheDocument();
        });
    });

    it('shows empty state for recent calls when none exist', async () => {
        fetchCallStats.mockResolvedValue({ total: 0, resolved: 0, escalated: 0, by_date: {}, recent: [] });
        renderPage();
        await waitFor(() => {
            expect(screen.getByText('No recent calls found.')).toBeInTheDocument();
        });
    });

    it('shows date range filter dropdown', async () => {
        renderPage();
        await waitFor(() => {
            const select = screen.getByRole('combobox');
            expect(select).toBeInTheDocument();
        });
    });
});
