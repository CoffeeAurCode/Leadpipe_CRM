import { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Calendar, Plus, Clock, Edit2, Save, X as CloseIcon, Trash2 } from 'lucide-react';
import { format, parseISO, isFuture, isToday, setHours, setMinutes, setSeconds } from 'date-fns';
import PriorityBadge from './PriorityBadge';
import { cn } from '@/lib';
import { api } from '../services/api';

function DateComplaintsModal({ date, complaints, onClose, onComplaintClick }) {
    const canSchedule = isFuture(date) || isToday(date);
    const [showForm, setShowForm] = useState(false);
    const [editingAppointment, setEditingAppointment] = useState(null);
    const [formData, setFormData] = useState({
        flat_number: '',
        time: '10:00',
        notes: ''
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [flatError, setFlatError] = useState('');

    // Separate complaints and appointments (complaints is now array of both)
    const actualComplaints = complaints.filter(item => item.type === 'complaint');
    const standaloneAppointments = complaints.filter(item => item.type === 'appointment');
    const allItems = [...actualComplaints, ...standaloneAppointments];

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        if (name === 'flat_number') setFlatError('');
        setError('');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            // Verify flat exists
            const flatCheck = await api.verifyFlat(formData.flat_number);
            if (!flatCheck.exists) {
                setFlatError(`Flat ${formData.flat_number} does not exist`);
                setLoading(false);
                return;
            }

            // Build ISO datetime string directly to avoid timezone issues
            const dateStr = format(date, 'yyyy-MM-dd');
            const timeStr = formData.time; // Already in HH:mm format
            const isoDateTime = `${dateStr}T${timeStr}:00`; // e.g., "2026-02-10T14:30:00"

            // Create appointment
            await api.createAppointment({
                flat_number: formData.flat_number,
                appointment_date: isoDateTime,
                notes: formData.notes || null,
                status: 'scheduled'
            });

            // Reset and close
            setFormData({ flat_number: '', time: '10:00', notes: '' });
            setShowForm(false);

            // Refresh the page to show new appointment
            window.location.reload();
        } catch (err) {
            setError(err.message || 'Failed to create appointment');
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (appointment) => {
        // Parse the appointment date and extract components in UTC to preserve exact time
        const appointmentDate = parseISO(appointment.appointment_date);
        const appointmentTime = format(appointmentDate, 'HH:mm');

        setEditingAppointment({
            id: appointment.id,
            time: appointmentTime,
            notes: appointment.notes || '',
            // Store the original date for reference
            originalDate: appointment.appointment_date
        });
    };

    const handleSaveEdit = async (appointmentId) => {
        setLoading(true);
        setError('');

        try {
            // Build ISO datetime string directly to avoid timezone issues
            const dateStr = format(date, 'yyyy-MM-dd');
            const timeStr = editingAppointment.time; // Already in HH:mm format
            const isoDateTime = `${dateStr}T${timeStr}:00`; // e.g., "2026-02-10T14:30:00"

            // Update appointment
            await api.updateAppointment(appointmentId, {
                appointment_date: isoDateTime,
                notes: editingAppointment.notes || null
            });

            // Reset and refresh
            setEditingAppointment(null);
            window.location.reload();
        } catch (err) {
            setError(err.message || 'Failed to update appointment');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (appointmentId) => {
        // Confirmation dialog for delete
        const confirmed = window.confirm(
            'Delete this appointment?\n\n' +
            'This will permanently remove the appointment from the schedule.'
        );

        if (!confirmed) {
            return;
        }

        setLoading(true);
        setError('');

        try {
            await api.cancelAppointment(appointmentId);
            window.location.reload();
        } catch (err) {
            setError(err.message || 'Failed to delete appointment');
        } finally {
            setLoading(false);
        }
    };

    const handleCancelEdit = () => {
        setEditingAppointment(null);
        setError('');
    };

    return (
        <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
            onClick={onClose}
        >
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-card border border-border rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
            >
                {/* Header */}
                <div className="flex items-start justify-between p-6 border-b border-border">
                    <div className="flex items-center gap-3">
                        <Calendar className="w-6 h-6 text-primary" />
                        <div>
                            <h2 className="text-2xl font-bold text-foreground">
                                {format(date, 'MMMM d, yyyy')}
                            </h2>
                            <p className="text-sm text-muted-foreground">
                                {allItems.length} scheduled visit{allItems.length !== 1 ? 's' : ''}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-secondary transition-colors"
                    >
                        <X className="w-5 h-5 text-muted-foreground" />
                    </button>
                </div>

                {/* Scheduled Visits List */}
                <div className="p-6 space-y-3">
                    {allItems.length === 0 ? (
                        <div className="text-center py-8">
                            <Calendar className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
                            <p className="text-muted-foreground">
                                {canSchedule ? 'No visits scheduled for this date' : 'No visits on this date'}
                            </p>
                        </div>
                    ) : (
                        allItems.map((item, index) => {
                            const isComplaint = item.type === 'complaint';
                            const isEditing = editingAppointment?.id === item.id;
                            const canEdit = !isComplaint && canSchedule;

                            // Edit mode for this appointment  
                            if (isEditing) {
                                return (
                                    <div
                                        key={`${item.type}-${item.id}-${index}`}
                                        className="bg-primary/5 rounded-lg border border-primary/20 p-4"
                                    >
                                        <div className="flex items-center justify-between mb-3">
                                            <h4 className="text-sm font-semibold text-foreground">Edit Appointment</h4>
                                            <button
                                                onClick={handleCancelEdit}
                                                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                                            >
                                                Cancel
                                            </button>
                                        </div>

                                        <div className="space-y-3">
                                            <div>
                                                <label className="block text-xs font-medium text-foreground mb-1.5">
                                                    Flat Number
                                                </label>
                                                <input
                                                    type="text"
                                                    value={item.flat_number}
                                                    disabled
                                                    className="w-full px-3 py-2 rounded-lg border border-border bg-secondary/50 text-muted-foreground text-sm cursor-not-allowed"
                                                />
                                            </div>

                                            <div>
                                                <label className="block text-xs font-medium text-foreground mb-1.5">
                                                    Time *
                                                </label>
                                                <input
                                                    type="time"
                                                    value={editingAppointment.time}
                                                    onChange={(e) => setEditingAppointment(prev => ({ ...prev, time: e.target.value }))}
                                                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                                                />
                                            </div>

                                            <div>
                                                <label className="block text-xs font-medium text-foreground mb-1.5">
                                                    Notes
                                                </label>
                                                <textarea
                                                    value={editingAppointment.notes}
                                                    onChange={(e) => setEditingAppointment(prev => ({ ...prev, notes: e.target.value }))}
                                                    placeholder="Add any notes..."
                                                    rows="2"
                                                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                                                />
                                            </div>

                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => handleSaveEdit(item.id)}
                                                    disabled={loading}
                                                    className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm font-medium"
                                                >
                                                    <Save className="w-4 h-4" />
                                                    {loading ? 'Saving...' : 'Save Changes'}
                                                </button>

                                                <button
                                                    onClick={() => handleDelete(item.id)}
                                                    disabled={loading}
                                                    className="px-4 py-2 bg-red-500/10 text-red-500 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm font-medium"
                                                    title="Delete appointment"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                );
                            }

                            // Normal display mode
                            return (
                                <button
                                    key={`${item.type}-${item.id}-${index}`}
                                    onClick={() => {
                                        if (isComplaint) {
                                            onClose();
                                            onComplaintClick(item);
                                        }
                                    }}
                                    className={cn(
                                        "w-full text-left p-4 rounded-lg border border-border bg-secondary relative",
                                        isComplaint && "hover:border-primary hover:bg-card transition-all duration-200 group cursor-pointer",
                                        !isComplaint && "cursor-default"
                                    )}
                                >
                                    {/* Edit button for appointments */}
                                    {canEdit && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleEdit(item);
                                            }}
                                            className="absolute top-3 right-3 p-1.5 rounded-md hover:bg-primary/10 text-muted-foreground hover:text-primary transition-colors"
                                            title="Edit appointment"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                    )}

                                    <div className="flex items-start justify-between gap-2 mb-2">
                                        <div className="flex-1 pr-8">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="text-xs font-medium text-muted-foreground">
                                                    Flat {item.flat_number || 'N/A'}
                                                </span>
                                                {isComplaint && (
                                                    <>
                                                        <span className="text-xs text-muted-foreground">•</span>
                                                        <span className="text-xs font-medium text-primary capitalize">
                                                            {item.category}
                                                        </span>
                                                    </>
                                                )}
                                                {!isComplaint && (
                                                    <>
                                                        <span className="text-xs text-muted-foreground">•</span>
                                                        <span className="text-xs font-medium text-blue-500">
                                                            Appointment
                                                        </span>
                                                    </>
                                                )}
                                            </div>
                                            <h4 className={cn(
                                                "text-sm font-semibold text-foreground",
                                                isComplaint && "group-hover:text-primary transition-colors"
                                            )}>
                                                {isComplaint
                                                    ? `${item.description?.substring(0, 60)}${item.description?.length > 60 ? '...' : ''}`
                                                    : item.notes || 'Scheduled visit'
                                                }
                                            </h4>
                                        </div>
                                        {isComplaint && <PriorityBadge priority={item.priority} />}
                                    </div>
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-2">
                                        <Clock className="w-3.5 h-3.5" />
                                        <span>{format(parseISO(item.appointment_date), 'h:mm a')}</span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-2">
                                        <span className={cn(
                                            "text-xs px-2 py-0.5 rounded-full capitalize",
                                            item.status === 'pending' && "bg-yellow-500/10 text-yellow-500",
                                            item.status === 'in-progress' && "bg-blue-500/10 text-blue-500",
                                            item.status === 'resolved' && "bg-green-500/10 text-green-500",
                                            item.status === 'cancelled' && "bg-red-500/10 text-red-500",
                                            item.status === 'scheduled' && "bg-blue-500/10 text-blue-500",
                                            item.status === 'completed' && "bg-green-500/10 text-green-500",
                                            item.status === 'rescheduled' && "bg-orange-500/10 text-orange-500"
                                        )}>
                                            {item.status}
                                        </span>
                                    </div>
                                </button>
                            );
                        })
                    )}
                </div>

                {/* Schedule New Appointment */}
                {canSchedule && (
                    <div className="p-6 pt-0">
                        {!showForm ? (
                            <button
                                onClick={() => setShowForm(true)}
                                className="w-full p-4 rounded-lg border-2 border-dashed border-border bg-secondary/50 hover:bg-secondary hover:border-primary transition-all group"
                            >
                                <Plus className="w-8 h-8 text-muted-foreground group-hover:text-primary mx-auto mb-2 transition-colors" />
                                <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                                    Schedule New Appointment
                                </p>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Click to create a visit for this date
                                </p>
                            </button>
                        ) : (
                            <motion.form
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                onSubmit={handleSubmit}
                                className="bg-secondary/50 rounded-lg border border-border p-4 space-y-4"
                            >
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-sm font-semibold text-foreground">New Appointment</h3>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowForm(false);
                                            setError('');
                                            setFlatError('');
                                        }}
                                        className="text-xs text-muted-foreground hover:text-foreground"
                                    >
                                        Cancel
                                    </button>
                                </div>

                                {error && (
                                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                                        <p className="text-xs text-red-500">{error}</p>
                                    </div>
                                )}

                                <div>
                                    <label className="block text-xs font-medium text-foreground mb-1.5">
                                        Flat Number *
                                    </label>
                                    <input
                                        type="text"
                                        name="flat_number"
                                        value={formData.flat_number}
                                        onChange={handleChange}
                                        placeholder="e.g., 101, A201, B305"
                                        required
                                        className={cn(
                                            "w-full px-3 py-2 rounded-lg border bg-background text-foreground text-sm",
                                            "focus:outline-none focus:ring-2 focus:ring-primary/50",
                                            flatError ? "border-red-500" : "border-border"
                                        )}
                                    />
                                    {flatError && <p className="text-xs text-red-500 mt-1">{flatError}</p>}
                                </div>

                                <div>
                                    <label className="block text-xs font-medium text-foreground mb-1.5">
                                        Time *
                                    </label>
                                    <input
                                        type="time"
                                        name="time"
                                        value={formData.time}
                                        onChange={handleChange}
                                        required
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-medium text-foreground mb-1.5">
                                        Notes (Optional)
                                    </label>
                                    <textarea
                                        name="notes"
                                        value={formData.notes}
                                        onChange={handleChange}
                                        placeholder="Add any notes about this appointment..."
                                        rows="2"
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                                    />
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full px-4 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? 'Creating...' : 'Create Appointment'}
                                </button>
                            </motion.form>
                        )}
                    </div>
                )}
            </motion.div>
        </div>
    );
}

export default DateComplaintsModal;
