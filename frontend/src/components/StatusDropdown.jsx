import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib';

function StatusDropdown({ currentStatus, onStatusChange, onClick }) {
    const statusConfig = {
        pending: { label: 'Pending', bg: 'bg-gray-500/10', text: 'text-gray-400', border: 'border-gray-500/30' },
        in_progress: { label: 'In Progress', bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
        'in-progress': { label: 'In Progress', bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
        resolved: { label: 'Resolved', bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30' },
        closed: { label: 'Closed', bg: 'bg-gray-500/10', text: 'text-gray-500', border: 'border-gray-500/30' },
    };

    const current = statusConfig[currentStatus] || statusConfig.pending;

    return (
        <div className="relative group" onClick={onClick}>
            <button className={cn(
                "inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border transition-all",
                current.bg,
                current.text,
                current.border
            )}>
                {current.label}
                <ChevronDown className="w-3 h-3" />
            </button>

            <div className="absolute right-0 top-full mt-1 bg-card border border-border rounded-lg shadow-lg hidden group-hover:block z-10 min-w-[140px]">
                {Object.entries(statusConfig).filter(([value]) => value !== 'in-progress').map(([value, config]) => (
                    <button
                        key={value}
                        onClick={(e) => {
                            e.stopPropagation();
                            onStatusChange(value);
                        }}
                        className={cn(
                            "w-full text-left px-4 py-2 text-sm transition-colors first:rounded-t-lg last:rounded-b-lg",
                            currentStatus === value || (currentStatus === 'in-progress' && value === 'in_progress')
                                ? "bg-primary text-primary-foreground"
                                : "text-foreground hover:bg-secondary"
                        )}
                    >
                        {config.label}
                    </button>
                ))}
            </div>
        </div>
    );
}

export default StatusDropdown;
