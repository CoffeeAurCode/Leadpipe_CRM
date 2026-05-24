import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Settings as SettingsIcon, Save, AlertTriangle, X,
    Building2, Home, Hash, ArrowLeft, ChevronRight, Layers, Users
} from 'lucide-react';
import {
    fetchPropertyGroups,
    fetchPropertySettings,
    fetchBuildingSettings,
    fetchUnitSettings,
    updatePropertySettings,
    updateBuildingSettings,
    updateUnitSettings,
    fetchPropertyBuildings,
    fetchBuildingUnits,
    fetchFlats,
} from '../services/apiService';
import { cn } from '@/lib';

/**
 * SettingsPage — Unit-centric hierarchical settings management.
 *
 * Navigation (drill-down, mirrors PropertiesPage):
 *   Level 0: Property Group cards + 'Unassigned Units' pseudo-property
 *   Level 1: Building cards + property-aggregate feature toggles + Standalone units
 *   Level 2: Unit cards + building-aggregate feature toggles
 *   Level 3: Unit selected → unit-specific feature toggles
 *
 * Save behaviour:
 *   - At Level 1 (property scope): saves to ALL units in the property via bulk endpoint
 *   - At Level 2 (building scope): saves to ALL units in the building via bulk endpoint
 *   - At Level 3 (unit scope): saves directly to that unit
 *
 * The backend handles all cascading — the DB stores one row per unit per feature.
 */

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

function PropertyGroupCard({ property, onClick, isUnassigned = false }) {
    const { t } = useTranslation();
    const cover = property.image_url ||
        'https://images.unsplash.com/photo-1486325212027-8081e485255e?q=80&w=2574&auto=format&fit=crop';

    if (isUnassigned) {
        return (
            <motion.div
                whileHover={{ y: -2 }}
                transition={{ duration: 0.2 }}
                onClick={() => onClick(property)}
                className="bg-card border border-dashed border-border rounded-xl overflow-hidden cursor-pointer group hover:border-primary hover:shadow-lg hover:shadow-primary/10 transition-colors duration-200 flex flex-col items-center justify-center p-8"
            >
                <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <Hash className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
                <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
                    {t('settings.unassigned')}
                </h3>
                <p className="text-sm text-muted-foreground mt-1 text-center">
                    {t('settings.unassignedHint', { count: property.unit_count })}
                </p>
            </motion.div>
        );
    }

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
                    <span>{t('settings.buildingCount', { count: property.building_count })}</span>
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

function BuildingCard({ building, onClick }) {
    const { t } = useTranslation();
    return (
        <motion.div
            whileHover={{ y: -1 }}
            transition={{ duration: 0.15 }}
            onClick={() => onClick(building)}
            className="bg-card border border-border rounded-xl p-4 cursor-pointer group hover:border-primary hover:shadow-md hover:shadow-primary/10 transition-all duration-200"
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
                        {t('settings.unitCount', { count: building.unit_count ?? 0 })}
                    </p>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground mt-1 group-hover:text-primary transition-colors" />
            </div>
        </motion.div>
    );
}

function UnitCard({ unit, onClick }) {
    const { t } = useTranslation();
    const isOccupied = !!unit.tenant_uuid || !!unit.tenant_id;
    return (
        <motion.div
            whileHover={{ y: -1 }}
            transition={{ duration: 0.15 }}
            onClick={() => onClick(unit)}
            className="bg-card border border-border rounded-xl p-4 cursor-pointer group hover:border-primary hover:shadow-md hover:shadow-primary/10 transition-all duration-200"
        >
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-secondary">
                        <Hash className="w-4 h-4 text-primary" />
                    </span>
                    <div>
                        <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                            {t('settings.unitLabel')} {unit.flat_number}
                        </p>
                        {unit.floor_number != null && (
                            <p className="text-xs text-muted-foreground">{t('settings.floor')} {unit.floor_number}</p>
                        )}
                    </div>
                </div>
                <span className={cn(
                    'text-xs px-2 py-0.5 rounded-full font-medium',
                    isOccupied ? 'bg-red-500/10 text-red-400' : 'bg-green-500/10 text-green-400'
                )}>
                    {isOccupied ? t('settings.occupied') : t('settings.vacant')}
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

// ── Feature toggles panel ──────────────────────────────────────────────────────

function FeaturePanel({ settings, pendingChanges, onToggle, scopeKey, isBulk }) {
    const { t } = useTranslation();
    const scopeLabel = t(`settings.scope.${scopeKey}`);

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
            {isBulk && (
                <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-orange-500/10 border border-orange-500/20 text-orange-400 text-sm">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>{t('settings.bulkWarning', { scope: scopeLabel })}</span>
                </div>
            )}

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

                            return (
                                <div
                                    key={feature.key}
                                    onClick={() => onToggle(feature.key, currentValue)}
                                    role="checkbox"
                                    aria-checked={currentValue}
                                    tabIndex={0}
                                    onKeyDown={e => (e.key === ' ' || e.key === 'Enter') && onToggle(feature.key, currentValue)}
                                    className={cn(
                                        'flex items-start gap-4 p-4 rounded-lg cursor-pointer transition-colors border select-none',
                                        currentValue
                                            ? 'bg-primary/5 border-primary/20'
                                            : 'bg-background border-border hover:bg-secondary/40',
                                        isDirty && 'ring-1 ring-primary/40'
                                    )}
                                >
                                    {/* Display-only checkbox — toggle is handled by the parent div */}
                                    <input
                                        type="checkbox"
                                        checked={currentValue}
                                        onChange={() => { }}
                                        tabIndex={-1}
                                        className="mt-1 w-5 h-5 accent-primary rounded pointer-events-none"
                                    />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-medium text-foreground">{feature.display_name}</span>
                                            {isDirty && (
                                                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                                                    {t('settings.unsaved')}
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-sm text-muted-foreground mt-1">{feature.description}</div>
                                    </div>
                                </div>
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
    const { t } = useTranslation();
    // ── Hierarchy data ─────────────────────────────────────────────────────────
    const [propertyGroups, setPropertyGroups] = useState([]);
    const [propertyBuildings, setPropertyBuildings] = useState([]);
    const [buildingUnits, setBuildingUnits] = useState([]);
    const [allFlats, setAllFlats] = useState([]);
    const [orphanedUnits, setOrphanedUnits] = useState([]);
    const [standaloneUnits, setStandaloneUnits] = useState([]);

    // ── Navigation (drill-down) ────────────────────────────────────────────────
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
    const [saveResult, setSaveResult] = useState(null); // { units_updated, message }
    const [error, setError] = useState(null);

    // ── Current scope label ────────────────────────────────────────────────────
    const scopeKey = selectedUnit ? 'unit' : selectedBuilding ? 'building' : 'property';
    const scopeLabel = t(`settings.scope.${scopeKey}`);
    const isBulk = !selectedUnit; // bulk if property or building scope

    // ── Load property groups & all flats ───────────────────────────────────────
    useEffect(() => {
        (async () => {
            try {
                setLoadingGroups(true);
                const [groups, flats] = await Promise.all([
                    fetchPropertyGroups(),
                    fetchFlats()
                ]);
                setPropertyGroups(groups || []);
                setAllFlats(flats || []);

                // Find orphaned units (no property assigned) for the pseudo-property group
                const orphans = (flats || []).filter(f => !f.property_id);
                setOrphanedUnits(orphans);
            } catch {
                setError(t('settings.failedLoadProps'));
            } finally {
                setLoadingGroups(false);
            }
        })();
    }, []);

    // ── Drill into property ────────────────────────────────────────────────────
    const drillIntoProperty = useCallback(async (property) => {
        setSelectedProperty(property);
        setSelectedBuilding(null);
        setSelectedUnit(null);
        setPropertyBuildings([]);
        setBuildingUnits([]);
        setStandaloneUnits([]);
        setSettings(null);
        setPendingChanges({});
        setHasChanges(false);
        setSaveResult(null);

        // Handle pseudo-property "Unassigned Units"
        if (property.isUnassigned) {
            setStandaloneUnits(orphanedUnits);
            return;
        }

        setLoadingDrill(true);
        try {
            const blds = await fetchPropertyBuildings(property.id);
            setPropertyBuildings(blds || []);

            // Also find standalone units for this property (property attached, but no building)
            const standalones = allFlats.filter(f => f.property_id === property.id && !f.building_id);
            setStandaloneUnits(standalones);
        } catch { /* ok if no buildings */ }
        finally { setLoadingDrill(false); }
    }, [allFlats, orphanedUnits]);

    // ── Drill into building ────────────────────────────────────────────────────
    const drillIntoBuilding = useCallback(async (building) => {
        setSelectedBuilding(building);
        setSelectedUnit(null);
        setBuildingUnits([]);
        setSettings(null);
        setPendingChanges({});
        setHasChanges(false);
        setSaveResult(null);
        setLoadingDrill(true);
        try {
            const units = await fetchBuildingUnits(building.id);
            setBuildingUnits(units || []);
        } catch { /* ok */ }
        finally { setLoadingDrill(false); }
    }, []);

    // ── Select a unit ──────────────────────────────────────────────────────────
    const selectUnit = useCallback((unit) => {
        setSelectedUnit(unit);
        setSettings(null);
        setPendingChanges({});
        setHasChanges(false);
        setSaveResult(null);
    }, []);

    // ── Load settings when scope changes ──────────────────────────────────────
    useEffect(() => {
        if (!selectedProperty || (selectedProperty.isUnassigned && !selectedUnit)) return;
        (async () => {
            try {
                setLoadingSettings(true);
                setError(null);
                let data;
                if (selectedUnit) {
                    data = await fetchUnitSettings(selectedUnit.id);
                } else if (selectedBuilding) {
                    data = await fetchBuildingSettings(selectedProperty.id, selectedBuilding.id);
                } else {
                    data = await fetchPropertySettings(selectedProperty.id);
                }
                setSettings(data?.features ?? null);
                setPendingChanges({});
                setHasChanges(false);
            } catch {
                setError(t('settings.failedLoadSettings'));
            } finally {
                setLoadingSettings(false);
            }
        })();
    }, [selectedProperty, selectedBuilding, selectedUnit]);

    // ── Toggle ─────────────────────────────────────────────────────────────────
    function handleToggle(featureKey, currentValue) {
        setPendingChanges(prev => ({ ...prev, [featureKey]: !currentValue }));
        setHasChanges(true);
    }

    // ── Save ───────────────────────────────────────────────────────────────────
    async function handleSave() {
        try {
            setSaving(true);
            setError(null);
            let result;
            if (selectedUnit) {
                result = await updateUnitSettings(selectedUnit.id, pendingChanges);
            } else if (selectedBuilding) {
                result = await updateBuildingSettings(selectedProperty.id, selectedBuilding.id, pendingChanges);
            } else {
                result = await updatePropertySettings(selectedProperty.id, pendingChanges);
            }
            setSettings(result.features);
            setPendingChanges({});
            setHasChanges(false);
            setSaveResult(result);
        } catch (e) {
            setError(t('settings.failedSave', { message: e.message }));
        } finally {
            setSaving(false);
        }
    }

    function handleCancel() {
        setPendingChanges({});
        setHasChanges(false);
    }

    // ── Back navigation ────────────────────────────────────────────────────────
    const backFromUnit = () => { setSelectedUnit(null); setSettings(null); setPendingChanges({}); setHasChanges(false); setSaveResult(null); };
    const backFromBuilding = () => { setSelectedBuilding(null); setSelectedUnit(null); setBuildingUnits([]); setSettings(null); setPendingChanges({}); setHasChanges(false); setSaveResult(null); };
    const backFromProperty = () => { setSelectedProperty(null); setSelectedBuilding(null); setSelectedUnit(null); setPropertyBuildings([]); setBuildingUnits([]); setStandaloneUnits([]); setSettings(null); setPendingChanges({}); setHasChanges(false); setSaveResult(null); };

    // ── Shared UI pieces ───────────────────────────────────────────────────────
    const saveBar = (
        <AnimatePresence>
            {hasChanges && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
                    className="sticky bottom-6 flex items-center justify-between gap-3 p-4 rounded-xl bg-card border border-border shadow-xl z-10"
                >
                    <span className="text-sm text-muted-foreground">
                        {t('settings.unsavedMsg', { count: Object.keys(pendingChanges).length, scope: scopeLabel.toLowerCase() })}
                    </span>
                    <div className="flex gap-3">
                        <button onClick={handleCancel} disabled={saving}
                            className="px-4 py-2 rounded-lg text-muted-foreground hover:bg-secondary transition-colors text-sm">
                            {t('common.cancel')}
                        </button>
                        <button onClick={handleSave} disabled={saving}
                            className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
                            {saving
                                ? <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />{t('settings.saving')}</>
                                : <><Save className="w-4 h-4" />{isBulk ? t('settings.applyToAll') : t('settings.saveChanges')}</>
                            }
                        </button>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );

    const saveResultBanner = saveResult && (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm"
            >
                ✓ {saveResult.message}
                {saveResult.units_updated !== undefined && (
                    <span className="ml-1 font-medium">({saveResult.units_updated} units)</span>
                )}
                <button onClick={() => setSaveResult(null)} className="ml-auto">
                    <X className="w-4 h-4" />
                </button>
            </motion.div>
        </AnimatePresence>
    );

    const pageHeader = (
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between">
            <div>
                <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
                    <SettingsIcon className="w-8 h-8 text-primary" />
                    {t('settings.title')}
                </h1>
                <p className="text-muted-foreground mt-1 text-sm">
                    {selectedUnit
                        ? t('settings.subtitleUnit', { flatNumber: selectedUnit.flat_number })
                        : selectedBuilding
                            ? t('settings.subtitleBuilding', { buildingName: selectedBuilding.name })
                            : selectedProperty
                                ? selectedProperty.isUnassigned
                                    ? t('settings.subtitleUnassigned')
                                    : t('settings.subtitleProperty', { propertyName: selectedProperty.name })
                                : t('settings.subtitleDefault')
                    }
                </p>
            </div>
        </motion.div>
    );

    const errorBanner = error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">{error}</div>
    );

    // ── Level 0: property picker ───────────────────────────────────────────────
    if (loadingGroups) {
        return (
            <div className="space-y-6 flex-1 min-h-0 overflow-y-auto w-full p-8 pb-32">
                <div className="max-w-[70rem] mx-auto space-y-6">
                    {pageHeader}
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
                    </div>
                </div>
            </div>
        );
    }

    if (!selectedProperty) {
        return (
            <div className="space-y-6 flex-1 min-h-0 overflow-y-auto w-full p-8 pb-32">
                <div className="max-w-[70rem] mx-auto space-y-6">
                    {pageHeader}
                    {errorBanner}
                    {propertyGroups.length === 0 && orphanedUnits.length === 0 ? (
                        <EmptyState icon={Layers} title={t('settings.noProperties')}
                            subtitle={t('settings.noPropertiesHint')} />
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
                            {orphanedUnits.length > 0 && (
                                <motion.div variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0 } }}>
                                    <PropertyGroupCard
                                        property={{ name: t('settings.unassigned'), unit_count: orphanedUnits.length, isUnassigned: true, id: 'unassigned' }}
                                        onClick={drillIntoProperty}
                                        isUnassigned={true}
                                    />
                                </motion.div>
                            )}
                        </motion.div>
                    )}
                </div>
            </div>
        );
    }

    // ── Level 3: Unit scope ────────────────────────────────────────────────────
    if (selectedUnit) {
        return (
            <div className="space-y-5 flex-1 min-h-0 overflow-y-auto w-full p-8 pb-32">
                <div className="max-w-[70rem] mx-auto space-y-5">
                    <Breadcrumb segments={[selectedBuilding?.name || selectedProperty.name, `${t('settings.unitLabel')} ${selectedUnit.flat_number}`]} onBack={backFromUnit} />
                    {pageHeader}
                    {errorBanner}
                    {saveResultBanner}
                    <FeaturePanel
                        settings={loadingSettings ? null : settings}
                        pendingChanges={pendingChanges}
                        onToggle={handleToggle}
                        scopeKey="unit"
                        isBulk={false}
                    />
                    {saveBar}
                </div>
            </div>
        );
    }

    // ── Level 2: Building scope ────────────────────────────────────────────────
    if (selectedBuilding) {
        return (
            <div className="space-y-5 flex-1 min-h-0 overflow-y-auto w-full p-8 pb-32">
                <div className="max-w-[70rem] mx-auto space-y-5">
                    <Breadcrumb segments={[selectedProperty.name, selectedBuilding.name]} onBack={backFromBuilding} />
                    {pageHeader}
                    {errorBanner}
                    {saveResultBanner}

                    {loadingDrill ? (
                        <div className="flex items-center justify-center h-28">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                        </div>
                    ) : buildingUnits.length > 0 && (
                        <div>
                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                                🏠 {t('settings.drillIntoUnit')}
                            </p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                                {buildingUnits.map(u => (
                                    <UnitCard key={u.id} unit={u} onClick={selectUnit} />
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="mt-8">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                            🏢 {t('settings.buildingBulk')}
                        </p>
                        <FeaturePanel
                            settings={loadingSettings ? null : settings}
                            pendingChanges={pendingChanges}
                            onToggle={handleToggle}
                            scopeKey="building"
                            isBulk={true}
                        />
                    </div>
                    {saveBar}
                </div>
            </div>
        );
    }

    // ── Level 1: Property scope ────────────────────────────────────────────────
    return (
        <div className="space-y-5 flex-1 min-h-0 overflow-y-auto w-full p-8 pb-32">
            <div className="max-w-[70rem] mx-auto space-y-5">
                <Breadcrumb segments={[t('nav.properties'), selectedProperty.name]} onBack={backFromProperty} />
                {pageHeader}
                {errorBanner}
                {saveResultBanner}

                {loadingDrill ? (
                    <div className="flex items-center justify-center h-28">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                    </div>
                ) : (
                    <>
                        {propertyBuildings.length > 0 && (
                            <div>
                                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                                    🏢 {t('settings.buildingsDrill')}
                                </p>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {propertyBuildings.map(b => (
                                        <BuildingCard key={b.id} building={b} onClick={drillIntoBuilding} />
                                    ))}
                                </div>
                            </div>
                        )}

                        {standaloneUnits.length > 0 && (
                            <div className={cn("mt-6", propertyBuildings.length === 0 ? "mt-0" : "")}>
                                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                                    🏠 {t('settings.standaloneUnitsSection')}
                                </p>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                                    {standaloneUnits.map(u => (
                                        <UnitCard key={u.id} unit={u} onClick={selectUnit} />
                                    ))}
                                </div>
                            </div>
                        )}
                    </>
                )}

                {!selectedProperty.isUnassigned && (
                    <div className="mt-8">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                            🏘️ {t('settings.propertyBulk')}
                        </p>
                        <FeaturePanel
                            settings={loadingSettings ? null : settings}
                            pendingChanges={pendingChanges}
                            onToggle={handleToggle}
                            scopeKey="property"
                            isBulk={true}
                        />
                    </div>
                )}
                {saveBar}
            </div>
        </div>
    );
}

export default SettingsPage;
