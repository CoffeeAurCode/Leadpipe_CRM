import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { subDays, format, parseISO, isToday } from 'date-fns';
import { TrendingUp, Clock, AlertCircle, CalendarCheck } from 'lucide-react';
import { cn } from '@/lib';
import DashboardListModal from './dashboard/DashboardListModal';
import DailyTasksModal from './dashboard/DailyTasksModal';
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

function BentoDashboard({ complaints, appointments = [], onComplaintUpdate, onAppointmentUpdate, onAppointmentDelete }) {
    const { t } = useTranslation();
    const [timeRange, setTimeRange] = useState('7d');
    const [activeModal, setActiveModal] = useState(null); // { title, complaints }
    const [showDailyTasks, setShowDailyTasks] = useState(false);

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
        { name: t('complaints.status.pending'),    value: filteredByTime.filter(c => c.status === STATUS.PENDING).length },
        { name: t('complaints.status.inProgress'), value: filteredByTime.filter(c => c.status === STATUS.IN_PROGRESS).length },
        { name: t('complaints.status.resolved'),   value: filteredByTime.filter(c => c.status === STATUS.RESOLVED).length },
    ], [filteredByTime, t]);

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

    const openKpiModal = (title, list) => setActiveModal({ title, complaints: list });
    const closeKpiModal = () => setActiveModal(null);

    const todayAppointments = useMemo(() => appointments.filter(a => {
        try { return a.appointment_date && isToday(parseISO(a.appointment_date)); }
        catch { return false; }
    }), [appointments]);

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
                    <h1 className="text-2xl font-bold text-foreground">{t('nav.dashboard')}</h1>
                    <p className="text-sm text-muted-foreground mt-0.5">{t('dashboard.subtitle')}</p>
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
            <div data-tour="kpi-cards" className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KPICard
                    label={t('dashboard.kpi.totalComplaints')}
                    value={kpis.total}
                    icon={TrendingUp}
                    delay={0.05}
                    onClick={() => openKpiModal(t('dashboard.kpi.totalComplaintsModal', { range: timeRange }), filteredByTime)}
                />
                <KPICard
                    label={t('complaints.status.pending')}
                    value={kpis.pending}
                    icon={Clock}
                    iconColor="text-amber-500"
                    delay={0.1}
                    onClick={() => openKpiModal(t('dashboard.kpi.pendingModal', { range: timeRange }), filteredByTime.filter(c => c.status === STATUS.PENDING))}
                />
                <KPICard
                    label={t('complaints.status.inProgress')}
                    value={kpis.inProgress}
                    icon={AlertCircle}
                    iconColor="text-blue-500"
                    delay={0.15}
                    onClick={() => openKpiModal(t('dashboard.kpi.inProgressModal', { range: timeRange }), filteredByTime.filter(c => c.status === STATUS.IN_PROGRESS))}
                />
                <KPICard
                    label={t('dashboard.kpi.dailyTasks')}
                    value={kpis.appointmentsToday}
                    icon={CalendarCheck}
                    iconColor="text-emerald-500"
                    delay={0.2}
                    onClick={() => setShowDailyTasks(true)}
                />
            </div>

            {/* ── Charts Row 1: Trends + Status Donut ── */}
            <motion.div
                data-tour="trends-charts"
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
                data-tour="category-charts"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-4"
            >
                <CategoriesPie data={categoriesData} />
                <AppointmentsBar data={appointmentsBarData} />
            </motion.div>

            {/* ── Modals ── */}
            <AnimatePresence>
                {activeModal && (
                    <DashboardListModal
                        title={activeModal.title}
                        complaints={activeModal.complaints}
                        onClose={closeKpiModal}
                    />
                )}
                {showDailyTasks && (
                    <DailyTasksModal
                        appointments={todayAppointments}
                        onClose={() => setShowDailyTasks(false)}
                        onAppointmentUpdate={onAppointmentUpdate}
                        onAppointmentDelete={onAppointmentDelete}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

export default BentoDashboard;
