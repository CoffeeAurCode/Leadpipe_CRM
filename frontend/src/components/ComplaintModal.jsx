import { motion } from 'framer-motion';
import { X, MapPin, Calendar, User } from 'lucide-react';
import { format } from 'date-fns';
import PriorityBadge from './PriorityBadge';
import StatusDropdown from './StatusDropdown';
import { cn } from '@/lib';

function ComplaintModal({ complaint, onClose, onUpdate }) {
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
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                            <h2 className="text-2xl font-bold text-foreground">Complaint Details</h2>
                            <PriorityBadge priority={complaint.priority} />
                        </div>
                        <p className="text-sm text-muted-foreground">ID: #{complaint.id}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-secondary transition-colors"
                    >
                        <X className="w-5 h-5 text-muted-foreground" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Summary */}
                    {(complaint.summary || complaint.description) && (
                        <div>
                            <h3 className="text-sm font-medium text-muted-foreground mb-2">Summary</h3>
                            <p className="text-foreground">{complaint.summary || complaint.description || 'No summary available'}</p>
                        </div>
                    )}

                    {/* Details Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {(complaint.location || complaint.flat_number) && (
                            <div className="flex items-start gap-3 p-4 rounded-lg bg-secondary">
                                <MapPin className="w-5 h-5 text-primary mt-0.5" />
                                <div>
                                    <p className="text-sm font-medium text-muted-foreground">Location</p>
                                    <p className="text-foreground">{complaint.location || complaint.flat_number}</p>
                                </div>
                            </div>
                        )}

                        <div className="flex items-start gap-3 p-4 rounded-lg bg-secondary">
                            <Calendar className="w-5 h-5 text-primary mt-0.5" />
                            <div>
                                <p className="text-sm font-medium text-muted-foreground">Created</p>
                                <p className="text-foreground">
                                    {format(new Date(complaint.created_at), 'MMM d, yyyy h:mm a')}
                                </p>
                            </div>
                        </div>

                        {complaint.tenant_name && (
                            <div className="flex items-start gap-3 p-4 rounded-lg bg-secondary">
                                <User className="w-5 h-5 text-primary mt-0.5" />
                                <div>
                                    <p className="text-sm font-medium text-muted-foreground">Tenant</p>
                                    <p className="text-foreground">{complaint.tenant_name}</p>
                                </div>
                            </div>
                        )}

                        <div className="flex items-start gap-3 p-4 rounded-lg bg-secondary">
                            <div className="w-5 h-5" /> {/* Spacer for alignment */}
                            <div className="flex-1">
                                <p className="text-sm font-medium text-muted-foreground mb-2">Status</p>
                                <StatusDropdown
                                    currentStatus={complaint.status}
                                    onStatusChange={(newStatus) => onUpdate({ ...complaint, status: newStatus })}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Description (if different from summary) */}
                    {complaint.description && complaint.summary && complaint.description !== complaint.summary && (
                        <div>
                            <h3 className="text-sm font-medium text-muted-foreground mb-2">Description</h3>
                            <p className="text-foreground whitespace-pre-wrap">{complaint.description}</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 p-6 border-t border-border">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </motion.div>
        </div>
    );
}

export default ComplaintModal;
