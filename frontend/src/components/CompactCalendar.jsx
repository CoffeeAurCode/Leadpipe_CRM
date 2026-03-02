import { useState, useMemo, useEffect } from 'react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isToday, isSameDay, parseISO, isFuture } from 'date-fns';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react';
import { cn } from '@/lib';
import { api } from '../services/api';

function CompactCalendar({ complaints, onDateClick }) {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [appointments, setAppointments] = useState([]);
    const [loading, setLoading] = useState(false);

    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(currentDate);
    const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });

    // Fetch appointments when month changes and listen for refresh events
    useEffect(() => {
        fetchAppointments();

        window.addEventListener('refresh-calendar', fetchAppointments);
        return () => window.removeEventListener('refresh-calendar', fetchAppointments);
    }, [currentDate]);

    const fetchAppointments = async () => {
        setLoading(true);
        try {
            const data = await api.fetchAppointments({
                start_date: monthStart.toISOString(),
                end_date: monthEnd.toISOString()
            });
            setAppointments(data || []);
        } catch (error) {
            console.error('Failed to fetch appointments:', error);
            setAppointments([]);
        } finally {
            setLoading(false);
        }
    };

    // Merge complaints (by appointment_date) and standalone appointments
    const itemsByDate = useMemo(() => {
        const map = {};

        // Add complaints with appointment dates
        complaints.forEach(complaint => {
            const relevantDate = complaint.appointment_date
                ? parseISO(complaint.appointment_date)
                : parseISO(complaint.created_at);
            const dateKey = format(relevantDate, 'yyyy-MM-dd');
            if (!map[dateKey]) map[dateKey] = [];
            map[dateKey].push({ ...complaint, type: 'complaint' });
        });

        // Add standalone appointments
        appointments.forEach(appointment => {
            const appointmentDate = parseISO(appointment.appointment_date);
            const dateKey = format(appointmentDate, 'yyyy-MM-dd');
            if (!map[dateKey]) map[dateKey] = [];
            map[dateKey].push({ ...appointment, type: 'appointment' });
        });

        return map;
    }, [complaints, appointments]);

    const previousMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1));
    };

    const nextMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1));
    };

    return (
        <div className="bg-card border border-border rounded-lg p-6 h-full">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <CalendarIcon className="w-5 h-5 text-primary" />
                    <h3 className="text-lg font-semibold text-foreground">
                        {format(currentDate, 'MMMM yyyy')}
                    </h3>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={previousMonth}
                        className="p-2 rounded-lg hover:bg-secondary transition-colors"
                    >
                        <ChevronLeft className="w-4 h-4 text-muted-foreground" />
                    </button>
                    <button
                        onClick={nextMonth}
                        className="p-2 rounded-lg hover:bg-secondary transition-colors"
                    >
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    </button>
                </div>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-3 mb-3 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-primary/20"></div>
                    <span>Scheduled visits</span>
                </div>
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-1">
                {/* Weekday headers */}
                {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, i) => (
                    <div key={i} className="text-center text-xs font-medium text-muted-foreground py-2">
                        {day}
                    </div>
                ))}

                {/* Calendar days */}
                {daysInMonth.map((day) => {
                    const dateKey = format(day, 'yyyy-MM-dd');
                    const itemsOnDate = itemsByDate[dateKey] || [];
                    const hasItems = itemsOnDate.length > 0;
                    const today = isToday(day);
                    const futureDate = isFuture(day) || isToday(day);

                    return (
                        <button
                            key={dateKey}
                            onClick={() => onDateClick(day, itemsOnDate)}
                            className={cn(
                                "aspect-square p-1 rounded-lg text-sm transition-all duration-200",
                                today && "ring-2 ring-primary ring-offset-2 ring-offset-background",
                                hasItems
                                    ? "bg-primary/10 text-foreground hover:bg-primary hover:text-primary-foreground cursor-pointer font-semibold"
                                    : futureDate
                                        ? "text-foreground hover:bg-secondary cursor-pointer"
                                        : "text-muted-foreground hover:bg-secondary/50 cursor-pointer",
                                !isSameMonth(day, currentDate) && "opacity-30"
                            )}
                        >
                            <div className="flex flex-col items-center justify-center h-full">
                                <span>{format(day, 'd')}</span>
                                {hasItems && (
                                    <div className="flex items-center gap-0.5 mt-0.5">
                                        <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
                                        <span className="text-[10px] font-bold text-primary">
                                            {itemsOnDate.length}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

export default CompactCalendar;
