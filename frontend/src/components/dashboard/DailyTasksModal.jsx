import { motion, AnimatePresence } from 'framer-motion';
import { X, MapPin, Clock } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { useState } from 'react';
import { cn } from '@/lib';
import AppointmentDetailModal from '../AppointmentDetailModal';

const STATUS_STYLES = {
    scheduled:     'bg-blue-500/10 text-blue-500',
    attended:      'bg-purple-500/10 text-purple-500',
    completed:     'bg-emerald-500/10 text-emerald-500',
    cancelled:     'bg-red-500/10 text-red-500',
    'in-progress': 'bg-amber-500/10 text-amber-500',
};

export default function DailyTasksModal({ appointments, onClose, onAppointmentUpdate, onAppointmentDelete }) {
    const [selectedAppointment, setSelectedAppointment] = useState(null);
    const today = new Date();
    const dateLabel = format(today, 'EEEE, MMMM d');

    const handleUpdate = async (id, updates) => {
        if (onAppointmentUpdate) await onAppointmentUpdate(id, updates);
        // update the selected appointment locally so the detail modal reflects the change
        setSelectedAppointment(prev => prev ? { ...prev, ...updates } : prev);
    };

    const handleDelete = async (id) => {
        if (onAppointmentDelete) await onAppointmentDelete(id);
        setSelectedAppointment(null);
    };

    return (
        <>
            <div
                className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
                onClick={onClose}
            >
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    onClick={(e) => e.stopPropagation()}
                    className="bg-card border border-border rounded-xl w-full max-w-lg max-h-[80vh] flex flex-col shadow-2xl"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
                        <div>
                            <h2 className="text-lg font-semibold text-foreground">Daily Tasks</h2>
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {dateLabel} · {appointments.length} appointment{appointments.length !== 1 ? 's' : ''}
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 rounded-lg hover:bg-secondary transition-colors"
                        >
                            <X className="w-4 h-4 text-muted-foreground" />
                        </button>
                    </div>

                    {/* List */}
                    <div className="overflow-y-auto flex-1 px-4 py-3 space-y-2">
                        {appointments.length === 0 ? (
                            <p className="text-center text-muted-foreground text-sm py-8">
                                No appointments scheduled for today.
                            </p>
                        ) : (
                            appointments.map((appt) => {
                                let timeStr = '—';
                                try { timeStr = format(parseISO(appt.appointment_date), 'h:mm a'); } catch { /* skip */ }

                                return (
                                    <button
                                        key={appt.id}
                                        onClick={() => setSelectedAppointment(appt)}
                                        className="w-full text-left flex items-start gap-3 p-3 rounded-lg bg-secondary/50 border border-border hover:bg-secondary hover:border-primary/30 transition-colors cursor-pointer"
                                    >
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="text-xs text-muted-foreground font-mono">#{appt.id}</span>
                                                {appt.status && (
                                                    <span className={cn(
                                                        'text-xs font-medium px-2 py-0.5 rounded-full',
                                                        STATUS_STYLES[appt.status] ?? 'bg-secondary text-foreground'
                                                    )}>
                                                        {appt.status}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm text-foreground font-medium">
                                                {appt.complaint_category
                                                    ? `Fix ${appt.complaint_category} Issue`
                                                    : 'Scheduled Visit'}
                                            </p>
                                            {appt.notes && (
                                                <p className="text-xs text-muted-foreground mt-0.5 truncate">{appt.notes}</p>
                                            )}
                                            <div className="flex items-center gap-3 mt-1.5">
                                                {appt.flat_number && (
                                                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                                        <MapPin className="w-3 h-3" />
                                                        {appt.flat_number}
                                                    </span>
                                                )}
                                                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                                    <Clock className="w-3 h-3" />
                                                    {timeStr}
                                                </span>
                                            </div>
                                        </div>
                                    </button>
                                );
                            })
                        )}
                    </div>

                    {/* Footer */}
                    <div className="flex justify-end px-6 py-3 border-t border-border shrink-0">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 rounded-lg bg-secondary text-foreground text-sm hover:bg-secondary/80 transition-colors"
                        >
                            Close
                        </button>
                    </div>
                </motion.div>
            </div>

            {/* Appointment detail modal — rendered outside the list modal so it sits on top */}
            <AnimatePresence>
                {selectedAppointment && (
                    <AppointmentDetailModal
                        appointment={selectedAppointment}
                        isOpen={true}
                        onClose={() => setSelectedAppointment(null)}
                        onUpdate={handleUpdate}
                        onDelete={handleDelete}
                    />
                )}
            </AnimatePresence>
        </>
    );
}
