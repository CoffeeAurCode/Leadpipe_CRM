import { TrendingUp, Clock, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

function CompactStatsGrid({ complaints }) {
    const stats = {
        total: complaints.length,
        pending: complaints.filter(c => c.status === 'pending').length,
        inProgress: complaints.filter(c => c.status === 'in_progress' || c.status === 'in-progress').length,
        resolved: complaints.filter(c => c.status === 'resolved').length,
    };

    const statCards = [
        { label: 'Total', value: stats.total, icon: TrendingUp, color: 'text-blue-500' },
        { label: 'Pending', value: stats.pending, icon: Clock, color: 'text-yellow-500' },
        { label: 'In Progress', value: stats.inProgress, icon: TrendingUp, color: 'text-blue-500' },
        { label: 'Resolved', value: stats.resolved, icon: CheckCircle, color: 'text-green-500' },
    ];

    return (
        <div className="grid grid-cols-2 gap-4 lg:gap-6">
            {statCards.map((stat, index) => {
                const Icon = stat.icon;
                return (
                    <motion.div
                        key={stat.label}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="bg-card border border-border rounded-lg p-6 lg:p-8 hover:border-primary transition-all duration-300 group"
                    >
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-sm lg:text-base text-muted-foreground">{stat.label}</span>
                            <Icon className={`w-5 h-5 lg:w-6 lg:h-6 ${stat.color}`} />
                        </div>
                        <p className="text-3xl lg:text-5xl font-bold text-foreground group-hover:text-primary transition-colors">
                            {stat.value}
                        </p>
                    </motion.div>
                );
            })}
        </div>
    );
}

export default CompactStatsGrid;
