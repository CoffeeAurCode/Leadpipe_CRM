import { motion, AnimatePresence } from 'framer-motion';
import { XMarkIcon, CalendarIcon, MapPinIcon, ClockIcon, PencilIcon, ChevronDownIcon } from '@heroicons/react/24/outline';
import { format, parseISO } from 'date-fns';
import { useState, useRef, useEffect } from 'react';
import { APPOINTMENT_STATUS, APPOINTMENT_STATUS_CONFIG, getAppointmentStatusConfig } from '../constants/status';
import './AppointmentDetailModal.css';

export default function AppointmentDetailModal({ appointment, isOpen, onClose, onUpdate }) {
    const [isEditing, setIsEditing] = useState(false);
    const [editData, setEditData] = useState({ appointment_date: '', notes: '' });
    const [currentStatus, setCurrentStatus] = useState(appointment?.status || APPOINTMENT_STATUS.SCHEDULED);
    const [statusLoading, setStatusLoading] = useState(false);
    const [statusDropdownOpen, setStatusDropdownOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Sync status from prop when appointment changes
    useEffect(() => {
        if (appointment?.status) {
            setCurrentStatus(appointment.status);
        }
    }, [appointment]);

    // Close dropdown on outside click
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setStatusDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    if (!appointment) return null;

    const handleStatusChange = async (newStatus) => {
        setStatusDropdownOpen(false);
        if (newStatus === currentStatus) return;
        setStatusLoading(true);
        const prevStatus = currentStatus;
        setCurrentStatus(newStatus); // optimistic update
        try {
            await onUpdate(appointment.id, { status: newStatus });
        } catch (error) {
            console.error('Failed to update appointment status:', error);
            setCurrentStatus(prevStatus); // revert on error
            alert('Failed to update status. Please try again.');
        } finally {
            setStatusLoading(false);
        }
    };

    const handleEditClick = () => {
        setEditData({ appointment_date: appointment.appointment_date, notes: appointment.notes || '' });
        setIsEditing(true);
    };

    const handleSaveEdit = async () => {
        try {
            await onUpdate(appointment.id, editData);
            setIsEditing(false);
            onClose();
        } catch (error) {
            console.error('Failed to update appointment:', error);
            alert('Failed to update appointment');
        }
    };


    const hasComplaint = appointment.complaint_category != null;
    const statusConfig = getAppointmentStatusConfig(currentStatus);

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        className="modal-backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                    />

                    {/* Modal */}
                    <motion.div
                        className="appointment-detail-modal"
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ type: "spring", duration: 0.3 }}
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="modal-header">
                            <div className="modal-title-section">
                                <CalendarIcon className="header-icon" />
                                <div>
                                    <h2 className="modal-title">
                                        {hasComplaint
                                            ? `Fix ${appointment.complaint_category} Issue`
                                            : 'Scheduled Visit'
                                        }
                                    </h2>
                                    <p className="modal-subtitle">Appointment #{appointment.id}</p>
                                </div>
                            </div>
                            <button className="close-button" onClick={onClose}>
                                <XMarkIcon className="close-icon" />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="modal-body">
                            {!isEditing ? (
                                <>
                                    {/* Appointment Details */}
                                    <div className="detail-section">
                                        <h3 className="section-title">Appointment Details</h3>

                                        <div className="detail-grid">
                                            <div className="detail-item">
                                                <MapPinIcon className="detail-icon" />
                                                <div>
                                                    <div className="detail-label">Flat Number</div>
                                                    <div className="detail-value">{appointment.flat_number}</div>
                                                </div>
                                            </div>

                                            <div className="detail-item">
                                                <CalendarIcon className="detail-icon" />
                                                <div>
                                                    <div className="detail-label">Date</div>
                                                    <div className="detail-value">
                                                        {format(parseISO(appointment.appointment_date), 'EEEE, MMMM d, yyyy')}
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="detail-item">
                                                <ClockIcon className="detail-icon" />
                                                <div>
                                                    <div className="detail-label">Time</div>
                                                    <div className="detail-value">
                                                        {format(parseISO(appointment.appointment_date), 'h:mm a')}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Status with inline dropdown */}
                                            <div className="detail-item">
                                                <div className="status-icon">●</div>
                                                <div style={{ flex: 1 }}>
                                                    <div className="detail-label">Status</div>
                                                    <div className="appt-status-wrapper" ref={dropdownRef}>
                                                        <button
                                                            className={`appt-status-btn ${statusConfig.text} ${statusConfig.bg} ${statusConfig.border}`}
                                                            onClick={() => setStatusDropdownOpen(o => !o)}
                                                            disabled={statusLoading}
                                                            title="Click to change status"
                                                        >
                                                            {statusLoading ? 'Updating…' : statusConfig.label}
                                                            <ChevronDownIcon className="appt-chevron" />
                                                        </button>

                                                        {statusDropdownOpen && (
                                                            <div className="appt-status-dropdown">
                                                                {Object.entries(APPOINTMENT_STATUS_CONFIG).map(([value, cfg]) => (
                                                                    <button
                                                                        key={value}
                                                                        className={`appt-status-option ${currentStatus === value ? 'active' : ''}`}
                                                                        onClick={() => handleStatusChange(value)}
                                                                    >
                                                                        <span className={`appt-status-dot ${cfg.text}`}>●</span>
                                                                        {cfg.label}
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        {appointment.notes && (
                                            <div className="notes-section">
                                                <div className="detail-label">Notes</div>
                                                <p className="notes-text">{appointment.notes}</p>
                                            </div>
                                        )}
                                    </div>

                                    {/* Linked Complaint Section */}
                                    {hasComplaint && (
                                        <motion.div
                                            className="complaint-section"
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: 0.1 }}
                                        >
                                            <h3 className="section-title complaint-title">
                                                Related Complaint
                                            </h3>

                                            <div className="complaint-card">
                                                <div className="complaint-header">
                                                    <span className="complaint-category">
                                                        {appointment.complaint_category}
                                                    </span>
                                                    {appointment.complaint_priority && (
                                                        <span className={`priority-badge priority-${appointment.complaint_priority}`}>
                                                            {appointment.complaint_priority}
                                                        </span>
                                                    )}
                                                </div>
                                                <p className="complaint-description">
                                                    {appointment.complaint_description}
                                                </p>
                                            </div>
                                        </motion.div>
                                    )}
                                </>
                            ) : (
                                /* Edit Form */
                                <div className="edit-form">
                                    <h3 className="section-title">Edit Appointment</h3>

                                    <div className="form-group">
                                        <label className="form-label">Date & Time</label>
                                        <input
                                            type="datetime-local"
                                            className="form-input"
                                            value={editData.appointment_date?.slice(0, 16) || ''}
                                            onChange={(e) => setEditData({
                                                ...editData,
                                                appointment_date: e.target.value + ':00'
                                            })}
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label className="form-label">Notes</label>
                                        <textarea
                                            className="form-textarea"
                                            rows="3"
                                            value={editData.notes}
                                            onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                                            placeholder="Add any notes or special instructions..."
                                        />
                                    </div>

                                    <div className="form-actions">
                                        <button className="btn-secondary" onClick={() => setIsEditing(false)}>
                                            Cancel
                                        </button>
                                        <button className="btn-primary" onClick={handleSaveEdit}>
                                            Save Changes
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        {!isEditing && (
                            <div className="modal-footer">
                                <div className="footer-right">
                                    <button className="btn-edit" onClick={handleEditClick}>
                                        <PencilIcon className="btn-icon" />
                                        Edit
                                    </button>
                                    <button className="btn-close" onClick={onClose}>
                                        Close
                                    </button>
                                </div>
                            </div>
                        )}
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
