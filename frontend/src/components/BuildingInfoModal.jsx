import { X, Building2, MapPin, Home, ShoppingBag } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { cn } from '@/lib';

function TypeIcon({ iconType }) {
    if (iconType === 'house') return <Home className="w-5 h-5 text-primary" />;
    if (iconType === 'shop') return <ShoppingBag className="w-5 h-5 text-primary" />;
    return <Building2 className="w-5 h-5 text-primary" />;
}

/**
 * BuildingInfoModal
 * Simple read-only modal showing building metadata.
 *
 * Props:
 *  - building: BuildingResponse | null
 *  - onClose: () => void
 */
function BuildingInfoModal({ building, onClose }) {
    const { t } = useTranslation();
    if (!building) return null;

    return (
        <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[70] flex items-center justify-center p-4"
            onClick={onClose}
        >
            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                onClick={e => e.stopPropagation()}
                className="bg-card border border-border rounded-xl max-w-md w-full shadow-2xl overflow-hidden"
            >
                {/* Image */}
                {building.image_url && (
                    <div className="h-40 overflow-hidden">
                        <img
                            src={building.image_url}
                            alt={building.name}
                            className="w-full h-full object-cover"
                            onError={e => { e.target.style.display = 'none'; }}
                        />
                    </div>
                )}

                {/* Header */}
                <div className="flex items-center justify-between p-5 border-b border-border bg-gradient-to-r from-primary/10 to-transparent">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/10">
                            <TypeIcon iconType={building.property_type_icon} />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-foreground">{building.name}</h2>
                            {building.property_type_name && (
                                <p className="text-xs text-muted-foreground">{building.property_type_name}</p>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-secondary transition-colors"
                        aria-label="Close"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Details */}
                <div className="p-5 space-y-4">
                    {building.description && (
                        <div>
                            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">{t('common.description')}</p>
                            <p className="text-sm text-foreground">{building.description}</p>
                        </div>
                    )}

                    {building.address && (
                        <div className="flex items-start gap-2">
                            <MapPin className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                            <p className="text-sm text-foreground">{building.address}</p>
                        </div>
                    )}

                    {/* Stats */}
                    <div className="grid grid-cols-3 gap-3 pt-2 border-t border-border">
                        <Stat label={t('building.totalUnits')} value={building.unit_count} />
                        <Stat label={t('settings.occupied')} value={building.occupied_count} highlight="red" />
                        <Stat label={t('settings.vacant')} value={building.unit_count - building.occupied_count} highlight="green" />
                    </div>
                </div>
            </motion.div>
        </div>
    );
}

function Stat({ label, value, highlight }) {
    const color = highlight === 'red' ? 'text-red-400' : highlight === 'green' ? 'text-green-400' : 'text-foreground';
    return (
        <div className="text-center p-3 rounded-lg bg-secondary">
            <p className={cn('text-2xl font-bold', color)}>{value}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
        </div>
    );
}


export default BuildingInfoModal;
