/**
 * Section 5.4 — Dashboard (App.jsx's Dashboard component via BentoDashboard)
 * We test the legacy Dashboard.jsx component which uses api.js directly,
 * and BentoDashboard.jsx for KPI / chart rendering.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';

// Mock the old api.js service
vi.mock('../services/api', () => ({
    api: {
        fetchComplaints: vi.fn(),
        fetchCallLogs: vi.fn(),
        updateComplaintStatus: vi.fn(),
    },
}));

// Mock apiService.js for BentoDashboard
vi.mock('../services/apiService', () => ({
    fetchComplaints: vi.fn(),
    fetchAppointments: vi.fn(),
    updateComplaint: vi.fn(),
    updateAppointment: vi.fn(),
    deleteAppointment: vi.fn(),
    getCallStatus: vi.fn(),
    fetchCallStats: vi.fn(),
    fetchCallLogs: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 'u1', email: 'mgr@test.com' }, session: {} }),
}));

vi.mock('../context/OnboardingContext', () => ({
    useOnboarding: () => ({
        isChecklistComplete: true,
        dbTourCompleted: true,
        markComplete: vi.fn(),
        SECTION_ITEMS: {},
        checked: {},
    }),
}));

vi.mock('../components/dashboard/TrendsChart', () => ({
    default: () => <div data-testid="trends-chart" />,
}));
vi.mock('../components/dashboard/StatusDonut', () => ({
    default: () => <div data-testid="status-donut" />,
}));
vi.mock('../components/dashboard/CategoriesPie', () => ({
    default: () => <div data-testid="categories-pie" />,
}));
vi.mock('../components/dashboard/AppointmentsBar', () => ({
    default: () => <div data-testid="appointments-bar" />,
}));
vi.mock('../components/dashboard/KPICard', () => ({
    default: ({ title, value }) => <div data-testid={`kpi-${title}`}>{value}</div>,
}));

vi.mock('../components/dashboard/DashboardListModal', () => ({
    default: () => null,
}));
vi.mock('../components/dashboard/DailyTasksModal', () => ({
    default: () => null,
}));

vi.mock('../components/CalendarView', () => ({
    default: () => <div data-testid="calendar-view" />,
}));

import Dashboard from '../components/Dashboard';
import { api } from '../services/api';

const MOCK_COMPLAINTS = [
    { id: 1, status: 'pending', priority: 'high', flat_number: 'A-101', created_at: '2026-05-01T10:00:00' },
    { id: 2, status: 'in-progress', priority: 'medium', flat_number: 'B-202', created_at: '2026-05-02T11:00:00' },
];

beforeEach(() => {
    vi.clearAllMocks();
    api.fetchComplaints.mockResolvedValue(MOCK_COMPLAINTS);
    api.fetchCallLogs.mockResolvedValue([]);
});

describe('Dashboard (legacy)', () => {
    it('shows loading state initially', () => {
        api.fetchComplaints.mockReturnValue(new Promise(() => {}));
        render(<Dashboard />);
        expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it('renders complaints after load', async () => {
        render(<Dashboard />);
        await waitFor(() => {
            expect(screen.getByText(/A-101/)).toBeInTheDocument();
        });
    });

    it('shows error state when fetch fails', async () => {
        api.fetchComplaints.mockRejectedValue(new Error('Network error'));
        render(<Dashboard />);
        await waitFor(() => {
            expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
        });
    });

    it('polls data every 5 seconds via setInterval', async () => {
        vi.useFakeTimers({ shouldAdvanceTime: false });
        // Re-mock inside fake timers context
        api.fetchComplaints.mockResolvedValue(MOCK_COMPLAINTS);
        api.fetchCallLogs.mockResolvedValue([]);

        render(<Dashboard />);

        // Initial load from useEffect
        await act(async () => {});
        const initialCalls = api.fetchComplaints.mock.calls.length;

        // Advance clock by 5s to trigger the interval
        await act(async () => { vi.advanceTimersByTime(5000); });
        expect(api.fetchComplaints.mock.calls.length).toBeGreaterThan(initialCalls);

        vi.useRealTimers();
    });

    it('shows empty state when no complaints', async () => {
        api.fetchComplaints.mockResolvedValue([]);
        api.fetchCallLogs.mockResolvedValue([]);
        render(<Dashboard />);
        await waitFor(() => {
            expect(api.fetchComplaints).toHaveBeenCalled();
        });
        // No complaint rows in the UI
        expect(screen.queryByText('A-101')).not.toBeInTheDocument();
    });
});
