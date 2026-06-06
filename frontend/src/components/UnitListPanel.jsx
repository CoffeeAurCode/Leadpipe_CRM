import { ArrowLeft, Home, CheckCircle2, XCircle, Bed, Bath, Hash, Tag } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib';

/**
 * UnitListPanel
 * Drill-down panel shown after clicking a property group.
 * Lists all units (flats) within that group.
 *
 * Props:
 *  - group: { name: string, units: FlatRecord[] }
 *  - onBack: () => void
 *  - onUnitClick: (unit) => void
 */
function UnitListPanel({ group, onBack, onUnitClick }) {
    const { name, units } = group;
    const totalUnits = units.length;
    const occupiedCount = units.filter(u => !!u.tenant_uuid).length;
    const vacantCount = totalUnits - occupiedCount;

    return (
        <motion.div
            key="unit-panel"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            className="space-y-5"
        >
            {/* Breadcrumb + Back Button */}
            <div className="flex items-center gap-2 text-sm">
                <button
                    onClick={onBack}
                    className={cn(
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-lg',
                        'text-muted-foreground hover:text-foreground hover:bg-secondary',
                        'transition-all duration-200 font-medium'
                    )}
                >
                    <ArrowLeft className="w-4 h-4" />
                    Properties
                </button>
                <span className="text-muted-foreground">/</span>
                <span className="text-foreground font-semibold truncate">{name}</span>
            </div>

            {/* Property Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">{name}</h2>
                    <p className="text-sm text-muted-foreground mt-0.5">
                        {totalUnits} {totalUnits === 1 ? 'unit' : 'units'} ·{' '}
                        <span className="text-green-500">{vacantCount} vacant</span> ·{' '}
                        <span className="text-red-400">{occupiedCount} occupied</span>
                    </p>
                </div>
            </div>

            {/* Unit Grid */}
            {units.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 rounded-xl border border-border bg-card">
                    <Home className="w-12 h-12 text-muted-foreground opacity-40 mb-3" />
                    <p className="text-muted-foreground">No units found in this property</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    <AnimatePresence>
                        {units.map((unit, i) => {
                            const isOccupied = !!unit.tenant_uuid;
                            return (
                                <motion.div
                                    key={unit.uuid}
                                    initial={{ opacity: 0, y: 16 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.04, duration: 0.2 }}
                                    onClick={() => onUnitClick(unit)}
                                    className={cn(
                                        'bg-card border rounded-xl p-4 cursor-pointer group',
                                        'hover:border-primary hover:shadow-md hover:shadow-primary/10',
                                        'transition-all duration-200',
                                        isOccupied ? 'border-border' : 'border-border'
                                    )}
                                >
                                    {/* Unit Header */}
                                    <div className="flex items-start justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-secondary text-foreground">
                                                <Hash className="w-4 h-4 text-primary" />
                                            </span>
                                            <div>
                                                <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                                                    Unit {unit.flat_number}
                                                </p>
                                                {unit.floor_number != null && (
                                                    <p className="text-xs text-muted-foreground">
                                                        Floor {unit.floor_number}
                                                    </p>
                                                )}
                                            </div>
                                        </div>

                                        {/* Status Badges */}
                                        <div className="flex flex-col items-end gap-1">
                                            {isOccupied ? (
                                                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/10 text-red-500 text-xs font-medium">
                                                    <XCircle className="w-3 h-3" />
                                                    Occupied
                                                </span>
                                            ) : (
                                                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-medium">
                                                    <CheckCircle2 className="w-3 h-3" />
                                                    Vacant
                                                </span>
                                            )}
                                            {isOccupied ? (
                                                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted text-muted-foreground text-xs font-medium">
                                                    <Tag className="w-3 h-3" />
                                                    Cannot be listed
                                                </span>
                                            ) : unit.is_listed ? (
                                                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-500 text-xs font-medium">
                                                    <Tag className="w-3 h-3" />
                                                    Listed
                                                </span>
                                            ) : (
                                                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 text-xs font-medium">
                                                    <Tag className="w-3 h-3" />
                                                    Not Listed
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Features */}
                                    <div className="flex items-center gap-3 text-xs text-muted-foreground border-t border-border pt-3">
                                        {unit.bedrooms != null && (
                                            <span className="flex items-center gap-1">
                                                <Bed className="w-3.5 h-3.5 text-primary" />
                                                <span className="font-medium text-foreground">{unit.bedrooms}</span> Bed
                                            </span>
                                        )}
                                        {unit.bathrooms != null && (
                                            <span className="flex items-center gap-1">
                                                <Bath className="w-3.5 h-3.5 text-primary" />
                                                <span className="font-medium text-foreground">{unit.bathrooms}</span> Bath
                                            </span>
                                        )}
                                    </div>
                                </motion.div>
                            );
                        })}
                    </AnimatePresence>
                </div>
            )}
        </motion.div>
    );
}

export default UnitListPanel;
