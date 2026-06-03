import { motion, AnimatePresence } from 'framer-motion';
import { XMarkIcon, CalendarIcon, MapPinIcon, TagIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';
import { formatDate } from '../services/apiService';
import { format, parseISO } from 'date-fns';
import './ComplaintDetailModal.css';

export default function ComplaintDetailModal({ complaint, isOpen, onClose }) {
    if (!complaint) return null;

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
                        className="complaint-detail-modal"
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ type: "spring", duration: 0.3 }}
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="modal-header">
                            <div className="modal-title-section">
                                <h2 className="modal-title">Complaint #{complaint.id}</h2>
                                <span className={`priority-badge priority-${complaint.priority}`}>
                                    {complaint.priority}
                                </span>
                            </div>
                            <button className="close-button" onClick={onClose}>
                                <XMarkIcon className="close-icon" />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="modal-body">
                            {/* Complaint Details */}
                            <div className="detail-section">
                                <h3 className="section-title">Complaint Details</h3>

                                <div className="detail-grid">
                                    <div className="detail-item">
                                        <MapPinIcon className="detail-icon" />
                                        <div>
                                            <div className="detail-label">Flat Number</div>
                                            <div className="detail-value">{complaint.flat_number || 'N/A'}</div>
                                        </div>
                                    </div>

                                    <div className="detail-item">
                                        <TagIcon className="detail-icon" />
                                        <div>
                                            <div className="detail-label">Category</div>
                                            <div className="detail-value">{complaint.category}</div>
                                        </div>
                                    </div>

                                    <div className="detail-item">
                                        <ExclamationCircleIcon className="detail-icon" />
                                        <div>
                                            <div className="detail-label">Status</div>
                                            <div className={`status-badge status-${complaint.status}`}>
                                                {complaint.status}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="detail-item">
                                        <CalendarIcon className="detail-icon" />
                                        <div>
                                            <div className="detail-label">Filed On</div>
                                            <div className="detail-value">{formatDate(complaint.created_at)}</div>
                                        </div>
                                    </div>
                                </div>

                                <div className="description-section">
                                    <div className="detail-label">Description</div>
                                    <p className="description-text">{complaint.description}</p>
                                </div>
                            </div>

                            {/* Appointment Section (if exists) */}
                            {complaint.appointment_date && (
                                <motion.div
                                    className="appointment-section"
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.1 }}
                                >
                                    <h3 className="section-title appointment-title">
                                        <CalendarIcon className="section-icon" />
                                        {complaint.appointment_type === 'callback' ? 'Manager Callback' : 'Scheduled Visit'}
                                    </h3>

                                    <div className="appointment-card">
                                        <div className="appointment-date">
                                            <div className="date-label">Date & Time</div>
                                            <div className="date-value">
                                                {format(parseISO(complaint.appointment_date), 'EEEE, MMMM d, yyyy')}
                                            </div>
                                            <div className="time-value">
                                                {format(parseISO(complaint.appointment_date), 'h:mm a')}
                                            </div>
                                        </div>

                                        {complaint.appointment_status && (
                                            <div className="appointment-status">
                                                <span className={`status-badge status-${complaint.appointment_status}`}>
                                                    {complaint.appointment_status}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            )}

                            {/* No Appointment Notice */}
                            {!complaint.appointment_date && (
                                <div className="no-appointment">
                                    <CalendarIcon className="no-appointment-icon" />
                                    <p>No appointment scheduled yet</p>
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="modal-footer">
                            <button className="close-modal-button" onClick={onClose}>
                                Close
                            </button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
