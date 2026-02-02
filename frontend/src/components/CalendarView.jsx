import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { startOfMonth, endOfMonth, eachDayOfInterval, format, isSameDay, isToday, parseISO } from 'date-fns';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import './CalendarView.css';

export default function CalendarView({ complaints }) {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedDate, setSelectedDate] = useState(null);

    // Get month days
    const monthDays = useMemo(() => {
        const start = startOfMonth(currentDate);
        const end = endOfMonth(currentDate);
        return eachDayOfInterval({ start, end });
    }, [currentDate]);

    // Get complaints for a specific date
    const getComplaintsForDate = (date) => {
        return complaints.filter(complaint => {
            const complaintDate = parseISO(complaint.created_at);
            return isSameDay(complaintDate, date);
        });
    };

    // Get selected date complaints
    const selectedDateComplaints = useMemo(() => {
        if (!selectedDate) return [];
        return getComplaintsForDate(selectedDate);
    }, [selectedDate, complaints]);

    // Navigate months
    const goToPreviousMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
        setSelectedDate(null);
    };

    const goToNextMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
        setSelectedDate(null);
    };

    return (
        <div className="calendar-view">
            <motion.div
                className="calendar-header"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <h2 className="calendar-title">
                    {format(currentDate, 'MMMM yyyy')}
                </h2>
                <div className="calendar-nav">
                    <button
                        className="nav-button"
                        onClick={goToPreviousMonth}
                        title="Previous month"
                    >
                        <ChevronLeftIcon className="nav-icon" />
                    </button>
                    <button
                        className="nav-button"
                        onClick={goToNextMonth}
                        title="Next month"
                    >
                        <ChevronRightIcon className="nav-icon" />
                    </button>
                </div>
            </motion.div>

            <div className="calendar-container">
                {/* Calendar Grid */}
                <motion.div
                    className="calendar-grid"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                >
                    {/* Weekday headers */}
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                        <div key={day} className="weekday-header">
                            {day}
                        </div>
                    ))}

                    {/* Month days */}
                    {monthDays.map(day => {
                        const dayComplaints = getComplaintsForDate(day);
                        const hasComplaints = dayComplaints.length > 0;
                        const isSelected = selectedDate && isSameDay(day, selectedDate);
                        const isTodayDate = isToday(day);

                        return (
                            <motion.div
                                key={day.toString()}
                                className={`calendar-day ${isSelected ? 'selected' : ''} ${isTodayDate ? 'today' : ''}`}
                                onClick={() => setSelectedDate(day)}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <div className="day-number">{format(day, 'd')}</div>
                                {hasComplaints && (
                                    <div className="complaint-indicator">
                                        <span className="indicator-dot"></span>
                                        <span className="indicator-count">{dayComplaints.length}</span>
                                    </div>
                                )}
                            </motion.div>
                        );
                    })}
                </motion.div>

                {/* Selected Date Details */}
                {selectedDate && (
                    <motion.div
                        className="date-details"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                    >
                        <h3 className="details-title">
                            {format(selectedDate, 'MMMM d, yyyy')}
                        </h3>

                        {selectedDateComplaints.length === 0 ? (
                            <p className="no-complaints">No complaints for this date</p>
                        ) : (
                            <div className="complaints-list">
                                {selectedDateComplaints.map(complaint => (
                                    <div key={complaint.id} className="complaint-item">
                                        <div className="complaint-header-mini">
                                            <span className="complaint-id-mini">#{complaint.id}</span>
                                            <span className={`priority-dot priority-${complaint.priority}`}></span>
                                        </div>
                                        <div className="complaint-flat">Flat: {complaint.flat_number || 'N/A'}</div>
                                        <div className="complaint-category-mini">{complaint.category}</div>
                                        <div className="complaint-desc-mini">{complaint.description.substring(0, 80)}...</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </motion.div>
                )}
            </div>
        </div>
    );
}
