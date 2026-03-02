import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Settings as SettingsIcon, Save, AlertTriangle, X,
    Building2, Home, Hash, ArrowLeft, ChevronRight, Layers
} from 'lucide-react';
import {
    fetchPropertyGroups,
    fetchPropertySettings,
    updatePropertySettings,
    fetchPropertyBuildings,
    fetchBuildingUnits,
} from '../services/apiService';
import { cn } from '@/lib';

/**
 * SettingsPage — Hierarchical settings management.
 *
 * Navigation mirrors PropertiesPage:
 *   Level 0: Property Group cards (root)
 *   Level 1: Building cards (drilled into a property) + show property-scope settings
 *   Level 2: Unit cards (drilled into a building) + show building-scope settings
 *   Level 3: Unit selected → show unit-scope settings
 *
 * Settings are stored in/read from the property_features table.
 */

const SOURCE_BADGE = {
    overridden: { label: 'Overridden', cls: 'bg-orange-500/20 text-orange-400 border border-orange-500/30' },
    inherited: { label: 'Inherited', cls: 'bg-blue-500/10 text-blue-400 border border-blue-500/30' },
    building: { label: 'From Building', cls: 'bg-purple-500/10 text-purple-400 border border-purple-500/30' },
    default: { label: 'Default', cls: 'bg-gray-500/10 text-gray-400 border border-gray-500/30' },
};

const fadeSlide = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -8 },
    transition: { duration: 0.22, ease: 'easeOut' },
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function Breadcrumb({ segments, onBack }) {
    return (
        <div className="flex items-center gap-2 text-sm">
            <button
                onClick={onBack}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-all font-medium"
            >
                <ArrowLeft className="w-4 h-4" />
                {segments[0]}
            </button>
            {segments.slice(1).map((seg, i) => (
                <span key={i} className="flex items-center gap-2">
                    <span className="text-muted-foreground">/</span>
                    <span className="text-foreground font-semibold truncate">{seg}</span>
                </span>
            ))}
        </div>
    );
}

function PropertyGroupCard({ property, onClick }) {
    const cover = property.image_url ||
        'https://images.unsplash.com/photo-1486325212027-8081e485255e?q=80&w=2574&auto=format&fit=crop';
    return (
        <motion.div
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2 }}
            onClick={() => onClick(property)}
            className="bg-card border border-border rounded-xl overflow-hidden cursor-pointer group hover:border-primary hover:shadow-lg hover:shadow-primary/10 transition-colors duration-200"
        >
            <div className="relative h-36 overflow-hidden">
                <img src={cover} alt={property.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    onError={e => { e.target.src = cover; }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                <div className="absolute bottom-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/50 backdrop-blur-sm text-white text-xs font-medium">
                    <Building2 className="w-3.5 h-3.5" />
                    <span>{property.building_count} {property.building_count === 1 ? 'Building' : 'Buildings'}</span>
                </div>
            </div>
            <div className="p-4">
                <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-1">
                    {property.name}
                </h3>
                {property.address && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{property.address}</p>}
            </div>
        </motion.div>
    );
}

function BuildingCard({ building, onClick, isSelected }) {
    return (
        <motion.div
            whileHover={{ y: -1 }}
            transition={{ duration: 0.15 }}
            onClick={() => onClick(building)}
            className={cn(
                'bg-card border rounded-xl p-4 cursor-pointer group transition-all duration-200',
                isSelected
                    ? 'border-primary bg-primary/5 shadow-md shadow-primary/10'
                    : 'border-border hover:border-primary hover:shadow-md hover:shadow-primary/10'
            )}
        >
            <div className="flex items-start gap-3">
                <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-secondary flex-shrink-0">
                    <Building2 className="w-5 h-5 text-primary" />
                </span>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors truncate">
                        {building.name}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {building.unit_count ?? 0} units
                        {building.property_type_name && <> · {building.property_type_name}</>}
                    </p>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground mt-1 group-hover:text-primary transition-colors" />
            </div>
        </motion.div>
    );
}

function UnitCard({ unit, onClick, isSelected }) {
    const isOccupied = !!unit.tenant_uuid;
    return (
        <motion.div
            whileHover={{ y: -1 }}
            transition={{ duration: 0.15 }}
            onClick={() => onClick(unit)}
            className={cn(
                'bg-card border rounded-xl p-4 cursor-pointer group transition-all duration-200',
                isSelected
                    ? 'border-primary bg-primary/5 shadow-md shadow-primary/10'
                    : 'border-border hover:border-primary hover:shadow-md hover:shadow-primary/10'
            )}
        >
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-secondary">
                        <Hash className="w-4 h-4 text-primary" />
                    </span>
                    <div>
                        <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                            Unit {unit.flat_number}
                        </p>
                        {unit.floor_number != null && (
                            <p className="text-xs text-muted-foreground">Floor {unit.floor_number}</p>
                        )}
                    </div>
                </div>
                <span className={cn(
                    'text-xs px-2 py-0.5 rounded-full font-medium',
                    isOccupied
                        ? 'bg-red-500/10 text-red-400'
                        : 'bg-green-500/10 text-green-400'
                )}>
                    {isOccupied ? 'Occupied' : 'Vacant'}
                </span>
            </div>
        </motion.div>
    );
}

function EmptyState({ icon: Icon, title, subtitle }) {
    return (
        <div className="flex flex-col items-center justify-center h-48 rounded-xl border border-border bg-card text-center p-6">
            <Icon className="w-12 h-12 text-muted-foreground opacity-30 mb-3" />
            <p className="text-foreground font-medium">{title}</p>
            {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
        </div>
    );
}

// ── Feature panel ──────────────────────────────────────────────────────────────

function FeaturePanel({ settings, pendingChanges, onToggle }) {
    if (!settings) {
        return (
            <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
        );
    }

    const categories = {};
    Object.entries(settings).forEach(([key, meta]) => {
        const cat = meta.category || 'Other';
        if (!categories[cat]) categories[cat] = [];
        categories[cat].push({ key, ...meta });
    });

    return (
        <div className="space-y-4">
            {Object.entries(categories).map(([category, features]) => (
                <motion.div
                    key={category}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="rounded-xl border border-border bg-card overflow-hidden"
                >
                    <div className="px-6 py-4 border-b border-border bg-secondary/40">
                        <h3 className="text-base font-semibold text-foreground">{category}</h3>
                    </div>
                    <div className="p-6 space-y-3">
                        {features.map(feature => {
                            const currentValue = pendingChanges.hasOwnProperty(feature.key)
                                ? pendingChanges[feature.key]
                                : feature.enabled;
                            const isDirty = pendingChanges.hasOwnProperty(feature.key);
                            const badge = SOURCE_BADGE[feature.source] || SOURCE_BADGE.default;

                            return (
                                <label
                                    key={feature.key}
                                    className={cn(
                                        'flex items-start gap-4 p-4 rounded-lg cursor-pointer transition-colors border',
                                        currentValue
                                            ? 'bg-primary/5 border-primary/20'
                                            : 'bg-background border-border hover:bg-secondary/40',
                                        isDirty && 'ring-1 ring-primary/40'
                                    )}
                                >
                                    <input
                                        type="checkbox"
                                        checked={currentValue}
                                        onChange={() => onToggle(feature.key, currentValue)}
                                        className="mt-1 w-5 h-5 accent-primary rounded"
                                    />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-medium text-foreground">{feature.display_name}</span>
                                            <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', badge.cls)}>
                                                {badge.label}
                                            </span>
                                            {isDirty && (
                                                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                                                    Unsaved
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-sm text-muted-foreground mt-1">{feature.description}</div>
                                    </div>
                                </label>
                            );
                        })}
                    </div>
                </motion.div>
            ))}
        </div>
    );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

function SettingsPage() {
    // ── Hierarchy data ─────────────────────────────────────────────────────────
    const [propertyGroups, setPropertyGroups] = useState([]);
    const [propertyBuildings, setPropertyBuildings] = useState([]);
    const [buildingUnits, setBuildingUnits] = useState([]);

    // ── Navigation state (drill-down) ──────────────────────────────────────────
    // null = not yet selected at that level
    const [selectedProperty, setSelectedProperty] = useState(null);
    const [selectedBuilding, setSelectedBuilding] = useState(null);
    const [selectedUnit, setSelectedUnit] = useState(null);

    // ── Settings state ─────────────────────────────────────────────────────────
    const [settings, setSettings] = useState(null);
    const [pendingChanges, setPendingChanges] = useState({});
    const [hasChanges, setHasChanges] = useState(false);

    // ── UI ─────────────────────────────────────────────────────────────────────
    const [loadingGroups, setLoadingGroups] = useState(true);
    const [loadingDrill, setLoadingDrill] = useState(false);
    const [loadingSettings, setLoadingSettings] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [bulkModal, setBulkModal] = useState(null);

    // ── Load property groups on mount ──────────────────────────────────────────
    useEffect(() => {
        (async () => {
            try {
                setLoadingGroups(true);
                const data = await fetchPropertyGroups();
                setPropertyGroups(data);
            } catch {
                setError('Failed to load properties');
            } finally {
                setLoadingGroups(false);
            }
        })();
    }, []);

    // ── Drill into a property → load its buildings ─────────────────────────────
    const drillIntoProperty = useCallback(async (property) => {
        setSelectedProperty(property);
        setSelectedBuilding(null);
        setSelectedUnit(null);
        setPropertyBuildings([]);
        setBuildingUnits([]);
        setSettings(null);
        setPendingChanges({});
        setHasChanges(false);
        setLoadingDrill(true);
        try {
            const blds = await fetchPropertyBuildings(property.id);
            setPropertyBuildings(blds || []);
        } catch { /* buildings optional */ }
        finally { setLoadingDrill(false); }
    }, []);

    // ── Drill into a building → load its units ─────────────────────────────────
    const drillIntoBuilding = useCallback(async (building) => {
        setSelectedBuilding(building);
        setSelectedUnit(null);
        setBuildingUnits([]);
        setSettings(null);
        setPendingChanges({});
        setHasChanges(false);
        setLoadingDrill(true);
        try {
            const units = await fetchBuildingUnits(building.id);
            setBuildingUnits(units || []);
        } catch { /* ignore */ }
        finally { setLoadingDrill(false); }
    }, []);

    // ── Select a unit (leaf scope) ─────────────────────────────────────────────
    const selectUnit = useCallback((unit) => {
        setSelectedUnit(unit);
        setSettings(null);
        setPendingChanges({});
        setHasChanges(false);
    }, []);

    // ── Load settings whenever the effective scope changes ─────────────────────
    useEffect(() => {
        if (!selectedProperty) return;
        (async () => {
            try {
                setLoadingSettings(true);
                setError(null);
                const scope = {
                    building_id: selectedBuilding?.id ?? null,
                    unit_id: selectedUnit?.id ?? null,
                };
                const data = await fetchPropertySettings(selectedProperty.id, scope);
                setSettings(data.features);
                setPendingChanges({});
                setHasChanges(false);
            } catch {
                setError('Failed to load settings');
            } finally {
                setLoadingSettings(false);
            }
        })();
    }, [selectedProperty, selectedBuilding, selectedUnit]);

    // ── Toggle / Save ──────────────────────────────────────────────────────────
    function handleToggle(featureKey, currentValue) {
        const newValue = !currentValue;
        if (!selectedUnit && (selectedBuilding || selectedProperty)) {
            const affectedUnits = selectedBuilding ? buildingUnits.length : 0;
            setBulkModal({ featureKey, newValue, affectedUnits });
        } else {
            applyToggle(featureKey, newValue);
        }
    }

    function applyToggle(featureKey, newValue) {
        setPendingChanges(prev => ({ ...prev, [featureKey]: newValue }));
        setHasChanges(true);
        setBulkModal(null);
    }

    async function handleSave(replaceOverrides = false) {
        try {
            setSaving(true);
            const scope = {
                building_id: selectedBuilding?.id ?? null,
                unit_id: selectedUnit?.id ?? null,
                replace_overrides: replaceOverrides,
            };
            await updatePropertySettings(selectedProperty.id, pendingChanges, scope);
            // Reload settings after save
            const data = await fetchPropertySettings(selectedProperty.id, scope);
            setSettings(data.features);
            setPendingChanges({});
            setHasChanges(false);
        } catch {
            setError('Failed to save settings');
        } finally {
            setSaving(false);
        }
    }

    function handleCancel() {
        setPendingChanges({});
        setHasChanges(false);
    }

    // ── Back navigation helpers ────────────────────────────────────────────────
    const backFromUnit = () => {
        setSelectedUnit(null);
        setSettings(null);
        setPendingChanges({});
        setHasChanges(false);
    };

    const backFromBuilding = () => {
        setSelectedBuilding(null);
        setSelectedUnit(null);
        setBuildingUnits([]);
        setSettings(null);
        setPendingChanges({});
        setHasChanges(false);
    };

    const backFromProperty = () => {
        setSelectedProperty(null);
        setSelectedBuilding(null);
        setSelectedUnit(null);
        setPropertyBuildings([]);
        setBuildingUnits([]);
        setSettings(null);
        setPendingChanges({});
        setHasChanges(false);
    };

    // ── Scope description ──────────────────────────────────────────────────────
    const scopeHint = selectedUnit
        ? '📦 Unit scope: changes apply only to this unit, overriding building and property settings.'
        : selectedBuilding
            ? '🏢 Building scope: changes apply to all units in this building (unless a unit overrides).'
            : selectedProperty
                ? '🏠 Property scope: these are the defaults for all buildings & units in this property.'
                : null;

    // ── Page header ────────────────────────────────────────────────────────────
    const header = (
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between">
            <div>
                <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
                    <SettingsIcon className="w-8 h-8 text-primary" />
                    Settings
                </h1>
                <p className="text-muted-foreground mt-1">
                    {selectedUnit
                        ? `Managing settings for Unit ${selectedUnit.flat_number}`
                        : selectedBuilding
                            ? `Managing settings for ${selectedBuilding.name}`
                            : selectedProperty
                                ? `Managing settings for ${selectedProperty.name}`
                                : 'Select a property to manage its feature settings'
                    }
                </p>
            </div>
        </motion.div>
    );

    // ── Loading initial property groups ────────────────────────────────────────
    if (loadingGroups) {
        return (
            <div className="space-y-6">
                {header}
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
                </div>
            </div>
        );
    }

    // ── Level 0: No property selected — show property group cards ──────────────
    if (!selectedProperty) {
        return (
            <div className="space-y-6">
                {header}
                {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">{error}</div>
                )}
                {propertyGroups.length === 0 ? (
                    <EmptyState icon={Layers} title="No properties found"
                        subtitle="Add a property from the Properties page first." />
                ) : (
                    <motion.div
                        initial="hidden" animate="visible"
                        variants={{ hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.06 } } }}
                        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
                    >
                        {propertyGroups.map(p => (
                            <motion.div key={p.id} variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0 } }}>
                                <PropertyGroupCard property={p} onClick={drillIntoProperty} />
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </div>
        );
    }

    // ── Shared save bar ────────────────────────────────────────────────────────
    const saveBar = (
        <AnimatePresence>
            {hasChanges && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
                    className="sticky bottom-6 flex items-center justify-between gap-3 p-4 rounded-xl bg-card border border-border shadow-xl"
                >
                    <span className="text-sm text-muted-foreground">
                        {Object.keys(pendingChanges).length} unsaved change(s)
                    </span>
                    <div className="flex gap-3">
                        <button onClick={handleCancel} disabled={saving}
                            className="px-4 py-2 rounded-lg text-muted-foreground hover:bg-secondary transition-colors text-sm">
                            Cancel
                        </button>
                        <button onClick={() => handleSave(false)} disabled={saving}
                            className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
                            {saving
                                ? <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />Saving…</>
                                : <><Save className="w-4 h-4" />Save Changes</>
                            }
                        </button>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );

    // ── Bulk edit modal ────────────────────────────────────────────────────────
    const bulkConfirmModal = (
        <AnimatePresence>
            {bulkModal && (
                <>
                    <motion.div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9000]"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={() => setBulkModal(null)} />
                    <motion.div
                        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[9001] w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl p-6"
                        initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
                    >
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-orange-500/20">
                                    <AlertTriangle className="w-5 h-5 text-orange-400" />
                                </div>
                                <h2 className="text-lg font-semibold text-foreground">Bulk Edit Warning</h2>
                            </div>
                            <button onClick={() => setBulkModal(null)} className="p-1 rounded text-muted-foreground hover:bg-secondary">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <p className="text-sm text-muted-foreground mb-4">
                            You are about to <strong className="text-foreground">{bulkModal.newValue ? 'enable' : 'disable'}</strong>{' '}
                            <strong className="text-foreground">{bulkModal.featureKey.replace(/_/g, ' ')}</strong>{' '}
                            at the {selectedBuilding ? 'building' : 'property'} level.
                            {bulkModal.affectedUnits > 0 && (
                                <> This may affect up to <strong className="text-foreground">{bulkModal.affectedUnits} unit(s)</strong>.</>
                            )}
                        </p>
                        <p className="text-xs text-muted-foreground mb-6">
                            Do you want to also <strong>clear all existing unit-level overrides</strong> for this feature?
                        </p>
                        <div className="flex flex-col gap-2">
                            <button onClick={() => applyToggle(bulkModal.featureKey, bulkModal.newValue)}
                                className="w-full px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors">
                                Apply at this level only (keep unit overrides)
                            </button>
                            <button onClick={() => { applyToggle(bulkModal.featureKey, bulkModal.newValue); handleSave(true); }}
                                className="w-full px-4 py-2.5 rounded-lg border border-orange-500/30 text-orange-400 text-sm font-medium hover:bg-orange-500/10 transition-colors">
                                Apply &amp; replace all unit overrides
                            </button>
                            <button onClick={() => setBulkModal(null)}
                                className="w-full px-4 py-2.5 rounded-lg text-muted-foreground text-sm hover:bg-secondary transition-colors">
                                Cancel
                            </button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );

    // ── Level 3: Unit scope — show unit settings ───────────────────────────────
    if (selectedUnit) {
        return (
            <div className="space-y-5">
                <Breadcrumb
                    segments={[selectedBuilding?.name || selectedProperty.name, `Unit ${selectedUnit.flat_number}`]}
                    onBack={backFromUnit}
                />
                {header}
                {scopeHint && <p className="text-sm text-muted-foreground px-1">{scopeHint}</p>}
                {error && <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">{error}</div>}
                <FeaturePanel settings={loadingSettings ? null : settings} pendingChanges={pendingChanges} onToggle={handleToggle} />
                {saveBar}
                {bulkConfirmModal}
            </div>
        );
    }

    // ── Level 2: Building scope — show unit cards + settings for this building ──
    if (selectedBuilding) {
        return (
            <div className="space-y-5">
                <Breadcrumb
                    segments={[selectedProperty.name, selectedBuilding.name]}
                    onBack={backFromBuilding}
                />
                {header}
                {scopeHint && <p className="text-sm text-muted-foreground px-1">{scopeHint}</p>}
                {error && <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">{error}</div>}

                {/* Unit picker */}
                {loadingDrill ? (
                    <div className="flex items-center justify-center h-28">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                    </div>
                ) : buildingUnits.length > 0 && (
                    <div>
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                            🏠 Drill into a specific Unit (optional)
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                            {buildingUnits.map(u => (
                                <UnitCard key={u.id} unit={u} onClick={selectUnit} isSelected={false} />
                            ))}
                        </div>
                    </div>
                )}

                {/* Building-level feature settings */}
                <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                        🏢 Building-level Settings
                    </p>
                    <FeaturePanel settings={loadingSettings ? null : settings} pendingChanges={pendingChanges} onToggle={handleToggle} />
                </div>

                {saveBar}
                {bulkConfirmModal}
            </div>
        );
    }

    // ── Level 1: Property scope — show building cards + property-level settings ─
    return (
        <div className="space-y-5">
            <Breadcrumb
                segments={['Properties', selectedProperty.name]}
                onBack={backFromProperty}
            />
            {header}
            {scopeHint && <p className="text-sm text-muted-foreground px-1">{scopeHint}</p>}
            {error && <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">{error}</div>}

            {/* Building picker */}
            {loadingDrill ? (
                <div className="flex items-center justify-center h-28">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
            ) : propertyBuildings.length > 0 && (
                <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                        🏢 Drill into a specific Building (optional)
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {propertyBuildings.map(b => (
                            <BuildingCard key={b.id} building={b} onClick={drillIntoBuilding} isSelected={false} />
                        ))}
                    </div>
                </div>
            )}

            {/* Property-level feature settings */}
            <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                    🏠 Property-level Settings
                </p>
                <FeaturePanel settings={loadingSettings ? null : settings} pendingChanges={pendingChanges} onToggle={handleToggle} />
            </div>

            {saveBar}
            {bulkConfirmModal}
        </div>
    );
}

export default SettingsPage;
