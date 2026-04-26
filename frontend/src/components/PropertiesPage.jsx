import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Building2, Plus, Home, Hash, Bed, Bath,
    CheckCircle2, XCircle, ArrowLeft, Layers, Trash2, Upload
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
} from '../services/apiService';

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
function PropertyGroupCard({ property, onClick }) {
    const coverImage = property.image_url ||
        'https://images.unsplash.com/photo-1486325212027-8081e485255e?q=80&w=2574&auto=format&fit=crop';

    const typeIcons = { house: '🏠', shop: '🏪', apartment: '🏢' };

    return (
        <motion.div
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2 }}
            onClick={() => onClick(property)}
            className={cn(
                'bg-card border border-border rounded-xl overflow-hidden cursor-pointer group',
                'hover:border-primary hover:shadow-lg hover:shadow-primary/10',
                'transition-colors duration-200'
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
                <div className="absolute bottom-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/50 backdrop-blur-sm text-white text-xs font-medium">
                    <Building2 className="w-3.5 h-3.5" />
                    <span>{property.building_count} {property.building_count === 1 ? 'Building' : 'Buildings'}</span>
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
                {property.address && (
                    <p className="text-xs text-muted-foreground line-clamp-1">{property.address}</p>
                )}
            </div>
        </motion.div>
    );
}

/** Unit card — used in both drill-down view and flat Unit View */
function UnitCard({ unit, onClick, buildingName, propertyTypeName }) {
    const isOccupied = !!unit.tenant_uuid;
    const flatNum = unit.flat_number;
    const floor = unit.floor_number;
    const beds = unit.bedrooms;
    const baths = unit.bathrooms;

    return (
        <motion.div
            whileHover={{ y: -1 }}
            transition={{ duration: 0.15 }}
            onClick={() => onClick(unit)}
            className={cn(
                'bg-card border border-border rounded-xl p-4 cursor-pointer group',
                'hover:border-primary hover:shadow-md hover:shadow-primary/10',
                'transition-all duration-200'
            )}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-secondary">
                        <Hash className="w-4 h-4 text-primary" />
                    </span>
                    <div>
                        <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                            Unit {flatNum}
                        </p>
                        {floor != null && (
                            <p className="text-xs text-muted-foreground">Floor {floor}</p>
                        )}
                    </div>
                </div>
                {isOccupied ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/10 text-red-500 text-xs font-medium">
                        <XCircle className="w-3 h-3" /> Occupied
                    </span>
                ) : (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-medium">
                        <CheckCircle2 className="w-3 h-3" /> Vacant
                    </span>
                )}
            </div>

            {/* Features */}
            <div className="flex items-center gap-3 text-xs text-muted-foreground border-t border-border pt-3">
                {beds != null && (
                    <span className="flex items-center gap-1">
                        <Bed className="w-3.5 h-3.5 text-primary" />
                        <span className="font-medium text-foreground">{beds}</span> Bed
                    </span>
                )}
                {baths != null && (
                    <span className="flex items-center gap-1">
                        <Bath className="w-3.5 h-3.5 text-primary" />
                        <span className="font-medium text-foreground">{baths}</span> Bath
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

    // ── Load property groups on mount ─────────────────────────────────────────
    const loadPropertyGroups = useCallback(async () => {
        try {
            setLoadingMain(true);
            const data = await fetchPropertyGroups();
            setPropertyGroups(data);
            setError(null);
        } catch (err) {
            setError('Failed to load properties. Is the backend running?');
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

    const handleBuildingAdded = (newBuilding) => {
        setBuildings(prev => [newBuilding, ...prev].sort((a, b) => a.name.localeCompare(b.name)));
        // If we're inside a property, refresh its buildings list
        if (selectedProperty) drillIntoProperty(selectedProperty);
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
            alert(err.message || 'Failed to delete property.');
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
            alert(err.message || 'Failed to delete building.');
        } finally {
            setDeletingBuilding(false);
        }
    };

    const handleFlatDelete = (deletedUuid) => {
        setBuildingUnits(prev => prev.filter(u => u.uuid !== deletedUuid));
        setAllUnits(prev => prev.filter(u => u.uuid !== deletedUuid));
        setSelectedFlatUuid(null);
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
                <PageHeader subtitle="Loading..." />
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
            : ['Buildings', selectedBuilding.name];

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
                            {totalUnits} {totalUnits === 1 ? 'unit' : 'units'} ·{' '}
                            <span className="text-green-500">{vacantCount} vacant</span> ·{' '}
                            <span className="text-red-400">{occupiedCount} occupied</span>
                            {selectedBuilding.property_type_name && (
                                <> · <span className="text-primary">{selectedBuilding.property_type_name}</span></>
                            )}
                        </p>
                    </div>
                    <button
                        onClick={handleDeleteBuilding}
                        disabled={deletingBuilding}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-500 border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 transition-colors disabled:opacity-60 flex-shrink-0"
                    >
                        <Trash2 className="w-4 h-4" />
                        {deletingBuilding ? 'Deleting…' : 'Delete Building'}
                    </button>
                </div>

                {loadingDrill ? (
                    <div className="flex items-center justify-center h-48">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
                    </div>
                ) : buildingUnits.length === 0 ? (
                    <EmptyState
                        icon={Home}
                        title="No units in this building"
                        subtitle='Use "Add Unit" below to add units to this building'
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

                <FAB icon={Plus} label="Add Unit" onClick={() => setShowAddUnit(true)} />

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
                />
            </div>
        );
    }

    // ── Render — Property drill-down (buildings inside a property) ────────────
    if (viewMode === 'properties' && selectedProperty) {
        return (
            <div className="space-y-5">
                <Breadcrumb
                    segments={['Properties', selectedProperty.name]}
                    onBack={backFromProperty}
                />

                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-foreground">{selectedProperty.name}</h2>
                        <p className="text-sm text-muted-foreground mt-0.5">
                            {selectedProperty.building_count} {selectedProperty.building_count === 1 ? 'building' : 'buildings'}
                            {selectedProperty.address && <> · {selectedProperty.address}</>}
                        </p>
                    </div>
                    <button
                        onClick={handleDeleteProperty}
                        disabled={deletingProperty}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-500 border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 transition-colors disabled:opacity-60 flex-shrink-0"
                    >
                        <Trash2 className="w-4 h-4" />
                        {deletingProperty ? 'Deleting…' : 'Delete Property'}
                    </button>
                </div>

                {loadingDrill ? (
                    <div className="flex items-center justify-center h-48">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
                    </div>
                ) : propertyBuildings.length === 0 ? (
                    <EmptyState
                        icon={Building2}
                        title="No buildings in this property"
                        subtitle='Use "Add Building" to add a building and link it to this property'
                    />
                ) : (
                    <CardGrid>
                        {propertyBuildings.map(b => (
                            <motion.div key={b.id} variants={cardVariants}>
                                <BuildingCard
                                    building={b}
                                    onClick={drillIntoBuilding}
                                    onInfo={setInfoBuilding}
                                    showPropertyType={true}
                                />
                            </motion.div>
                        ))}
                    </CardGrid>
                )}

                <FAB icon={Building2} label="Add Building" onClick={() => setShowAddBuilding(true)} />

                <BuildingInfoModal building={infoBuilding} onClose={() => setInfoBuilding(null)} />
                <AddBuildingModal
                    isOpen={showAddBuilding}
                    onClose={() => setShowAddBuilding(false)}
                    onSuccess={handleBuildingAdded}
                    initialPropertyId={selectedProperty?.id ?? null}
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
                            ? `${propertyGroups.length} ${propertyGroups.length === 1 ? 'property' : 'properties'}`
                            : viewMode === 'units'
                                ? `${allUnits.length} total units across ${buildings.length} buildings`
                                : `${buildings.length} ${buildings.length === 1 ? 'building' : 'buildings'}`
                    }
                />
                <div data-tour="view-switcher"><ViewSwitcher activeView={viewMode} onChange={handleViewSwitch} /></div>
            </div>

            <AnimatePresence mode="wait">
                {/* ── PROPERTIES VIEW (true top-level property entities) ── */}
                {viewMode === 'properties' && (
                    <motion.div key="properties" {...fadeSlide} className="space-y-5">
                        {propertyGroups.length === 0 ? (
                            <EmptyState
                                icon={Layers}
                                title="No properties yet"
                                subtitle='Click "Add Property" below to create your first property estate'
                            />
                        ) : (
                            <div data-tour="property-list">
                            <CardGrid>
                                {propertyGroups.map(p => (
                                    <motion.div key={p.id} variants={cardVariants}>
                                        <PropertyGroupCard property={p} onClick={drillIntoProperty} />
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
                            <EmptyState icon={Building2} title="No buildings yet" />
                        ) : (
                            <CardGrid>
                                {buildings.map(b => (
                                    <motion.div key={b.id} variants={cardVariants}>
                                        <BuildingCard
                                            building={b}
                                            onClick={drillIntoBuilding}
                                            onInfo={setInfoBuilding}
                                            showPropertyType={true}
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
                                title="No units found"
                                subtitle="Add units via the Add Unit button"
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
                                            />
                                        </motion.div>
                                    );
                                })}
                            </CardGrid>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Floating Action Buttons */}
            <div data-tour="fab-buttons" className="fixed bottom-8 left-8 flex flex-col gap-3 z-50">
                {viewMode === 'properties' && (
                    <FAB icon={Layers} label="Add Property" onClick={() => setShowAddProperty(true)} />
                )}
                {(viewMode === 'buildings') && (
                    <FAB icon={Building2} label="Add Building" onClick={() => setShowAddBuilding(true)} />
                )}
                <FAB icon={Plus} label="Add Unit" onClick={() => setShowAddUnit(true)} secondary />
                <FAB icon={Upload} label="Import CSV" onClick={() => setShowCsvImport(true)} secondary />
            </div>

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
            <AddBuildingModal
                isOpen={showAddBuilding}
                onClose={() => setShowAddBuilding(false)}
                onSuccess={handleBuildingAdded}
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

function FAB({ icon: Icon, label, onClick, secondary = false }) {
    return (
        <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onClick}
            className={cn(
                'flex items-center gap-2 pl-4 pr-5 py-3 rounded-full shadow-xl transition-all group',
                secondary
                    ? 'bg-card border border-border hover:border-primary text-foreground'
                    : 'bg-primary text-primary-foreground hover:bg-primary/90'
            )}
        >
            <Icon className="w-5 h-5" />
            <span className="text-sm font-medium">{label}</span>
        </motion.button>
    );
}

const fadeSlide = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -8 },
    transition: { duration: 0.22, ease: 'easeOut' },
};

export default PropertiesPage;
