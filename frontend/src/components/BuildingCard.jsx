import { Home, ShoppingBag, Building2, Info, Pencil, CheckCircle2, XCircle, Square, CheckSquare } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib';

/**
 * Maps property_type.icon_type string to a styled icon component.
 */
function PropertyTypeIcon({ iconType, className }) {
    const base = cn('flex-shrink-0', className);
    if (iconType === 'house') return <Home className={base} />;
    if (iconType === 'shop') return <ShoppingBag className={base} />;
    return <Building2 className={base} />;
}

/**
 * BuildingCard
 * Used in both Building View (flat list) and any hierarchy drill-down.
 *
 * Props:
 *  - building: BuildingResponse
 *  - onClick: (building) => void    — drills into units
 *  - onInfo: (building) => void     — opens info modal
 *  - showPropertyType: bool         — show the property type badge (true in Building View)
 */
function BuildingCard({ building, onClick, onInfo, onEdit, showPropertyType = false, selectMode = false, isSelected = false, onToggle }) {
    const { name, image_url, property_type_name, property_type_icon,
        unit_count = 0, occupied_count = 0 } = building;

    const vacantCount = unit_count - occupied_count;
    const occupancyPct = unit_count > 0 ? Math.round((occupied_count / unit_count) * 100) : 0;

    const coverImage = image_url ||
        'https://images.unsplash.com/photo-1486325212027-8081e485255e?q=80&w=2574&auto=format&fit=crop';

    const handleCardClick = () => {
        if (selectMode) onToggle?.(String(building.id));
        else onClick?.(building);
    };

    return (
        <motion.div
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2 }}
            className={cn(
                'bg-card border rounded-xl overflow-hidden group',
                'hover:shadow-lg hover:shadow-primary/10 transition-colors duration-200',
                isSelected
                    ? 'border-primary ring-2 ring-primary/30 hover:border-primary'
                    : 'border-border hover:border-primary'
            )}
        >
            {/* Cover Image — clickable to drill into units */}
            <div
                className="relative h-40 overflow-hidden cursor-pointer"
                onClick={handleCardClick}
            >
                <img
                    src={coverImage}
                    alt={name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    onError={e => {
                        e.target.src =
                            'https://images.unsplash.com/photo-1486325212027-8081e485255e?q=80&w=2574&auto=format&fit=crop';
                    }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

                {/* Checkbox overlay in select mode */}
                {selectMode && (
                    <div className="absolute top-3 left-3">
                        {isSelected
                            ? <CheckSquare className="w-5 h-5 text-primary drop-shadow" />
                            : <Square className="w-5 h-5 text-white drop-shadow" />
                        }
                    </div>
                )}

                {/* Unit count pill */}
                <span className="absolute bottom-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/50 backdrop-blur-sm text-white text-xs font-medium">
                    {unit_count} {unit_count === 1 ? 'Unit' : 'Units'}
                </span>

                {/* Info + Edit buttons — stop propagation so they don't trigger drill-down */}
                {!selectMode && (
                    <div className="absolute top-3 right-3 flex items-center gap-1.5">
                        <button
                            onClick={e => { e.stopPropagation(); onEdit?.(building); }}
                            aria-label="Edit building"
                            className="p-1.5 rounded-full bg-black/50 backdrop-blur-sm text-white hover:bg-black/70 transition-colors"
                        >
                            <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                            onClick={e => { e.stopPropagation(); onInfo?.(building); }}
                            aria-label="Building info"
                            className="p-1.5 rounded-full bg-black/50 backdrop-blur-sm text-white hover:bg-black/70 transition-colors"
                        >
                            <Info className="w-3.5 h-3.5" />
                        </button>
                    </div>
                )}
            </div>

            {/* Card Body */}
            <div
                className="p-4 space-y-3 cursor-pointer"
                onClick={handleCardClick}
            >
                <div className="flex items-start justify-between gap-2">
                    <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-1">
                        {name}
                    </h3>

                    {/* Property type badge — shown in Building View */}
                    {showPropertyType && property_type_name && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium flex-shrink-0">
                            <PropertyTypeIcon iconType={property_type_icon} className="w-3 h-3" />
                            {property_type_name}
                        </span>
                    )}
                </div>

                {/* Occupancy stats */}
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5 text-red-400" />
                        <span className="font-medium text-foreground">{occupied_count}</span> Occupied
                    </span>
                    <div className="w-px h-4 bg-border" />
                    <span className="flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
                        <span className="font-medium text-foreground">{vacantCount}</span> Vacant
                    </span>
                </div>

                {/* Occupancy bar */}
                <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                    <div
                        className="h-full bg-primary rounded-full transition-all duration-500"
                        style={{ width: `${occupancyPct}%` }}
                    />
                </div>
            </div>
        </motion.div>
    );
}

export default BuildingCard;
