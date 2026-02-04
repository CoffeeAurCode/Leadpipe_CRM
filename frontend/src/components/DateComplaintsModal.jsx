import { motion } from 'framer-motion';
import { X, Calendar, Plus, Clock } from 'lucide-react';
import { format, parseISO, isFuture, isToday } from 'date-fns';
import PriorityBadge from './PriorityBadge';
import { cn } from '@/lib';

function DateComplaintsModal({ date, complaints, onClose, onComplaintClick }) {
    const canSchedule = isFuture(date) || isToday(date);

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
                                {complaints.length} scheduled visit{complaints.length !== 1 ? 's' : ''}
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
                    {complaints.length === 0 ? (
                        <div className="text-center py-8">
                            <Calendar className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
                            <p className="text-muted-foreground">
                                {canSchedule ? 'No visits scheduled for this date' : 'No visits on this date'}
                            </p>
                        </div>
                    ) : (
                        complaints.map(complaint => (
                            <button
                                key={complaint.id}
                                onClick={() => {
                                    onClose();
                                    onComplaintClick(complaint);
                                }}
                                className={cn(
                                    "w-full text-left p-4 rounded-lg border border-border bg-secondary",
                                    "hover:border-primary hover:bg-card transition-all duration-200 group"
                                )}
                            >
                                <div className="flex items-start justify-between gap-2 mb-2">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-xs font-medium text-muted-foreground">
                                                Flat {complaint.flat_number || 'N/A'}
                                            </span>
                                            <span className="text-xs text-muted-foreground">•</span>
                                            <span className="text-xs font-medium text-primary capitalize">
                                                {complaint.category}
                                            </span>
                                        </div>
                                        <h4 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                                            {complaint.description?.substring(0, 60)}{complaint.description?.length > 60 ? '...' : ''}
                                        </h4>
                                    </div>
                                    <PriorityBadge priority={complaint.priority} />
                                </div>
                                {complaint.appointment_date && (
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-2">
                                        <Clock className="w-3.5 h-3.5" />
                                        <span>{format(parseISO(complaint.appointment_date), 'h:mm a')}</span>
                                    </div>
                                )}
                                <div className="flex items-center gap-2 mt-2">
                                    <span className={cn(
                                        "text-xs px-2 py-0.5 rounded-full capitalize",
                                        complaint.status === 'pending' && "bg-yellow-500/10 text-yellow-500",
                                        complaint.status === 'in-progress' && "bg-blue-500/10 text-blue-500",
                                        complaint.status === 'resolved' && "bg-green-500/10 text-green-500",
                                        complaint.status === 'cancelled' && "bg-red-500/10 text-red-500"
                                    )}>
                                        {complaint.status}
                                    </span>
                                </div>
                            </button>
                        ))
                    )}
                </div>

                {/* Future: Add appointment button (placeholder for now) */}
                {canSchedule && (
                    <div className="p-6 pt-0">
                        <div className="p-4 rounded-lg border-2 border-dashed border-border bg-secondary/50 text-center">
                            <Plus className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-50" />
                            <p className="text-sm text-muted-foreground">
                                Schedule appointment feature coming soon
                            </p>
                            <p className="text-xs text-muted-foreground/70 mt-1">
                                You'll be able to create new appointments for this date
                            </p>
                        </div>
                    </div>
                )}
            </motion.div>
        </div>
    );
}

export default DateComplaintsModal;
