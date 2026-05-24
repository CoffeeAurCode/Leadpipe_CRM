import { Building2, Home, CheckCircle2, XCircle, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib';

function PropertyGroupCard({ group, onClick }) {
    const { t } = useTranslation();
    const totalUnits = group.units.length;
    const occupiedCount = group.units.filter(u => !!u.tenant_uuid).length;
    const vacantCount = totalUnits - occupiedCount;

    const coverImage =
        group.units.find(u => u.image_url && !u.image_url.includes('placeholder'))?.image_url ||
        'https://images.unsplash.com/photo-1486325212027-8081e485255e?q=80&w=2574&auto=format&fit=crop';

    return (
        <motion.div
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2 }}
            onClick={() => onClick?.(group)}
            className={cn(
                'bg-card border border-border rounded-xl overflow-hidden cursor-pointer group',
                'hover:border-primary hover:shadow-lg hover:shadow-primary/10',
                'transition-colors duration-200'
            )}
        >
            {/* Cover Image */}
            <div className="relative h-44 overflow-hidden">
                <img
                    src={coverImage}
                    alt={group.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    onError={(e) => {
                        e.target.src =
                            'https://images.unsplash.com/photo-1486325212027-8081e485255e?q=80&w=2574&auto=format&fit=crop';
                    }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

                {/* Unit count pill */}
                <div className="absolute bottom-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/50 backdrop-blur-sm text-white text-xs font-medium">
                    <Home className="w-3.5 h-3.5" />
                    <span>{totalUnits} {totalUnits === 1 ? t('properties.unitLabel') : t('properties.units')}</span>
                </div>
            </div>

            {/* Card Body */}
            <div className="p-4 space-y-3">
                {/* Property Name */}
                <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <Building2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                        <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-1">
                            {group.name}
                        </h3>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5 group-hover:text-primary group-hover:translate-x-0.5 transition-all duration-200" />
                </div>

                {/* Occupancy Stats */}
                <div className="flex items-center gap-3 pt-2 border-t border-border">
                    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                        <XCircle className="w-3.5 h-3.5 text-red-400" />
                        <span className="font-medium text-foreground">{occupiedCount}</span>
                        <span>{t('properties.unitStatus.occupied')}</span>
                    </div>
                    <div className="w-px h-4 bg-border" />
                    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
                        <span className="font-medium text-foreground">{vacantCount}</span>
                        <span>{t('properties.unitStatus.vacant')}</span>
                    </div>
                </div>

                {/* Occupancy Bar */}
                <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                    <div
                        className="h-full bg-primary rounded-full transition-all duration-500"
                        style={{ width: totalUnits > 0 ? `${(occupiedCount / totalUnits) * 100}%` : '0%' }}
                    />
                </div>
            </div>
        </motion.div>
    );
}

export default PropertyGroupCard;
