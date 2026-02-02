import { format } from 'date-fns';
import PriorityBadge from './PriorityBadge';
import StatusDropdown from './StatusDropdown';
import { MapPin } from 'lucide-react';
import { cn } from '@/lib';

function CompactComplaintCard({ complaint, onClick, onUpdate }) {
    return (
        <div
            onClick={onClick}
            className={cn(
                "bg-card border border-border rounded-lg p-4 cursor-pointer",
                "hover:border-primary hover:shadow-lg hover:shadow-primary/10",
                "transition-all duration-300 group"
            )}
        >
            <div className="flex items-start justify-between gap-2 mb-2">
                <h4 className="text-sm font-semibold text-foreground line-clamp-2 group-hover:text-primary transition-colors">
                    {complaint.summary || complaint.flat_number || 'No summary available'}
                </h4>
                <PriorityBadge priority={complaint.priority} />
            </div>

            {(complaint.location || complaint.flat_number) && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                    <MapPin className="w-3 h-3" />
                    <span className="line-clamp-1">{complaint.location || complaint.flat_number}</span>
                </div>
            )}

            <div className="flex items-center justify-between gap-2 mt-3">
                <span className="text-xs text-muted-foreground">
                    {format(new Date(complaint.created_at), 'MMM d, yyyy')}
                </span>
                <StatusDropdown
                    currentStatus={complaint.status}
                    onStatusChange={(newStatus) => {
                        onUpdate({ ...complaint, status: newStatus });
                    }}
                    onClick={(e) => e.stopPropagation()}
                />
            </div>
        </div>
    );
}

export default CompactComplaintCard;
