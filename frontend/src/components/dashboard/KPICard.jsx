import { useState, useEffect } from 'react';
import { useSpring, useMotionValueEvent, motion } from 'framer-motion';

function AnimatedNumber({ value }) {
    const spring = useSpring(0, { stiffness: 60, damping: 20 });
    const [current, setCurrent] = useState(0);

    useEffect(() => { spring.set(value); }, [spring, value]);
    useMotionValueEvent(spring, 'change', (v) => setCurrent(Math.round(v)));

    return <span>{current}</span>;
}

export default function KPICard({ label, value, icon: Icon, iconColor = 'text-primary', delay = 0, onClick }) {
    const interactive = typeof onClick === 'function';

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay }}
            onClick={onClick}
            whileHover={interactive ? { scale: 1.02 } : undefined}
            className={[
                'bg-card border border-border rounded-xl p-5 transition-all duration-300 group',
                interactive
                    ? 'cursor-pointer hover:border-primary hover:shadow-md'
                    : 'hover:border-primary',
            ].join(' ')}
        >
            <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-muted-foreground">{label}</span>
                <Icon className={`w-5 h-5 ${iconColor}`} />
            </div>
            <p className="text-4xl font-bold text-foreground group-hover:text-primary transition-colors">
                <AnimatedNumber value={value} />
            </p>
        </motion.div>
    );
}
