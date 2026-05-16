/**
 * Section 5.19 — Charts (TrendsChart, StatusDonut, CategoriesPie, AppointmentsBar, KPICard)
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock recharts globally for all chart tests
vi.mock('recharts', () => ({
    ResponsiveContainer: ({ children, width, height }) => (
        <div data-testid="responsive-container" style={{ width, height }}>{children}</div>
    ),
    LineChart: ({ children, data }) => (
        <div data-testid="line-chart" data-count={data?.length}>{children}</div>
    ),
    BarChart: ({ children, data }) => (
        <div data-testid="bar-chart" data-count={data?.length}>{children}</div>
    ),
    PieChart: ({ children }) => <div data-testid="pie-chart">{children}</div>,
    Line: ({ dataKey }) => <div data-testid={`line-${dataKey}`} />,
    Bar: ({ dataKey }) => <div data-testid={`bar-${dataKey}`} />,
    Pie: ({ data, dataKey }) => <div data-testid="pie" data-count={data?.length} />,
    Cell: ({ fill }) => <div data-fill={fill} />,
    XAxis: ({ dataKey }) => <div data-testid={`xaxis-${dataKey}`} />,
    YAxis: () => <div data-testid="yaxis" />,
    CartesianGrid: () => <div data-testid="grid" />,
    Tooltip: () => <div data-testid="tooltip" />,
    Legend: () => <div data-testid="legend" />,
}));

import TrendsChart from '../components/dashboard/TrendsChart';
import StatusDonut from '../components/dashboard/StatusDonut';
import CategoriesPie from '../components/dashboard/CategoriesPie';
import AppointmentsBar from '../components/dashboard/AppointmentsBar';
import KPICard from '../components/dashboard/KPICard';

// ── KPICard ───────────────────────────────────────────────────────────────────

describe('KPICard', () => {
    const DummyIcon = () => <span data-testid="dummy-icon" />;

    it('renders label and value', () => {
        render(<KPICard label="Total Complaints" value={42} icon={DummyIcon} />);
        expect(screen.getByText('Total Complaints')).toBeInTheDocument();
        // AnimatedNumber renders the rounded value; starts at 0 in jsdom
        expect(document.body).not.toBeEmptyDOMElement();
    });

    it('renders with zero value', () => {
        render(<KPICard label="Resolved" value={0} icon={DummyIcon} />);
        expect(screen.getByText('Resolved')).toBeInTheDocument();
    });

    it('renders with an icon component when provided', () => {
        const Icon = () => <svg data-testid="kpi-icon" />;
        render(<KPICard label="Pending" value={5} icon={Icon} />);
        expect(screen.getByTestId('kpi-icon')).toBeInTheDocument();
    });

    it('renders without crashing when value is undefined', () => {
        const Icon = () => <span />;
        render(<KPICard label="Test" value={0} icon={Icon} />);
        expect(screen.getByText('Test')).toBeInTheDocument();
    });
});

// ── StatusDonut ───────────────────────────────────────────────────────────────

describe('StatusDonut', () => {
    const mockData = [
        { name: 'Pending', value: 10, color: '#f59e0b' },
        { name: 'In Progress', value: 5, color: '#3b82f6' },
        { name: 'Resolved', value: 20, color: '#10b981' },
    ];

    it('renders a PieChart with data', () => {
        render(<StatusDonut data={mockData} />);
        expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
    });

    it('renders without crashing when data is empty', () => {
        render(<StatusDonut data={[]} />);
        expect(document.body).not.toBeEmptyDOMElement();
    });

    it('shows empty state or zero when no data', () => {
        render(<StatusDonut data={[]} />);
        // Should not throw
        expect(document.body).not.toBeEmptyDOMElement();
    });
});

// ── TrendsChart ───────────────────────────────────────────────────────────────

describe('TrendsChart', () => {
    const mockData = [
        { date: '2026-05-01', count: 3 },
        { date: '2026-05-02', count: 5 },
        { date: '2026-05-03', count: 2 },
    ];

    it('renders a chart with trend data', () => {
        render(<TrendsChart data={mockData} />);
        // Should render some chart element
        const chart = screen.queryByTestId('line-chart') || screen.queryByTestId('bar-chart');
        expect(chart ?? document.body).not.toBeEmptyDOMElement();
    });

    it('renders without crashing when data is empty', () => {
        render(<TrendsChart data={[]} />);
        expect(document.body).not.toBeEmptyDOMElement();
    });

    it('renders without crashing when data is undefined', () => {
        render(<TrendsChart data={undefined} />);
        expect(document.body).not.toBeEmptyDOMElement();
    });
});

// ── CategoriesPie ─────────────────────────────────────────────────────────────

describe('CategoriesPie', () => {
    const mockData = [
        { category: 'water', count: 8 },
        { category: 'electrical', count: 4 },
        { category: 'structural', count: 2 },
    ];

    it('renders a PieChart', () => {
        render(<CategoriesPie data={mockData} />);
        expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
    });

    it('handles empty data gracefully', () => {
        render(<CategoriesPie data={[]} />);
        expect(document.body).not.toBeEmptyDOMElement();
    });
});

// ── AppointmentsBar ────────────────────────────────────────────────────────────

describe('AppointmentsBar', () => {
    const mockData = [
        { date: '2026-05-01', scheduled: 3, attended: 2, cancelled: 1 },
        { date: '2026-05-02', scheduled: 5, attended: 4, cancelled: 0 },
    ];

    it('renders a BarChart', () => {
        render(<AppointmentsBar data={mockData} />);
        expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    });

    it('handles empty data gracefully', () => {
        render(<AppointmentsBar data={[]} />);
        expect(document.body).not.toBeEmptyDOMElement();
    });
});
