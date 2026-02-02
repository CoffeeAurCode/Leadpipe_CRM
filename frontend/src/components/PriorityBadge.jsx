import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib';

function PriorityBadge({ priority }) {
    const config = {
        high: {
            bg: 'bg-red-500/10',
            text: 'text-red-500',
            border: 'border-red-500/30',
            label: 'High'
        },
        medium: {
            bg: 'bg-yellow-500/10',
            text: 'text-yellow-500',
            border: 'border-yellow-500/30',
            label: 'Medium'
        },
        low: {
            bg: 'bg-gray-500/10',
            text: 'text-gray-500',
            border: 'border-gray-500/30',
            label: 'Low'
        }
    };

    const style = config[priority] || config.low;

    return (
        <span className={cn(
            "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border",
            style.bg,
            style.text,
            style.border
        )}>
            <AlertCircle className="w-3 h-3" />
            {style.label}
        </span>
    );
}

export default PriorityBadge;
