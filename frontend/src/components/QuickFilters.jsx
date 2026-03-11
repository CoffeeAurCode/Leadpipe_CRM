import { Filter } from 'lucide-react';
import { cn } from '@/lib';
import { STATUS } from '../constants/status';

function QuickFilters({ filters, onFilterChange }) {
    const statusOptions = [
        { value: 'all', label: 'All Status' },
        { value: STATUS.PENDING, label: 'Pending' },
        { value: STATUS.IN_PROGRESS, label: 'In Progress' },
        { value: STATUS.RESOLVED, label: 'Resolved' },
    ];

    const priorityOptions = [
        { value: 'all', label: 'All Priority' },
        { value: 'low', label: 'Low' },
        { value: 'medium', label: 'Medium' },
        { value: 'high', label: 'High' },
    ];

    return (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <Filter className="w-3.5 h-3.5 text-muted-foreground shrink-0" />

            {statusOptions.map(option => (
                <button
                    key={option.value}
                    onClick={() => onFilterChange({ ...filters, status: option.value })}
                    className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-200",
                        filters.status === option.value
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary text-muted-foreground hover:text-foreground"
                    )}
                >
                    {option.label}
                </button>
            ))}

            <div className="w-px h-3.5 bg-border shrink-0" />

            {priorityOptions.map(option => (
                <button
                    key={option.value}
                    onClick={() => onFilterChange({ ...filters, priority: option.value })}
                    className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-200",
                        filters.priority === option.value
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary text-muted-foreground hover:text-foreground"
                    )}
                >
                    {option.label}
                </button>
            ))}
        </div>
    );
}

export default QuickFilters;
