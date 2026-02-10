import { Clock } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import PriorityBadge from './PriorityBadge';

function RecentUpdates({ complaints, onComplaintClick }) {
    return (
        <div className="bg-card border border-border rounded-lg p-6 h-full">
            <div className="flex items-center gap-2 mb-4">
                <Clock className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold text-foreground">Recent Activity</h3>
            </div>

            <div className="space-y-3 overflow-y-auto max-h-96 pr-2">
                {complaints.map(complaint => (
                    <button
                        key={complaint.id}
                        onClick={() => onComplaintClick(complaint)}
                        className="w-full text-left p-3 rounded-lg bg-secondary hover:bg-secondary/80 transition-all duration-200 border border-transparent hover:border-primary group"
                    >
                        <div className="flex items-start justify-between gap-2 mb-1">
                            <p className="text-sm font-medium text-foreground line-clamp-1 group-hover:text-primary transition-colors">
                                {complaint.summary || complaint.flat_number || 'No summary'}
                            </p>
                            <PriorityBadge priority={complaint.priority} />
                        </div>
                        <p className="text-xs text-muted-foreground">
                            {format(parseISO(complaint.created_at), 'MMM d, h:mm a')}
                        </p>
                    </button>
                ))}

                {complaints.length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-8">No recent updates</p>
                )}
            </div>
        </div>
    );
}

export default RecentUpdates;
