import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { XMarkIcon, CalendarIcon } from '@heroicons/react/24/outline';
import { api } from '../services/api';
import './AppointmentModal.css';

export default function AppointmentModal({ isOpen, onClose, selectedDate, onSuccess }) {
    const [formData, setFormData] = useState({
        flat_number: '',
        appointment_date: selectedDate ? selectedDate.toISOString().slice(0, 16) : '',
        notes: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [flatError, setFlatError] = useState('');

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));

        // Clear errors when user types
        if (name === 'flat_number') setFlatError('');
        setError('');
    };

    const validateFlat = async (flatNumber) => {
        if (!flatNumber) {
            setFlatError('Flat number is required');
            return false;
        }

        try {
            const result = await api.verifyFlat(flatNumber);
            if (!result.exists) {
                setFlatError(`Flat ${flatNumber} does not exist`);
                return false;
            }
            return true;
        } catch (err) {
            setFlatError('Error verifying flat');
            return false;
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            // Validate flat exists
            const isValidFlat = await validateFlat(formData.flat_number);
            if (!isValidFlat) {
                setLoading(false);
                return;
            }

            // Create appointment
            await api.createAppointment({
                flat_number: formData.flat_number,
                appointment_date: formData.appointment_date,
                notes: formData.notes || null,
                status: 'scheduled',
            });

            // Reset form and close
            setFormData({ flat_number: '', appointment_date: '', notes: '' });
            onSuccess?.();
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to create appointment');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                className="appointment-modal-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={onClose}
            >
                <motion.div
                    className="appointment-modal-content"
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="appointment-modal-header">
                        <div className="modal-title-section">
                            <CalendarIcon className="modal-title-icon" />
                            <h2>Schedule Appointment</h2>
                        </div>
                        <button onClick={onClose} className="modal-close-btn">
                            <XMarkIcon className="close-icon" />
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="appointment-form">
                        {error && (
                            <div className="error-alert">
                                {error}
                            </div>
                        )}

                        <div className="form-group">
                            <label htmlFor="flat_number">Flat Number *</label>
                            <input
                                type="text"
                                id="flat_number"
                                name="flat_number"
                                value={formData.flat_number}
                                onChange={handleChange}
                                placeholder="e.g., 101, A201, B305"
                                required
                                className={flatError ? 'input-error' : ''}
                            />
                            {flatError && <span className="field-error">{flatError}</span>}
                        </div>

                        <div className="form-group">
                            <label htmlFor="appointment_date">Appointment Date & Time *</label>
                            <input
                                type="datetime-local"
                                id="appointment_date"
                                name="appointment_date"
                                value={formData.appointment_date}
                                onChange={handleChange}
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="notes">Notes (Optional)</label>
                            <textarea
                                id="notes"
                                name="notes"
                                value={formData.notes}
                                onChange={handleChange}
                                placeholder="Add any additional notes or instructions..."
                                rows="3"
                            />
                        </div>

                        <div className="modal-actions">
                            <button
                                type="button"
                                onClick={onClose}
                                className="btn-cancel"
                                disabled={loading}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn-submit"
                                disabled={loading}
                            >
                                {loading ? 'Creating...' : 'Create Appointment'}
                            </button>
                        </div>
                    </form>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
