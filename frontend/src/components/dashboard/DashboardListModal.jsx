import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import PriorityBadge from '../PriorityBadge';
import { cn } from '@/lib';

export default function DashboardListModal({ title, complaints, onClose }) {
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
                className="bg-card border border-border rounded-xl w-full max-w-lg max-h-[80vh] flex flex-col shadow-2xl"
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
                    <div>
                        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            {complaints.length} complaint{complaints.length !== 1 ? 's' : ''}
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
                    {complaints.length === 0 ? (
                        <p className="text-center text-muted-foreground text-sm py-8">No complaints to show.</p>
                    ) : (
                        complaints.map((c) => (
                            <div
                                key={c.id}
                                className="flex items-start gap-3 p-3 rounded-lg bg-secondary/50 border border-border"
                            >
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs text-muted-foreground font-mono">#{c.id}</span>
                                        <PriorityBadge priority={c.priority} />
                                    </div>
                                    <p className="text-sm text-foreground font-medium truncate">
                                        {c.summary || c.description || 'No description'}
                                    </p>
                                    <div className="flex items-center gap-3 mt-1">
                                        {(c.flat_number || c.location) && (
                                            <span className="text-xs text-muted-foreground">
                                                {c.flat_number || c.location}
                                            </span>
                                        )}
                                        {c.created_at && (
                                            <span className="text-xs text-muted-foreground">
                                                {format(parseISO(c.created_at), 'MMM d, yyyy')}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <span className={cn(
                                    'shrink-0 text-xs font-medium px-2 py-0.5 rounded-full',
                                    c.status === 'Pending'     && 'bg-amber-500/10 text-amber-500',
                                    c.status === 'In Progress' && 'bg-blue-500/10 text-blue-500',
                                    c.status === 'Resolved'    && 'bg-emerald-500/10 text-emerald-500',
                                )}>
                                    {c.status}
                                </span>
                            </div>
                        ))
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
    );
}
