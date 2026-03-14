import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { subDays, format, parseISO, isToday } from 'date-fns';
import { TrendingUp, Clock, AlertCircle, CalendarCheck } from 'lucide-react';
import { cn } from '@/lib';
import QuickFilters from './QuickFilters';
import CompactComplaintCard from './CompactComplaintCard';
import ComplaintModal from './ComplaintModal';
import KPICard from './dashboard/KPICard';
import TrendsChart from './dashboard/TrendsChart';
import StatusDonut from './dashboard/StatusDonut';
import CategoriesPie from './dashboard/CategoriesPie';
import AppointmentsBar from './dashboard/AppointmentsBar';
import { STATUS } from '../constants/status';

const TIME_RANGES = [
    { label: '7d', days: 7 },
    { label: '30d', days: 30 },
    { label: '3m', days: 90 },
];

const DAY_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function BentoDashboard({ complaints, appointments = [], onComplaintUpdate }) {
    const [filters, setFilters] = useState({ status: 'all', priority: 'all' });
    const [timeRange, setTimeRange] = useState('7d');
    const [selectedComplaint, setSelectedComplaint] = useState(null);

    // Filter complaints based on active filters
    const filteredComplaints = useMemo(() => {
        return complaints.filter(complaint => {
            const matchesStatus = filters.status === 'all' || complaint.status === filters.status;
            const matchesPriority = filters.priority === 'all' || complaint.priority === filters.priority;
            return matchesStatus && matchesPriority;
        });
    }, [complaints, filters]);

    // ── Analytics data (time-range filtered) ──────────────────────────────────

    const cutoff = useMemo(() => {
        const days = TIME_RANGES.find(r => r.label === timeRange)?.days ?? 7;
        return subDays(new Date(), days);
    }, [timeRange]);

    const filteredByTime = useMemo(
        () => complaints.filter(c => new Date(c.created_at) >= cutoff),
        [complaints, cutoff]
    );

    const kpis = useMemo(() => ({
        total: filteredByTime.length,
        pending: filteredByTime.filter(c => c.status === STATUS.PENDING).length,
        inProgress: filteredByTime.filter(c => c.status === STATUS.IN_PROGRESS).length,
        appointmentsToday: appointments.filter(a => {
            try { return a.appointment_date && isToday(parseISO(a.appointment_date)); }
            catch { return false; }
        }).length,
    }), [filteredByTime, appointments]);

    const trendsData = useMemo(() => {
        const grouped = new Map();
        [...filteredByTime]
            .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
            .forEach(c => {
                try {
                    const d = format(parseISO(c.created_at.endsWith('Z') ? c.created_at : c.created_at + 'Z'), 'MMM dd');
                    grouped.set(d, (grouped.get(d) || 0) + 1);
                } catch { /* skip malformed dates */ }
            });
        return Array.from(grouped.entries()).map(([date, complaints]) => ({ date, complaints }));
    }, [filteredByTime]);

    const statusData = useMemo(() => [
        { name: 'Pending',     value: filteredByTime.filter(c => c.status === STATUS.PENDING).length },
        { name: 'In Progress', value: filteredByTime.filter(c => c.status === STATUS.IN_PROGRESS).length },
        { name: 'Resolved',    value: filteredByTime.filter(c => c.status === STATUS.RESOLVED).length },
    ], [filteredByTime]);

    const categoriesData = useMemo(() => {
        const counts = {};
        filteredByTime.forEach(c => {
            if (c.category) counts[c.category] = (counts[c.category] || 0) + 1;
        });
        return Object.entries(counts)
            .sort(([, a], [, b]) => b - a)
            .map(([name, value]) => ({ name, value }));
    }, [filteredByTime]);

    const appointmentsBarData = useMemo(() => {
        const counts = Object.fromEntries(DAY_ORDER.map(d => [d, 0]));
        appointments
            .filter(a => {
                try { return a.appointment_date && new Date(a.appointment_date) >= cutoff; }
                catch { return false; }
            })
            .forEach(a => {
                try {
                    const day = format(parseISO(a.appointment_date), 'EEE');
                    if (day in counts) counts[day]++;
                } catch { /* skip */ }
            });
        return DAY_ORDER.map(day => ({ day, count: counts[day] }));
    }, [appointments, cutoff]);

    // ── End analytics ──────────────────────────────────────────────────────────

    const openComplaintModal = (complaint) => setSelectedComplaint(complaint);
    const closeComplaintModal = () => setSelectedComplaint(null);

    return (
        <div className="space-y-6">

            {/* ── Page Header ── */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="flex items-center justify-between"
            >
                <div>
                    <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
                    <p className="text-sm text-muted-foreground mt-0.5">Tenant complaint management overview</p>
                </div>
                <div className="flex gap-1 bg-secondary rounded-lg p-1">
                    {TIME_RANGES.map(r => (
                        <button
                            key={r.label}
                            onClick={() => setTimeRange(r.label)}
                            className={cn(
                                'px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200',
                                timeRange === r.label
                                    ? 'bg-primary text-primary-foreground shadow-sm'
                                    : 'text-muted-foreground hover:text-foreground'
                            )}
                        >
                            {r.label}
                        </button>
                    ))}
                </div>
            </motion.div>

            {/* ── KPI Row ── */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KPICard label="Total Complaints" value={kpis.total}              icon={TrendingUp}   delay={0.05} />
                <KPICard label="Pending"          value={kpis.pending}            icon={Clock}        iconColor="text-amber-500"   delay={0.1} />
                <KPICard label="In Progress"      value={kpis.inProgress}         icon={AlertCircle}  iconColor="text-blue-500"    delay={0.15} />
                <KPICard label="Appts Today"      value={kpis.appointmentsToday}  icon={CalendarCheck} iconColor="text-emerald-500" delay={0.2} />
            </div>

            {/* ── Charts Row 1: Trends + Status Donut ── */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
                className="grid grid-cols-1 lg:grid-cols-3 gap-4"
            >
                <div className="lg:col-span-2">
                    <TrendsChart data={trendsData} />
                </div>
                <div className="lg:col-span-1">
                    <StatusDonut data={statusData} />
                </div>
            </motion.div>

            {/* ── Charts Row 2: Categories + Appointments ── */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-4"
            >
                <CategoriesPie data={categoriesData} />
                <AppointmentsBar data={appointmentsBarData} />
            </motion.div>

            {/* ── All Complaints ── */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.45 }}
                className="space-y-3"
            >
                <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-foreground">
                        All Complaints
                        <span className="ml-2 text-sm font-normal text-muted-foreground">
                            ({filters.status !== 'all' || filters.priority !== 'all'
                                ? `${filteredComplaints.length} filtered`
                                : `${complaints.length} total`})
                        </span>
                    </h3>
                </div>
                <QuickFilters filters={filters} onFilterChange={setFilters} />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredComplaints.map(complaint => (
                        <CompactComplaintCard
                            key={complaint.id}
                            complaint={complaint}
                            onClick={() => openComplaintModal(complaint)}
                            onUpdate={onComplaintUpdate}
                        />
                    ))}
                    {filteredComplaints.length === 0 && (
                        <div className="col-span-3 flex items-center justify-center h-32 rounded-lg border border-border bg-card">
                            <p className="text-muted-foreground text-sm">No complaints match the current filters</p>
                        </div>
                    )}
                </div>
            </motion.div>

            {/* ── Modals ── */}
            <AnimatePresence>
                {selectedComplaint && (
                    <ComplaintModal
                        complaint={selectedComplaint}
                        onClose={closeComplaintModal}
                        onUpdate={onComplaintUpdate}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

export default BentoDashboard;

