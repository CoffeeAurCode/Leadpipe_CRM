import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    startOfMonth, eachDayOfInterval, endOfMonth,
    format, isSameDay, isToday, parseISO,
} from 'date-fns';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { cn } from '@/lib';
import AppointmentDetailModal from './AppointmentDetailModal';
import ComplaintModal from './ComplaintModal';
import './CalendarView.css';

// ── Status colour maps ────────────────────────────────────────────────────────

// For mini-cards inside calendar cells (border-l-2 + subtle bg)
const MINI_STATUS = {
    scheduled:    'border-blue-500   bg-blue-50   text-blue-700',
    in_progress:  'border-orange-500 bg-orange-50 text-orange-700',
    'in progress':'border-orange-500 bg-orange-50 text-orange-700',
    completed:    'border-green-500  bg-green-50  text-green-700',
    resolved:     'border-green-500  bg-green-50  text-green-700',
    attended:     'border-purple-500 bg-purple-50 text-purple-700',
    cancelled:    'border-red-500    bg-red-50    text-red-700',
    canceled:     'border-red-500    bg-red-50    text-red-700',
    pending:      'border-amber-500  bg-amber-50  text-amber-700',
};

// For left border of panel event cards
const PANEL_BORDER = {
    scheduled:    'border-l-blue-500',
    in_progress:  'border-l-orange-500',
    'in progress':'border-l-orange-500',
    completed:    'border-l-green-500',
    resolved:     'border-l-green-500',
    attended:     'border-l-purple-500',
    cancelled:    'border-l-red-500',
    canceled:     'border-l-red-500',
    pending:      'border-l-amber-500',
};

// For status badge pills inside the panel
const BADGE_CLASSES = {
    scheduled:    'bg-blue-100   text-blue-700',
    in_progress:  'bg-orange-100 text-orange-700',
    'in progress':'bg-orange-100 text-orange-700',
    completed:    'bg-green-100  text-green-700',
    resolved:     'bg-green-100  text-green-700',
    attended:     'bg-purple-100 text-purple-700',
    cancelled:    'bg-red-100    text-red-700',
    canceled:     'bg-red-100    text-red-700',
    pending:      'bg-amber-100  text-amber-700',
};

function normalize(status) {
    return (status || '').toLowerCase().trim();
}
function getMiniClasses(status)  { return MINI_STATUS[normalize(status)]  || 'border-gray-400 bg-gray-50 text-gray-600'; }
function getPanelBorder(status)  { return PANEL_BORDER[normalize(status)] || 'border-l-gray-400'; }
function getBadgeClasses(status) { return BADGE_CLASSES[normalize(status)] || 'bg-gray-100 text-gray-600'; }

// ── Constants ─────────────────────────────────────────────────────────────────

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MAX_VISIBLE = 2;

const LEGEND = [
    { label: 'Scheduled',   color: 'bg-blue-500' },
    { label: 'In Progress', color: 'bg-orange-500' },
    { label: 'Completed',   color: 'bg-green-500' },
    { label: 'Attended',    color: 'bg-purple-500' },
    { label: 'Cancelled',   color: 'bg-red-500' },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function CalendarView({
    complaints = [],
    appointments = [],
    onComplaintUpdate,
    onAppointmentUpdate,
    onAppointmentDelete,
}) {
    const [currentDate, setCurrentDate]   = useState(new Date());
    const [selectedDate, setSelectedDate] = useState(null);
    const [hoveredDate, setHoveredDate]   = useState(null);
    const [activeEvent, setActiveEvent]   = useState(null); // event clicked in panel

    // Month days array
    const monthDays = useMemo(() => eachDayOfInterval({
        start: startOfMonth(currentDate),
        end:   endOfMonth(currentDate),
    }), [currentDate]);

    // How many blank cells before day 1
    const startOffset = useMemo(() => startOfMonth(currentDate).getDay(), [currentDate]);

    // Merge appointments + complaints for a given day
    function getEventsForDate(date) {
        const appts = appointments.filter(a => {
            try { return a.appointment_date && isSameDay(parseISO(a.appointment_date), date); }
            catch { return false; }
        }).map(a => ({ ...a, _type: 'appointment' }));

        const comps = complaints.filter(c => {
            try { return c.created_at && isSameDay(parseISO(c.created_at), date); }
            catch { return false; }
        }).map(c => ({ ...c, _type: 'complaint' }));

        return [...appts, ...comps];
    }

    // Events for the open panel
    const panelEvents = useMemo(
        () => (selectedDate ? getEventsForDate(selectedDate) : []),
        [selectedDate, appointments, complaints]
    );

    // Navigation
    const goToPrev  = () => { setCurrentDate(d => new Date(d.getFullYear(), d.getMonth() - 1, 1)); setSelectedDate(null); };
    const goToNext  = () => { setCurrentDate(d => new Date(d.getFullYear(), d.getMonth() + 1, 1)); setSelectedDate(null); };
    const goToToday = () => { setCurrentDate(new Date()); setSelectedDate(null); };

    const closePanel = () => { setSelectedDate(null); setActiveEvent(null); };

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-4">

            {/* ── Header ── */}
            <div data-tour="calendar-header" className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-foreground">
                    {format(currentDate, 'MMMM yyyy')}
                </h1>
                <div className="flex items-center gap-2">
                    <button
                        onClick={goToToday}
                        className="px-3 py-1.5 text-sm font-medium border border-border rounded-lg hover:bg-secondary transition-colors text-foreground"
                    >
                        Today
                    </button>
                    <button onClick={goToPrev} className="p-1.5 border border-border rounded-lg hover:bg-secondary transition-colors">
                        <ChevronLeft className="w-4 h-4 text-foreground" />
                    </button>
                    <button onClick={goToNext} className="p-1.5 border border-border rounded-lg hover:bg-secondary transition-colors">
                        <ChevronRight className="w-4 h-4 text-foreground" />
                    </button>
                </div>
            </div>

            {/* ── Control Bar ── */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                {/* View label */}
                <div className="flex items-center gap-1 bg-secondary rounded-lg p-1">
                    <span className="px-3 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground shadow-sm">
                        Month
                    </span>
                </div>

                {/* Filter placeholders */}
                <div className="flex items-center gap-2">
                    <select className="text-sm border border-border rounded-lg px-3 py-1.5 bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary">
                        <option>All Properties</option>
                    </select>
                    <select className="text-sm border border-border rounded-lg px-3 py-1.5 bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary">
                        <option>All Types</option>
                    </select>
                </div>
            </div>

            {/* ── Legend ── */}
            <div className="flex items-center gap-5 flex-wrap">
                {LEGEND.map(({ label, color }) => (
                    <div key={label} className="flex items-center gap-1.5">
                        <span className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0', color)} />
                        <span className="text-xs text-muted-foreground">{label}</span>
                    </div>
                ))}
            </div>

            {/* ── Calendar Grid ── */}
            <div data-tour="calendar-grid" className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">

                {/* Weekday headers */}
                <div className="grid grid-cols-7 border-b border-border">
                    {WEEKDAYS.map(d => (
                        <div key={d} className="py-2.5 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                            {d}
                        </div>
                    ))}
                </div>

                {/* Day cells */}
                <div className="grid grid-cols-7 gap-px bg-border p-px">
                    {/* Empty offset cells */}
                    {Array.from({ length: startOffset }).map((_, i) => (
                        <div key={`empty-${i}`} className="bg-card min-h-[90px]" />
                    ))}

                    {monthDays.map(day => {
                        const events   = getEventsForDate(day);
                        const visible  = events.slice(0, MAX_VISIBLE);
                        const overflow = events.length - MAX_VISIBLE;
                        const isSelected  = selectedDate && isSameDay(day, selectedDate);
                        const isTodayDay  = isToday(day);
                        const isHovered   = hoveredDate && isSameDay(day, hoveredDate);

                        return (
                            <div
                                key={day.toString()}
                                className={cn(
                                    'relative min-h-[90px] p-1.5 bg-card cursor-pointer transition-colors duration-100',
                                    isTodayDay  && !isSelected && 'bg-primary/5',
                                    isSelected  ? 'bg-primary/10' : 'hover:bg-secondary/50',
                                )}
                                onClick={() => setSelectedDate(isSelected ? null : day)}
                                onMouseEnter={() => events.length > 0 && setHoveredDate(day)}
                                onMouseLeave={() => setHoveredDate(null)}
                            >
                                {/* Day number */}
                                <div className={cn(
                                    'w-6 h-6 flex items-center justify-center rounded-full text-xs font-semibold mb-1',
                                    isTodayDay
                                        ? 'bg-primary text-primary-foreground'
                                        : isSelected
                                            ? 'text-primary font-bold'
                                            : 'text-foreground'
                                )}>
                                    {format(day, 'd')}
                                </div>

                                {/* Event mini-cards */}
                                {visible.map((evt, idx) => (
                                    <div
                                        key={`${evt._type}-${evt.id}-${idx}`}
                                        className={cn(
                                            'text-[10px] truncate rounded px-1 py-0.5 mb-0.5 border-l-2 leading-tight',
                                            getMiniClasses(evt.status)
                                        )}
                                    >
                                        {evt._type === 'appointment'
                                            ? `${format(parseISO(evt.appointment_date), 'HH:mm')} ${evt.flat_number || '?'}`
                                            : `#${evt.id} ${evt.flat_number || '?'}`
                                        }
                                    </div>
                                ))}

                                {/* Overflow badge */}
                                {overflow > 0 && (
                                    <div className="text-[10px] text-muted-foreground font-medium px-1">
                                        +{overflow} more
                                    </div>
                                )}

                                {/* Hover tooltip — opaque bg-card */}
                                {isHovered && !isSelected && events.length > 0 && (
                                    <div className="absolute bottom-full left-0 mb-1 z-20 w-52 bg-card border border-border rounded-lg shadow-xl p-2.5 pointer-events-none">
                                        <p className="text-xs font-semibold text-foreground mb-1.5">{format(day, 'MMM d')}</p>
                                        {events.slice(0, 5).map((evt, idx) => (
                                            <div key={idx} className="text-[10px] text-muted-foreground truncate py-0.5 flex items-center gap-1">
                                                <span>{evt._type === 'appointment' ? '📅' : '💬'}</span>
                                                <span>
                                                    {evt._type === 'appointment'
                                                        ? `${format(parseISO(evt.appointment_date), 'HH:mm')} · Flat ${evt.flat_number || '?'}`
                                                        : `#${evt.id} · Flat ${evt.flat_number || '?'} · ${evt.category || 'complaint'}`
                                                    }
                                                </span>
                                            </div>
                                        ))}
                                        {events.length > 5 && (
                                            <div className="text-[10px] text-muted-foreground mt-1">+{events.length - 5} more</div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* ── Slide-Over Panel ── */}
            <AnimatePresence>
                {selectedDate && (
                    <>
                        {/* Backdrop */}
                        <motion.div
                            key="backdrop"
                            className="fixed inset-0 bg-black/25 z-30"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            onClick={closePanel}
                        />

                        {/* Panel */}
                        <motion.div
                            key="panel"
                            className="fixed right-0 top-0 h-screen w-96 bg-card border-l border-border shadow-2xl z-40 flex flex-col"
                            initial={{ x: '100%' }}
                            animate={{ x: 0 }}
                            exit={{ x: '100%' }}
                            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
                        >
                            {/* Panel Header */}
                            <div className="flex items-center justify-between px-5 py-4 border-b border-border flex-shrink-0">
                                <div>
                                    <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                                        {format(selectedDate, 'EEEE')}
                                    </p>
                                    <h2 className="text-lg font-bold text-foreground leading-tight">
                                        {format(selectedDate, 'MMMM d, yyyy')}
                                    </h2>
                                </div>
                                <button
                                    onClick={closePanel}
                                    className="p-1.5 rounded-lg hover:bg-secondary transition-colors"
                                >
                                    <X className="w-5 h-5 text-muted-foreground" />
                                </button>
                            </div>

                            {/* Panel Body */}
                            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
                                {panelEvents.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center h-52 text-center">
                                        <div className="text-5xl mb-3 select-none">📭</div>
                                        <p className="text-sm font-semibold text-foreground">No events on this day</p>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            No appointments or complaints recorded
                                        </p>
                                    </div>
                                ) : (
                                    <>
                                        <p className="text-xs text-muted-foreground font-medium">
                                            {panelEvents.length} event{panelEvents.length !== 1 ? 's' : ''} — click a card to view or edit
                                        </p>
                                        {panelEvents.map((evt, idx) => (
                                            <div
                                                key={`${evt._type}-${evt.id}-${idx}`}
                                                className={cn(
                                                    'p-3 rounded-lg border border-border border-l-4 bg-background',
                                                    'cursor-pointer hover:bg-secondary/50 transition-colors',
                                                    getPanelBorder(evt.status)
                                                )}
                                                onClick={() => setActiveEvent(evt)}
                                            >
                                                {evt._type === 'appointment' ? (
                                                    <>
                                                        <div className="flex items-center justify-between mb-1.5">
                                                            <span className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                                                                Appointment
                                                            </span>
                                                            <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize', getBadgeClasses(evt.status))}>
                                                                {evt.status}
                                                            </span>
                                                        </div>
                                                        <p className="text-sm font-semibold text-foreground">
                                                            {format(parseISO(evt.appointment_date), 'h:mm a')} · Flat {evt.flat_number || 'N/A'}
                                                        </p>
                                                        {(evt.complaint_category || evt.category) && (
                                                            <p className="text-xs text-muted-foreground mt-1">
                                                                {evt.complaint_category || evt.category}
                                                            </p>
                                                        )}
                                                        {evt.notes && (
                                                            <p className="text-xs text-muted-foreground mt-1 italic line-clamp-2">
                                                                {evt.notes}
                                                            </p>
                                                        )}
                                                    </>
                                                ) : (
                                                    <>
                                                        <div className="flex items-center justify-between mb-1.5">
                                                            <span className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                                                                Complaint #{evt.id}
                                                            </span>
                                                            <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize', getBadgeClasses(evt.status))}>
                                                                {evt.status}
                                                            </span>
                                                        </div>
                                                        <p className="text-sm font-semibold text-foreground">
                                                            Flat {evt.flat_number || 'N/A'}
                                                        </p>
                                                        {evt.category && (
                                                            <p className="text-xs text-muted-foreground mt-1">{evt.category}</p>
                                                        )}
                                                        {evt.description && (
                                                            <p className="text-xs text-muted-foreground mt-1 line-clamp-3">{evt.description}</p>
                                                        )}
                                                    </>
                                                )}
                                            </div>
                                        ))}
                                    </>
                                )}
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* ── Event Detail Modals ── */}
            {activeEvent?._type === 'appointment' && (
                <AppointmentDetailModal
                    appointment={activeEvent}
                    isOpen={true}
                    onClose={() => setActiveEvent(null)}
                    onUpdate={onAppointmentUpdate}
                    onDelete={onAppointmentDelete}
                />
            )}
            {activeEvent?._type === 'complaint' && (
                <ComplaintModal
                    complaint={activeEvent}
                    onClose={() => setActiveEvent(null)}
                    onUpdate={onComplaintUpdate}
                />
            )}
        </div>
    );
}
