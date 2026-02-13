import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib';
import { STATUS, STATUS_CONFIG } from '../constants/status';

function StatusDropdown({ currentStatus, onStatusChange, onClick }) {
    const current = STATUS_CONFIG[currentStatus] || STATUS_CONFIG[STATUS.PENDING];

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
                {Object.entries(STATUS_CONFIG).map(([value, config]) => (
                    <button
                        key={value}
                        onClick={(e) => {
                            e.stopPropagation();
                            onStatusChange(value);
                        }}
                        className={cn(
                            "w-full text-left px-4 py-2 text-sm transition-colors first:rounded-t-lg last:rounded-b-lg",
                            currentStatus === value
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
