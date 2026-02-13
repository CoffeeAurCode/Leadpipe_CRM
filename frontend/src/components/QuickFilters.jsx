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
        <div className="bg-card border border-border rounded-lg p-6 h-full">
            <div className="flex items-center gap-2 mb-4">
                <Filter className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold text-foreground">Quick Filters</h3>
            </div>

            <div className="space-y-4">
                {/* Status Filter */}
                <div>
                    <label className="text-sm font-medium text-muted-foreground mb-2 block">Status</label>
                    <div className="grid grid-cols-2 gap-2">
                        {statusOptions.map(option => (
                            <button
                                key={option.value}
                                onClick={() => onFilterChange({ ...filters, status: option.value })}
                                className={cn(
                                    "px-3 py-2 rounded-md text-sm font-medium transition-all duration-200",
                                    filters.status === option.value
                                        ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                                        : "bg-secondary text-muted-foreground hover:bg-secondary/80 hover:text-foreground"
                                )}
                            >
                                {option.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Priority Filter */}
                <div>
                    <label className="text-sm font-medium text-muted-foreground mb-2 block">Priority</label>
                    <div className="grid grid-cols-2 gap-2">
                        {priorityOptions.map(option => (
                            <button
                                key={option.value}
                                onClick={() => onFilterChange({ ...filters, priority: option.value })}
                                className={cn(
                                    "px-3 py-2 rounded-md text-sm font-medium transition-all duration-200",
                                    filters.priority === option.value
                                        ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                                        : "bg-secondary text-muted-foreground hover:bg-secondary/80 hover:text-foreground"
                                )}
                            >
                                {option.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default QuickFilters;
