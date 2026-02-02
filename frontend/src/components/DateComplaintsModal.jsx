import { motion } from 'framer-motion';
import { X, Calendar } from 'lucide-react';
import { format } from 'date-fns';
import PriorityBadge from './PriorityBadge';
import { cn } from '@/lib';

function DateComplaintsModal({ date, complaints, onClose, onComplaintClick }) {
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
                            <p className="text-sm text-muted-foreground">{complaints.length} complaint{complaints.length !== 1 ? 's' : ''}</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-secondary transition-colors"
                    >
                        <X className="w-5 h-5 text-muted-foreground" />
                    </button>
                </div>

                {/* Complaints List */}
                <div className="p-6 space-y-3">
                    {complaints.map(complaint => (
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
                                <h4 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                                    {complaint.summary || complaint.flat_number || 'No summary'}
                                </h4>
                                <PriorityBadge priority={complaint.priority} />
                            </div>
                            <p className="text-xs text-muted-foreground">
                                {format(new Date(complaint.created_at), 'h:mm a')}
                            </p>
                        </button>
                    ))}
                </div>
            </motion.div>
        </div>
    );
}

export default DateComplaintsModal;
