import { useState, useMemo } from 'react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isToday } from 'date-fns';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react';
import { cn } from '@/lib';

function CompactCalendar({ complaints, onDateClick }) {
    const [currentDate, setCurrentDate] = useState(new Date());

    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(currentDate);
    const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });

    const complaintsByDate = useMemo(() => {
        const map = {};
        complaints.forEach(complaint => {
            const date = format(new Date(complaint.created_at), 'yyyy-MM-dd');
            if (!map[date]) map[date] = [];
            map[date].push(complaint);
        });
        return map;
    }, [complaints]);

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
                    const complaintsOnDate = complaintsByDate[dateKey] || [];
                    const hasComplaints = complaintsOnDate.length > 0;
                    const today = isToday(day);

                    return (
                        <button
                            key={dateKey}
                            onClick={() => hasComplaints && onDateClick(day, complaintsOnDate)}
                            disabled={!hasComplaints}
                            className={cn(
                                "aspect-square p-1 rounded-lg text-sm transition-all duration-200",
                                today && "ring-2 ring-primary ring-offset-2 ring-offset-background",
                                hasComplaints
                                    ? "bg-primary/10 text-foreground hover:bg-primary hover:text-primary-foreground cursor-pointer"
                                    : "text-muted-foreground cursor-default",
                                !isSameMonth(day, currentDate) && "opacity-30"
                            )}
                        >
                            <div className="flex flex-col items-center justify-center h-full">
                                <span>{format(day, 'd')}</span>
                                {hasComplaints && (
                                    <span className="text-[10px] font-bold text-primary mt-0.5">
                                        {complaintsOnDate.length}
                                    </span>
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
