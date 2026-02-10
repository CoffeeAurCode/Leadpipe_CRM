import { motion, AnimatePresence } from 'framer-motion';
import { XMarkIcon, CalendarIcon, MapPinIcon, ClockIcon, TrashIcon, PencilIcon } from '@heroicons/react/24/outline';
import { format, parseISO } from 'date-fns';
import { useState } from 'react';
import './AppointmentDetailModal.css';

export default function AppointmentDetailModal({ appointment, isOpen, onClose, onUpdate, onDelete }) {
    const [isEditing, setIsEditing] = useState(false);
    const [editData, setEditData] = useState({
        appointment_date: '',
        notes: ''
    });

    if (!appointment) return null;

    const handleEditClick = () => {
        // Initialize form with current data
        setEditData({
            appointment_date: appointment.appointment_date,
            notes: appointment.notes || ''
        });
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

    const handleDelete = async () => {
        const confirmed = window.confirm(
            'Delete this appointment?\n\nThis action cannot be undone.'
        );

        if (confirmed) {
            try {
                await onDelete(appointment.id);
                onClose();
            } catch (error) {
                console.error('Failed to delete appointment:', error);
                alert('Failed to delete appointment');
            }
        }
    };

    const hasComplaint = appointment.complaint_category != null;

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

                                            <div className="detail-item">
                                                <div className="status-icon">●</div>
                                                <div>
                                                    <div className="detail-label">Status</div>
                                                    <div className={`status-badge status-${appointment.status}`}>
                                                        {appointment.status}
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
                                            onChange={(e) => setEditData({
                                                ...editData,
                                                notes: e.target.value
                                            })}
                                            placeholder="Add any notes or special instructions..."
                                        />
                                    </div>

                                    <div className="form-actions">
                                        <button
                                            className="btn-secondary"
                                            onClick={() => setIsEditing(false)}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            className="btn-primary"
                                            onClick={handleSaveEdit}
                                        >
                                            Save Changes
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        {!isEditing && (
                            <div className="modal-footer">
                                <button className="btn-delete" onClick={handleDelete}>
                                    <TrashIcon className="btn-icon" />
                                    Delete
                                </button>
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
