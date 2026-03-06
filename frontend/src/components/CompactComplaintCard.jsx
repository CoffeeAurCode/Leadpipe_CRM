import PriorityBadge from './PriorityBadge';
import StatusDropdown from './StatusDropdown';
import { MapPin } from 'lucide-react';
import { formatDate } from '../services/apiService';
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
            {/* Top: ID + category heading | Priority badge */}
            <div className="flex items-start justify-between gap-2 mb-2">
                <h4 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                    #{complaint.id} · {complaint.category}
                </h4>
                <PriorityBadge priority={complaint.priority} />
            </div>

            {/* Property / unit reference */}
            {complaint.flat_number && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                    <MapPin className="w-3 h-3" />
                    <span className="line-clamp-1">{complaint.flat_number}</span>
                </div>
            )}

            {/* Middle: description */}
            <p className="text-sm text-foreground/80 line-clamp-2 break-words mb-3">
                {complaint.description || 'No description provided.'}
            </p>

            {/* Bottom: date (left) | status (right) */}
            <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-muted-foreground">
                    {formatDate(complaint.created_at)}
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
