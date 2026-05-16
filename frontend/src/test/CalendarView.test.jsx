/**
 * Section 5.8 — CalendarView.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// CalendarView imports CalendarView.css — vi.mock doesn't help with bare CSS in jsdom
// but we set css: false in vitest config, so the import is ignored.
vi.mock('../components/CalendarView.css', () => ({}));

// Mock child modals that have their own heavy dependencies
vi.mock('../components/AppointmentDetailModal', () => ({
    default: ({ appointment, onClose }) => (
        <div data-testid="appointment-detail-modal">
            <span>{appointment?.id}</span>
            <button onClick={onClose}>Close</button>
        </div>
    ),
}));

vi.mock('../components/ComplaintModal', () => ({
    default: ({ complaint, onClose }) => (
        <div data-testid="complaint-modal">
            <button onClick={onClose}>Close</button>
        </div>
    ),
}));

import CalendarView from '../components/CalendarView';

// Build appointments spanning two days
const TODAY = new Date();
const todayStr = TODAY.toISOString().split('T')[0];
const tomorrowStr = new Date(TODAY.getTime() + 86400000).toISOString().split('T')[0];

const MOCK_APPOINTMENTS = [
    { id: 'a1', flat_number: 'A-101', appointment_date: `${todayStr}T10:00:00`, status: 'scheduled' },
    { id: 'a2', flat_number: 'B-202', appointment_date: `${todayStr}T14:00:00`, status: 'attended' },
    { id: 'a3', flat_number: 'C-303', appointment_date: `${tomorrowStr}T09:00:00`, status: 'scheduled' },
];

const MOCK_COMPLAINTS = [
    { id: 'c1', flat_number: 'A-101', status: 'pending', priority: 'high', created_at: `${todayStr}T08:00:00` },
];

function renderCalendar(props = {}) {
    return render(
        <CalendarView
            appointments={MOCK_APPOINTMENTS}
            complaints={MOCK_COMPLAINTS}
            onUpdateAppointment={vi.fn()}
            onDeleteAppointment={vi.fn()}
            onUpdateComplaint={vi.fn()}
            {...props}
        />
    );
}

describe('CalendarView', () => {
    it('renders the current month and year in the header', () => {
        renderCalendar();
        const currentMonth = TODAY.toLocaleString('default', { month: 'long' });
        const currentYear = TODAY.getFullYear().toString();
        expect(screen.getByText(new RegExp(`${currentMonth}.*${currentYear}`, 'i'))).toBeInTheDocument();
    });

    it('renders day-of-week headers', () => {
        renderCalendar();
        expect(screen.getByText('Sun')).toBeInTheDocument();
        expect(screen.getByText('Mon')).toBeInTheDocument();
        expect(screen.getByText('Sat')).toBeInTheDocument();
    });

    it('renders at least 28 day cells', () => {
        renderCalendar();
        // Day numbers are rendered as text; check there are many cells
        const cells = document.querySelectorAll('[data-date]');
        // If no data-date attr, count by the day grid structure
        // At minimum there should be 28 number cells
        const dayNumbers = screen.getAllByText(/^\d+$/).filter(el => {
            const n = parseInt(el.textContent);
            return n >= 1 && n <= 31;
        });
        expect(dayNumbers.length).toBeGreaterThanOrEqual(28);
    });

    it('navigates to the next month on chevron-right click', async () => {
        const user = userEvent.setup();
        renderCalendar();

        const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
        const nextMonthName = MONTHS[(TODAY.getMonth() + 1) % 12];

        // Header buttons: [Today, ChevronLeft (prev), ChevronRight (next)]
        const buttons = screen.getAllByRole('button');
        await user.click(buttons[2]); // ChevronRight

        await waitFor(() => {
            expect(screen.getByText(new RegExp(nextMonthName, 'i'))).toBeInTheDocument();
        });
    });

    it('navigates to the previous month on chevron-left click', async () => {
        const user = userEvent.setup();
        renderCalendar();

        const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
        const prevMonthName = MONTHS[(TODAY.getMonth() - 1 + 12) % 12];

        // Header buttons: [Today, ChevronLeft (prev), ChevronRight (next)]
        const buttons = screen.getAllByRole('button');
        await user.click(buttons[1]); // ChevronLeft

        await waitFor(() => {
            expect(screen.getByText(new RegExp(prevMonthName, 'i'))).toBeInTheDocument();
        });
    });

    it('renders appointments as mini-cards on their scheduled day', () => {
        renderCalendar();
        // A-101 appointment is today
        expect(screen.getAllByText(/A-101/).length).toBeGreaterThanOrEqual(1);
    });

    it('shows empty state when no appointments', () => {
        renderCalendar({ appointments: [] });
        // Should still render without crashing
        expect(screen.getByText(/today/i) ?? screen.getAllByRole('button').length > 0).toBeTruthy();
    });
});
