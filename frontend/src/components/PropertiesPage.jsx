import { useState, useEffect, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Building2, Plus, Home, Hash, Bed, Bath,
    CheckCircle2, XCircle, ArrowLeft, Layers, Trash2, Upload,
    Square, CheckSquare, Pencil
} from 'lucide-react';
import { cn } from '@/lib';

import ViewSwitcher from './ViewSwitcher';
import BuildingCard from './BuildingCard';
import BuildingInfoModal from './BuildingInfoModal';
import AddBuildingModal from './AddBuildingModal';
import FlatDetailModal from './FlatDetailModal';
import { AddPropertyModal } from './AddPropertyModal';
import AddPropertyGroupModal from './AddPropertyGroupModal';
import CsvImportModal from './CsvImportModal';
import {
    fetchBuildings,
    fetchProperties,
    fetchBuildingUnits,
    fetchPropertyGroups,
    fetchPropertyBuildings,
    deletePropertyGroup,
    deleteBuilding,
    bulkDeletePropertyGroups,
    bulkDeleteBuildings,
    bulkDeleteFlats,
} from '../services/apiService';

// ── Address helper ────────────────────────────────────────────────────────────

function formatAddress(entity) {
    const parts = [
        entity.street_address,
        entity.address_line,
        entity.city,
        entity.state,
        entity.country,
    ].filter(Boolean);
    if (parts.length > 0) return parts.join(', ');
    return entity.address || '';
}

// ── Sub-components ────────────────────────────────────────────────────────────

/** Inline breadcrumb with back button */
function Breadcrumb({ segments, onBack }) {
    return (
        <div className="flex items-center gap-2 text-sm">
            <button
                onClick={onBack}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-all duration-200 font-medium"
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

/** Card for a property group (top-level estate/property) */
function PropertyGroupCard({ property, onClick, onEdit, selectMode = false, isSelected = false, onToggle }) {
    const { t } = useTranslation();
    const coverImage = property.image_url ||
        'https://images.unsplash.com/photo-1486325212027-8081e485255e?q=80&w=2574&auto=format&fit=crop';

    const typeIcons = { house: '🏠', shop: '🏪', apartment: '🏢' };

    const handleClick = () => {
        if (selectMode) onToggle?.(String(property.id));
        else onClick(property);
    };

    return (
        <motion.div
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2 }}
            onClick={handleClick}
            className={cn(
                'bg-card border rounded-xl overflow-hidden cursor-pointer group',
                'hover:shadow-lg hover:shadow-primary/10 transition-colors duration-200',
                isSelected
                    ? 'border-primary ring-2 ring-primary/30 hover:border-primary'
                    : 'border-border hover:border-primary'
            )}
        >
            {/* Cover */}
            <div className="relative h-40 overflow-hidden">
                <img
                    src={coverImage}
                    alt={property.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    onError={e => { e.target.src = 'https://images.unsplash.com/photo-1486325212027-8081e485255e?q=80&w=2574&auto=format&fit=crop'; }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                {selectMode && (
                    <div className="absolute top-3 left-3">
                        {isSelected
                            ? <CheckSquare className="w-5 h-5 text-primary drop-shadow" />
                            : <Square className="w-5 h-5 text-white drop-shadow" />
                        }
                    </div>
                )}
                {!selectMode && (
                    <button
                        onClick={e => { e.stopPropagation(); onEdit?.(property); }}
                        aria-label="Edit property group"
                        className="absolute top-3 right-3 p-1.5 rounded-full bg-black/50 backdrop-blur-sm text-white hover:bg-black/70 transition-colors"
                    >
                        <Pencil className="w-3.5 h-3.5" />
                    </button>
                )}
                <div className="absolute bottom-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/50 backdrop-blur-sm text-white text-xs font-medium">
                    <Building2 className="w-3.5 h-3.5" />
                    <span>{property.building_count} {t('properties.building', {count: property.building_count})}</span>
                </div>
            </div>

            {/* Body */}
            <div className="p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                    <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-1">
                        {property.name}
                    </h3>
                    {property.property_type_name && (
                        <span className="flex-shrink-0 text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                            {typeIcons[property.property_type_icon] || '🏢'} {property.property_type_name}
                        </span>
                    )}
                </div>
                {formatAddress(property) && (
                    <p className="text-xs text-muted-foreground line-clamp-1">{formatAddress(property)}</p>
                )}
            </div>
        </motion.div>
    );
}

/** Unit card — used in both drill-down view and flat Unit View */
function UnitCard({ unit, onClick, buildingName, propertyTypeName, selectMode = false, isSelected = false, onToggle }) {
    const { t } = useTranslation();
    const isOccupied = !!unit.tenant_uuid;
    const flatNum = unit.flat_number;
    const floor = unit.floor_number;
    const beds = unit.bedrooms;
    const baths = unit.bathrooms;

    const handleClick = () => {
        if (selectMode) onToggle?.(unit.uuid);
        else onClick(unit);
    };

    return (
        <motion.div
            whileHover={{ y: -1 }}
            transition={{ duration: 0.15 }}
            onClick={handleClick}
            className={cn(
                'bg-card border rounded-xl p-4 cursor-pointer group',
                'hover:shadow-md hover:shadow-primary/10 transition-all duration-200',
                isSelected
                    ? 'border-primary ring-2 ring-primary/30 hover:border-primary'
                    : 'border-border hover:border-primary'
            )}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    {selectMode ? (
                        isSelected
                            ? <CheckSquare className="w-5 h-5 text-primary flex-shrink-0" />
                            : <Square className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                    ) : (
                        <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-secondary">
                            <Hash className="w-4 h-4 text-primary" />
                        </span>
                    )}
                    <div>
                        <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                            {t('properties.unitLabel')} {flatNum}
                        </p>
                        {floor != null && (
                            <p className="text-xs text-muted-foreground">{t('properties.floor')} {floor}</p>
                        )}
                    </div>
                </div>
                {isOccupied ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/10 text-red-500 text-xs font-medium">
                        <XCircle className="w-3 h-3" /> {t('properties.unitStatus.occupied')}
                    </span>
                ) : (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-medium">
                        <CheckCircle2 className="w-3 h-3" /> {t('properties.unitStatus.vacant')}
                    </span>
                )}
            </div>

            {/* Features */}
            <div className="flex items-center gap-3 text-xs text-muted-foreground border-t border-border pt-3">
                {beds != null && (
                    <span className="flex items-center gap-1">
                        <Bed className="w-3.5 h-3.5 text-primary" />
                        <span className="font-medium text-foreground">{beds}</span> {t('properties.bed')}
                    </span>
                )}
                {baths != null && (
                    <span className="flex items-center gap-1">
                        <Bath className="w-3.5 h-3.5 text-primary" />
                        <span className="font-medium text-foreground">{baths}</span> {t('properties.bath')}
                    </span>
                )}
            </div>

            {/* Context chips */}
            {(buildingName || propertyTypeName) && (
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                    {buildingName && (
                        <span className="px-2 py-0.5 rounded-full bg-secondary text-muted-foreground text-xs">
                            {buildingName}
                        </span>
                    )}
                    {propertyTypeName && (
                        <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs">
                            {propertyTypeName}
                        </span>
                    )}
                </div>
            )}
        </motion.div>
    );
}

/** Empty state component */
function EmptyState({ icon: Icon, title, subtitle }) {
    return (
        <div className="flex flex-col items-center justify-center h-64 rounded-xl border border-border bg-card text-center p-6">
            <Icon className="w-14 h-14 text-muted-foreground opacity-30 mb-3" />
            <p className="text-foreground font-medium">{title}</p>
            {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
        </div>
    );
}

/** Staggered card grid wrapper */
const CardGrid = ({ children, columns = 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3' }) => (
    <motion.div
        initial="hidden"
        animate="visible"
        variants={{ hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.06 } } }}
        className={cn('grid gap-5', columns)}
    >
        {children}
    </motion.div>
);

const cardVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: { opacity: 1, y: 0 },
};

// ── Main Page ─────────────────────────────────────────────────────────────────

function PropertiesPage() {
    // ── Data ──────────────────────────────────────────────────────────────────
    const [propertyGroups, setPropertyGroups] = useState([]);   // top-level properties
    const [buildings, setBuildings] = useState([]);              // all buildings (for Buildings View)
    const [allUnits, setAllUnits] = useState([]);                // all units (for Units View)
    const [buildingUnits, setBuildingUnits] = useState([]);      // units for a drilled-in building
    const [propertyBuildings, setPropertyBuildings] = useState([]); // buildings under a selected property

    const [loadingMain, setLoadingMain] = useState(true);
    const [loadingDrill, setLoadingDrill] = useState(false);
    const [error, setError] = useState(null);
    const [deletingProperty, setDeletingProperty] = useState(false);
    const [deletingBuilding, setDeletingBuilding] = useState(false);

    // ── Select mode ───────────────────────────────────────────────────────────
    const [selectMode, setSelectMode] = useState(false);
    const [selectedPropertyIds, setSelectedPropertyIds] = useState(new Set());
    const [selectedBuildingIds, setSelectedBuildingIds] = useState(new Set());
    const [selectedFlatUuids, setSelectedFlatUuidsSet] = useState(new Set());
    const [bulkDeleting, setBulkDeleting] = useState(false);
    const [bulkError, setBulkError] = useState(null);

    const togglePropertySelection = useCallback((id) => {
        setSelectedPropertyIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    }, []);

    const toggleBuildingSelection = useCallback((id) => {
        setSelectedBuildingIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    }, []);

    const toggleFlatSelection = useCallback((uuid) => {
        setSelectedFlatUuidsSet(prev => {
            const next = new Set(prev);
            if (next.has(uuid)) next.delete(uuid); else next.add(uuid);
            return next;
        });
    }, []);

    // ── Navigation state ──────────────────────────────────────────────────────
    const [viewMode, setViewMode] = useState('properties'); // 'properties' | 'buildings' | 'units'
    const [selectedProperty, setSelectedProperty] = useState(null);  // property group drill-down
    const [selectedBuilding, setSelectedBuilding] = useState(null);  // building drill-down
    const [selectedFlatUuid, setSelectedFlatUuid] = useState(null);  // opens FlatDetailModal

    // ── Modal state ───────────────────────────────────────────────────────────
    const [infoBuilding, setInfoBuilding] = useState(null);
    const [showAddProperty, setShowAddProperty] = useState(false);  // AddPropertyGroupModal
    const [showAddBuilding, setShowAddBuilding] = useState(false);
    const [showAddUnit, setShowAddUnit] = useState(false);
    const [showCsvImport, setShowCsvImport] = useState(false);
    const [editGroup, setEditGroup] = useState(null);
    const [editBuilding, setEditBuilding] = useState(null);

    const { t } = useTranslation();

    // ── Load property groups on mount ─────────────────────────────────────────
    const loadPropertyGroups = useCallback(async () => {
        try {
            setLoadingMain(true);
            const data = await fetchPropertyGroups();
            setPropertyGroups(data);
            setError(null);
        } catch (err) {
            setError(t('properties.failedLoad'));
        } finally {
            setLoadingMain(false);
        }
    }, []);

    // ── Load all buildings (Buildings View) ───────────────────────────────────
    const loadBuildings = useCallback(async () => {
        try {
            const data = await fetchBuildings();
            setBuildings(data);
        } catch (err) {
            console.error('Error loading buildings:', err);
        }
    }, []);

    // ── Load all units (Units View) ───────────────────────────────────────────
    const loadAllUnits = useCallback(async () => {
        try {
            const data = await fetchProperties();
            setAllUnits(data);
        } catch (err) {
            console.error('Error loading units:', err);
        }
    }, []);

    // Initial load
    useEffect(() => { loadPropertyGroups(); loadBuildings(); }, []);
    useEffect(() => { if (viewMode === 'units') loadAllUnits(); }, [viewMode]);

    // Refresh triggered by onboarding tour after creating a property/building/unit
    useEffect(() => {
        const handler = () => { loadPropertyGroups(); loadBuildings(); };
        window.addEventListener('refresh-properties', handler);
        return () => window.removeEventListener('refresh-properties', handler);
    }, [loadPropertyGroups, loadBuildings]);

    // ── Drill into a property group → show its buildings ──────────────────────
    const drillIntoProperty = useCallback(async (property) => {
        setSelectedProperty(property);
        setPropertyBuildings([]);
        setLoadingDrill(true);
        try {
            const buildings = await fetchPropertyBuildings(property.id);
            setPropertyBuildings(buildings);
        } catch (err) {
            console.error('Error loading property buildings:', err);
        } finally {
            setLoadingDrill(false);
        }
    }, []);

    // ── Drill into a building → show its units ────────────────────────────────
    const drillIntoBuilding = useCallback(async (building) => {
        setSelectedBuilding(building);
        setBuildingUnits([]);
        setLoadingDrill(true);
        try {
            const units = await fetchBuildingUnits(building.id);
            setBuildingUnits(units);
        } catch (err) {
            console.error('Error loading building units:', err);
        } finally {
            setLoadingDrill(false);
        }
    }, []);

    // ── Handle view switch — reset all drill-down state ───────────────────────
    const handleViewSwitch = (newView) => {
        setViewMode(newView);
        setSelectedProperty(null);
        setSelectedBuilding(null);
    };

    // ── Back navigation helpers ───────────────────────────────────────────────
    const backFromBuilding = () => {
        setSelectedBuilding(null);
        setBuildingUnits([]);
    };

    const backFromProperty = () => {
        // If we're in the properties view and drilled into a property,
        // going back means going back to the property list
        setSelectedProperty(null);
        setPropertyBuildings([]);
        setSelectedBuilding(null);
    };

    // ── Building lookup for Unit View context chips ────────────────────────────
    const buildingLookup = useMemo(() => {
        const map = {};
        for (const b of buildings) map[b.id] = b;
        return map;
    }, [buildings]);

    // ── Handlers ──────────────────────────────────────────────────────────────
    const handleUnitClick = (unit) => setSelectedFlatUuid(unit.uuid);

    const handlePropertyGroupAdded = (newProperty) => {
        setPropertyGroups(prev => [newProperty, ...prev].sort((a, b) => a.name.localeCompare(b.name)));
    };

    const handlePropertyGroupUpdated = (updatedGroup) => {
        setPropertyGroups(prev => prev.map(p => String(p.id) === String(updatedGroup.id) ? updatedGroup : p));
        if (selectedProperty && String(selectedProperty.id) === String(updatedGroup.id)) {
            setSelectedProperty(updatedGroup);
        }
        setEditGroup(null);
    };

    const handleBuildingAdded = (newBuilding) => {
        setBuildings(prev => [newBuilding, ...prev].sort((a, b) => a.name.localeCompare(b.name)));
        // If we're inside a property, refresh its buildings list
        if (selectedProperty) drillIntoProperty(selectedProperty);
    };

    const handleBuildingUpdated = (updatedBuilding) => {
        setBuildings(prev => prev.map(b => String(b.id) === String(updatedBuilding.id) ? updatedBuilding : b));
        setPropertyBuildings(prev => prev.map(b => String(b.id) === String(updatedBuilding.id) ? updatedBuilding : b));
        if (selectedBuilding && String(selectedBuilding.id) === String(updatedBuilding.id)) {
            setSelectedBuilding(updatedBuilding);
        }
        setEditBuilding(null);
    };

    const handleUnitAdded = () => {
        loadBuildings();
        loadAllUnits();
        if (selectedBuilding) drillIntoBuilding(selectedBuilding);
    };

    const handleDeleteProperty = async () => {
        if (!window.confirm(
            `Delete "${selectedProperty.name}" and ALL its buildings, flats, and tenants?\n\nThis cannot be undone.`
        )) return;
        setDeletingProperty(true);
        try {
            await deletePropertyGroup(selectedProperty.id);
            setPropertyGroups(prev => prev.filter(p => p.id !== selectedProperty.id));
            setSelectedProperty(null);
            setPropertyBuildings([]);
        } catch (err) {
            if (err?.detail === 'tenant_block') {
                const confirmed = window.confirm(
                    `This property has ${err.tenant_count} active tenant(s). Delete them too?`
                );
                if (confirmed) {
                    try {
                        await deletePropertyGroup(selectedProperty.id, true);
                        setPropertyGroups(prev => prev.filter(p => p.id !== selectedProperty.id));
                        setSelectedProperty(null);
                        setPropertyBuildings([]);
                    } catch (forceErr) {
                        alert(forceErr.message || t('properties.failedDeleteProperty'));
                    }
                }
            } else {
                alert(err.message || t('properties.failedDeleteProperty'));
            }
        } finally {
            setDeletingProperty(false);
        }
    };

    const handleDeleteBuilding = async () => {
        if (!window.confirm(
            `Delete building "${selectedBuilding.name}" and ALL its units and tenants?\n\nThis cannot be undone.`
        )) return;
        setDeletingBuilding(true);
        try {
            await deleteBuilding(selectedBuilding.id);
            setBuildings(prev => prev.filter(b => b.id !== selectedBuilding.id));
            if (selectedProperty) {
                setPropertyBuildings(prev => prev.filter(b => b.id !== selectedBuilding.id));
            }
            setSelectedBuilding(null);
            setBuildingUnits([]);
        } catch (err) {
            alert(err.message || t('properties.failedDeleteBuilding'));
        } finally {
            setDeletingBuilding(false);
        }
    };

    const handleFlatDelete = (deletedUuid) => {
        setBuildingUnits(prev => prev.filter(u => u.uuid !== deletedUuid));
        setAllUnits(prev => prev.filter(u => u.uuid !== deletedUuid));
        setSelectedFlatUuid(null);
    };

    const exitSelectMode = () => {
        setSelectMode(false);
        setSelectedPropertyIds(new Set());
        setSelectedBuildingIds(new Set());
        setSelectedFlatUuidsSet(new Set());
        setBulkError(null);
    };

    const handleBulkDelete = async () => {
        const propertyCount = selectedPropertyIds.size;
        const buildingCount = selectedBuildingIds.size;
        const flatCount = selectedFlatUuids.size;
        const total = propertyCount + buildingCount + flatCount;
        if (total === 0) return;

        const label = [
            propertyCount > 0 && `${propertyCount} propert${propertyCount === 1 ? 'y' : 'ies'}`,
            buildingCount > 0 && `${buildingCount} building${buildingCount === 1 ? '' : 's'}`,
            flatCount > 0 && `${flatCount} unit${flatCount === 1 ? '' : 's'}`,
        ].filter(Boolean).join(', ');

        if (!window.confirm(
            `Delete ${label}? All linked tenants, rents, and listings will also be removed.\n\nThis cannot be undone.`
        )) return;

        setBulkDeleting(true);
        setBulkError(null);
        const allErrors = [];

        try {
            if (propertyCount > 0) {
                const r = await bulkDeletePropertyGroups([...selectedPropertyIds]);
                allErrors.push(...(r.errors || []));
                const deletedIds = new Set([...selectedPropertyIds].filter((id, idx) => !r.errors?.some(e => e.startsWith(id))));
                setPropertyGroups(prev => prev.filter(p => !deletedIds.has(String(p.id))));
            }
            if (buildingCount > 0) {
                const r = await bulkDeleteBuildings([...selectedBuildingIds]);
                allErrors.push(...(r.errors || []));
                const deletedIds = new Set([...selectedBuildingIds].filter(id => !r.errors?.some(e => e.startsWith(id))));
                setBuildings(prev => prev.filter(b => !deletedIds.has(String(b.id))));
                if (selectedProperty) setPropertyBuildings(prev => prev.filter(b => !deletedIds.has(String(b.id))));
            }
            if (flatCount > 0) {
                const r = await bulkDeleteFlats([...selectedFlatUuids]);
                allErrors.push(...(r.errors || []));
                const deletedUuids = new Set([...selectedFlatUuids].filter(u => !r.errors?.some(e => e.startsWith(u))));
                setBuildingUnits(prev => prev.filter(u => !deletedUuids.has(u.uuid)));
                setAllUnits(prev => prev.filter(u => !deletedUuids.has(u.uuid)));
            }
        } catch (err) {
            setBulkError(err.message || 'Bulk delete failed.');
        } finally {
            setBulkDeleting(false);
            if (allErrors.length === 0) {
                exitSelectMode();
            } else {
                setBulkError(`${total - allErrors.length} deleted. ${allErrors.length} failed.`);
                setSelectMode(false);
            }
        }
    };

    const handleFlatUpdate = (updatedFlat) => {
        setAllUnits(prev => prev.map(u => u.uuid === updatedFlat.uuid
            ? { ...u, tenant_uuid: updatedFlat.tenant_uuid, occupied: !!updatedFlat.tenant_uuid }
            : u
        ));
        setBuildingUnits(prev => prev.map(u => u.uuid === updatedFlat.uuid
            ? { ...u, tenant_uuid: updatedFlat.tenant_uuid }
            : u
        ));
    };

    // ── Loading / Error states ────────────────────────────────────────────────
    if (loadingMain) {
        return (
            <div className="space-y-6">
                <PageHeader subtitle={t('common.loading')} />
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-6">
                <PageHeader subtitle="Error" />
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500">
                    <p className="text-red-500">{error}</p>
                </div>
            </div>
        );
    }

    // ── Render — Building drill-down (units view) ─────────────────────────────
    if (selectedBuilding) {
        const totalUnits = buildingUnits.length;
        const occupiedCount = buildingUnits.filter(u => !!u.tenant_uuid).length;
        const vacantCount = totalUnits - occupiedCount;

        const breadcrumbSegments = selectedProperty
            ? [selectedProperty.name, selectedBuilding.name]
            : [t('properties.buildings'), selectedBuilding.name];

        return (
            <div className="space-y-5">
                <Breadcrumb
                    segments={breadcrumbSegments}
                    onBack={backFromBuilding}
                />

                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-foreground">{selectedBuilding.name}</h2>
                        <p className="text-sm text-muted-foreground mt-0.5">
                            {totalUnits} {t('properties.unit', {count: totalUnits})} ·{' '}
                            <span className="text-green-500">{vacantCount} {t('properties.vacant')}</span> ·{' '}
                            <span className="text-red-400">{occupiedCount} {t('properties.occupied')}</span>
                            {selectedBuilding.property_type_name && (
                                <> · <span className="text-primary">{selectedBuilding.property_type_name}</span></>
                            )}
                        </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                            onClick={() => setShowAddUnit(true)}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                        >
                            <Plus className="w-4 h-4" /> {t('properties.addUnit')}
                        </button>
                        <button
                            onClick={() => setEditBuilding(selectedBuilding)}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-primary border border-primary/30 bg-primary/10 hover:bg-primary/20 transition-colors"
                        >
                            <Pencil className="w-4 h-4" />
                            Edit
                        </button>
                        <button
                            onClick={handleDeleteBuilding}
                            disabled={deletingBuilding}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-500 border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 transition-colors disabled:opacity-60"
                        >
                            <Trash2 className="w-4 h-4" />
                            {deletingBuilding ? t('properties.deleting') : t('properties.deleteBuilding')}
                        </button>
                    </div>
                </div>

                {loadingDrill ? (
                    <div className="flex items-center justify-center h-48">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
                    </div>
                ) : buildingUnits.length === 0 ? (
                    <EmptyState
                        icon={Home}
                        title={t('properties.noUnits')}
                        subtitle={t('properties.noUnitsHint')}
                    />
                ) : (
                    <CardGrid columns="grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        {buildingUnits.map((unit, i) => (
                            <motion.div key={unit.uuid || unit.id} variants={cardVariants} transition={{ delay: i * 0.04 }}>
                                <UnitCard unit={unit} onClick={handleUnitClick} />
                            </motion.div>
                        ))}
                    </CardGrid>
                )}

                {selectedFlatUuid && (
                    <FlatDetailModal
                        flatUuid={selectedFlatUuid}
                        onClose={() => setSelectedFlatUuid(null)}
                        onFlatUpdate={handleFlatUpdate}
                        onDelete={handleFlatDelete}
                    />
                )}
                <AddPropertyModal
                    isOpen={showAddUnit}
                    onClose={() => setShowAddUnit(false)}
                    onSuccess={handleUnitAdded}
                    initialBuildingId={selectedBuilding?.id ?? null}
                    initialStreetAddress={selectedBuilding?.street_address ?? null}
                    initialCity={selectedBuilding?.city ?? null}
                    initialState={selectedBuilding?.state ?? null}
                    initialCountry={selectedBuilding?.country ?? null}
                />
                <AddBuildingModal
                    isOpen={!!editBuilding}
                    initialData={editBuilding}
                    onClose={() => setEditBuilding(null)}
                    onSuccess={handleBuildingUpdated}
                    propertyGroups={propertyGroups}
                />
            </div>
        );
    }

    // ── Render — Property drill-down (buildings inside a property) ────────────
    if (viewMode === 'properties' && selectedProperty) {
        return (
            <div className="space-y-5">
                <Breadcrumb
                    segments={[t('nav.properties'), selectedProperty.name]}
                    onBack={backFromProperty}
                />

                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-foreground">{selectedProperty.name}</h2>
                        <p className="text-sm text-muted-foreground mt-0.5">
                            {selectedProperty.building_count} {t('properties.building', {count: selectedProperty.building_count})}
                            {formatAddress(selectedProperty) && <> · {formatAddress(selectedProperty)}</>}
                        </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                            onClick={() => setShowAddBuilding(true)}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                        >
                            <Building2 className="w-4 h-4" /> {t('properties.addBuilding')}
                        </button>
                        <button
                            onClick={() => setEditGroup(selectedProperty)}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-primary border border-primary/30 bg-primary/10 hover:bg-primary/20 transition-colors"
                        >
                            <Pencil className="w-4 h-4" />
                            Edit
                        </button>
                        <button
                            onClick={handleDeleteProperty}
                            disabled={deletingProperty}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-500 border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 transition-colors disabled:opacity-60"
                        >
                            <Trash2 className="w-4 h-4" />
                            {deletingProperty ? t('properties.deleting') : t('properties.deleteProperty')}
                        </button>
                    </div>
                </div>

                {loadingDrill ? (
                    <div className="flex items-center justify-center h-48">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
                    </div>
                ) : propertyBuildings.length === 0 ? (
                    <EmptyState
                        icon={Building2}
                        title={t('properties.noBuildings')}
                        subtitle={t('properties.noBuildingsHint')}
                    />
                ) : (
                    <CardGrid>
                        {propertyBuildings.map(b => (
                            <motion.div key={b.id} variants={cardVariants}>
                                <BuildingCard
                                    building={b}
                                    onClick={drillIntoBuilding}
                                    onInfo={setInfoBuilding}
                                    onEdit={b => setEditBuilding(b)}
                                    showPropertyType={true}
                                    selectMode={selectMode}
                                    isSelected={selectedBuildingIds.has(String(b.id))}
                                    onToggle={toggleBuildingSelection}
                                />
                            </motion.div>
                        ))}
                    </CardGrid>
                )}

                <BuildingInfoModal building={infoBuilding} onClose={() => setInfoBuilding(null)} />
                <AddBuildingModal
                    isOpen={showAddBuilding}
                    onClose={() => setShowAddBuilding(false)}
                    onSuccess={handleBuildingAdded}
                    initialPropertyId={selectedProperty?.id ?? null}
                    propertyGroups={propertyGroups}
                />
                <AddBuildingModal
                    isOpen={!!editBuilding}
                    initialData={editBuilding}
                    onClose={() => setEditBuilding(null)}
                    onSuccess={handleBuildingUpdated}
                    propertyGroups={propertyGroups}
                />
                <AddPropertyGroupModal
                    isOpen={!!editGroup}
                    initialData={editGroup}
                    onClose={() => setEditGroup(null)}
                    onSuccess={handlePropertyGroupUpdated}
                />
                {selectedFlatUuid && (
                    <FlatDetailModal
                        flatUuid={selectedFlatUuid}
                        onClose={() => setSelectedFlatUuid(null)}
                        onFlatUpdate={handleFlatUpdate}
                        onDelete={handleFlatDelete}
                    />
                )}
            </div>
        );
    }

    // ── Render — Top-level views ──────────────────────────────────────────────
    return (
        <div className="space-y-5">

            {/* Header + ViewSwitcher */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <PageHeader
                    subtitle={
                        viewMode === 'properties'
                            ? `${propertyGroups.length} ${t('properties.property', {count: propertyGroups.length})}`
                            : viewMode === 'units'
                                ? t('properties.subtitleUnits', {unitCount: allUnits.length, buildingCount: buildings.length})
                                : `${buildings.length} ${t('properties.building', {count: buildings.length})}`
                    }
                />
                <div data-tour="view-switcher"><ViewSwitcher activeView={viewMode} onChange={handleViewSwitch} /></div>
            </div>

            {/* Action bar — below tabs */}
            <div data-tour="action-buttons" className="flex items-center gap-2 flex-wrap">
                {viewMode === 'properties' && (
                    <button
                        onClick={() => setShowAddProperty(true)}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                        <Layers className="w-4 h-4" /> {t('properties.addProperty')}
                    </button>
                )}
                {viewMode === 'buildings' && (
                    <button
                        onClick={() => setShowAddBuilding(true)}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                        <Building2 className="w-4 h-4" /> {t('properties.addBuilding')}
                    </button>
                )}
                <button
                    onClick={() => setShowAddUnit(true)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border bg-secondary text-foreground text-sm font-medium hover:bg-secondary/80 transition-colors"
                >
                    <Plus className="w-4 h-4" /> {t('properties.addUnit')}
                </button>
                <button
                    onClick={() => setShowCsvImport(true)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border bg-secondary text-foreground text-sm font-medium hover:bg-secondary/80 transition-colors"
                >
                    <Upload className="w-4 h-4" /> {t('properties.importCsv')}
                </button>
                <button
                    onClick={() => selectMode ? exitSelectMode() : setSelectMode(true)}
                    className={cn(
                        'flex items-center gap-1.5 px-4 py-2 rounded-lg border text-sm font-medium transition-colors',
                        selectMode
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-border bg-secondary text-foreground hover:bg-secondary/80'
                    )}
                >
                    {selectMode ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                    {selectMode ? 'Cancel Select' : 'Select'}
                </button>
            </div>

            {/* Bulk error message */}
            {bulkError && (
                <div className="px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-sm">
                    {bulkError}
                </div>
            )}

            <AnimatePresence mode="wait">
                {/* ── PROPERTIES VIEW (true top-level property entities) ── */}
                {viewMode === 'properties' && (
                    <motion.div key="properties" {...fadeSlide} className="space-y-5">
                        {propertyGroups.length === 0 ? (
                            <EmptyState
                                icon={Layers}
                                title={t('properties.noProperties')}
                                subtitle={t('properties.noPropertiesHint')}
                            />
                        ) : (
                            <div data-tour="property-list">
                            <CardGrid>
                                {propertyGroups.map(p => (
                                    <motion.div key={p.id} variants={cardVariants}>
                                        <PropertyGroupCard
                                            property={p}
                                            onClick={drillIntoProperty}
                                            onEdit={p => setEditGroup(p)}
                                            selectMode={selectMode}
                                            isSelected={selectedPropertyIds.has(String(p.id))}
                                            onToggle={togglePropertySelection}
                                        />
                                    </motion.div>
                                ))}
                            </CardGrid>
                            </div>
                        )}
                    </motion.div>
                )}

                {/* ── BUILDINGS VIEW (flat list of all buildings) ── */}
                {viewMode === 'buildings' && (
                    <motion.div key="buildings" {...fadeSlide} className="space-y-5">
                        {buildings.length === 0 ? (
                            <EmptyState icon={Building2} title={t('properties.noBuildings')} />
                        ) : (
                            <CardGrid>
                                {buildings.map(b => (
                                    <motion.div key={b.id} variants={cardVariants}>
                                        <BuildingCard
                                            building={b}
                                            onClick={drillIntoBuilding}
                                            onInfo={setInfoBuilding}
                                            onEdit={b => setEditBuilding(b)}
                                            showPropertyType={true}
                                            selectMode={selectMode}
                                            isSelected={selectedBuildingIds.has(String(b.id))}
                                            onToggle={toggleBuildingSelection}
                                        />
                                    </motion.div>
                                ))}
                            </CardGrid>
                        )}
                    </motion.div>
                )}

                {/* ── UNITS VIEW (all flats flat list) ── */}
                {viewMode === 'units' && (
                    <motion.div key="units" {...fadeSlide}>
                        {allUnits.length === 0 ? (
                            <EmptyState
                                icon={Home}
                                title={t('properties.noUnitsFound')}
                                subtitle={t('properties.noUnitsFoundHint')}
                            />
                        ) : (
                            <CardGrid columns="grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                                {allUnits.map((unit, i) => {
                                    const building = buildingLookup[unit.building_id];
                                    return (
                                        <motion.div key={unit.uuid} variants={cardVariants} transition={{ delay: i * 0.03 }}>
                                            <UnitCard
                                                unit={unit}
                                                onClick={handleUnitClick}
                                                buildingName={building?.name}
                                                propertyTypeName={building?.property_type_name}
                                                selectMode={selectMode}
                                                isSelected={selectedFlatUuids.has(unit.uuid)}
                                                onToggle={toggleFlatSelection}
                                            />
                                        </motion.div>
                                    );
                                })}
                            </CardGrid>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Floating bulk-action bar ── */}
            {selectMode && (selectedPropertyIds.size + selectedBuildingIds.size + selectedFlatUuids.size) > 0 && (
                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl bg-card border border-border shadow-xl shadow-black/20">
                    <span className="text-sm font-medium text-foreground">
                        {selectedPropertyIds.size + selectedBuildingIds.size + selectedFlatUuids.size} selected
                    </span>
                    <div className="w-px h-5 bg-border" />
                    <button
                        onClick={exitSelectMode}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleBulkDelete}
                        disabled={bulkDeleting}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-red-500 text-white text-sm font-medium hover:bg-red-600 transition-colors disabled:opacity-50"
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                        {bulkDeleting ? 'Deleting…' : 'Delete selected'}
                    </button>
                </div>
            )}

            {/* ── Modals ── */}
            {selectedFlatUuid && (
                <FlatDetailModal
                    flatUuid={selectedFlatUuid}
                    onClose={() => setSelectedFlatUuid(null)}
                    onFlatUpdate={handleFlatUpdate}
                    onDelete={handleFlatDelete}
                />
            )}
            <BuildingInfoModal building={infoBuilding} onClose={() => setInfoBuilding(null)} />
            <AddPropertyGroupModal
                isOpen={showAddProperty}
                onClose={() => setShowAddProperty(false)}
                onSuccess={handlePropertyGroupAdded}
            />
            <AddPropertyGroupModal
                isOpen={!!editGroup}
                initialData={editGroup}
                onClose={() => setEditGroup(null)}
                onSuccess={handlePropertyGroupUpdated}
            />
            <AddBuildingModal
                isOpen={showAddBuilding}
                onClose={() => setShowAddBuilding(false)}
                onSuccess={handleBuildingAdded}
                propertyGroups={propertyGroups}
            />
            <AddBuildingModal
                isOpen={!!editBuilding}
                initialData={editBuilding}
                onClose={() => setEditBuilding(null)}
                onSuccess={handleBuildingUpdated}
                propertyGroups={propertyGroups}
            />
            <AddPropertyModal
                isOpen={showAddUnit}
                onClose={() => setShowAddUnit(false)}
                onSuccess={handleUnitAdded}
            />
            <CsvImportModal
                isOpen={showCsvImport}
                onClose={() => setShowCsvImport(false)}
                defaultTab="properties"
                onSuccess={() => {
                    loadPropertyGroups();
                    loadBuildings();
                    loadAllUnits();
                }}
            />
        </div>
    );
}

// ── Shared primitives ─────────────────────────────────────────────────────────

function PageHeader({ subtitle }) {
    return (
        <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
                <Building2 className="w-8 h-8 text-primary" />
                Properties
            </h1>
            <p className="text-muted-foreground mt-1 text-sm">{subtitle}</p>
        </div>
    );
}

const fadeSlide = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -8 },
    transition: { duration: 0.22, ease: 'easeOut' },
};

export default PropertiesPage;
