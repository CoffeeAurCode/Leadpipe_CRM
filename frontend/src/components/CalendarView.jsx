import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { startOfMonth, endOfMonth, eachDayOfInterval, format, isSameDay, isToday, parseISO } from 'date-fns';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { api } from '../services/api';
import './CalendarView.css';

export default function CalendarView({ complaints }) {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedDate, setSelectedDate] = useState(null);
    const [appointments, setAppointments] = useState([]);

    // Fetch appointments for current month
    useEffect(() => {
        const fetchAppointments = async () => {
            try {
                const start = startOfMonth(currentDate);
                const end = endOfMonth(currentDate);
                const startDate = format(start, 'yyyy-MM-dd');
                const endDate = format(end, 'yyyy-MM-dd');

                const response = await fetch(
                    `http://localhost:8000/appointments?start_date=${startDate}&end_date=${endDate}`
                );
                const data = await response.json();
                setAppointments(data);
            } catch (error) {
                console.error('Error fetching appointments:', error);
                setAppointments([]);
            }
        };

        fetchAppointments();
    }, [currentDate]);

    // Get month days
    const monthDays = useMemo(() => {
        const start = startOfMonth(currentDate);
        const end = endOfMonth(currentDate);
        return eachDayOfInterval({ start, end });
    }, [currentDate]);

    // Get complaints AND appointments for a specific date
    const getItemsForDate = (date) => {
        // Get complaints with appointments
        const complaintsForDate = complaints.filter(complaint => {
            const relevantDate = complaint.appointment_date
                ? parseISO(complaint.appointment_date)
                : parseISO(complaint.created_at);
            return isSameDay(relevantDate, date);
        });

        // Get standalone appointments (not linked to complaints shown above)
        const appointmentsForDate = appointments.filter(apt => {
            if (!apt.appointment_date) return false;
            const aptDate = parseISO(apt.appointment_date);
            return isSameDay(aptDate, date);
        });

        // Merge: complaints first, then standalone appointments
        return [...complaintsForDate, ...appointmentsForDate];
    };

    // Get selected date items (complaints + appointments)
    const selectedDateItems = useMemo(() => {
        if (!selectedDate) return [];
        return getItemsForDate(selectedDate);
    }, [selectedDate, complaints, appointments]);

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
                    {format(currentDate, 'MMMM yyyy')} - Scheduled Visits
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
                        const dayItems = getItemsForDate(day);
                        const hasItems = dayItems.length > 0;
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
                                {hasItems && (
                                    <div className="appointment-indicator">
                                        <span className="indicator-dot"></span>
                                        <span className="indicator-count">{dayItems.length}</span>
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

                        {selectedDateItems.length === 0 ? (
                            <p className="no-appointments">No scheduled visits for this date</p>
                        ) : (
                            <div className="appointments-list">
                                {selectedDateItems.map(item => (
                                    <div key={item.id} className="appointment-item">
                                        <div className="appointment-header-mini">
                                            <span className="complaint-id-mini">#{item.id}</span>
                                            {item.priority && <span className={`priority-dot priority-${item.priority}`}></span>}
                                        </div>
                                        <div className="appointment-flat">Flat: {item.flat_number || 'N/A'}</div>
                                        <div className="appointment-category">{item.category || item.complaint_category || 'Visit'}</div>
                                        <div className="appointment-notes">
                                            {(item.description || item.complaint_description || item.notes || 'Scheduled visit').substring(0, 100)}{(item.description || item.complaint_description || item.notes || '').length > 100 ? '...' : ''}
                                        </div>
                                        <div className="appointment-status">
                                            <span className={`status-badge status-${item.status}`}>
                                                {item.status}
                                            </span>
                                        </div>
                                        {item.appointment_date && (
                                            <div className="appointment-time">
                                                Visit time: {format(parseISO(item.appointment_date), 'h:mm a')}
                                            </div>
                                        )}
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
