import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Building2, Plus } from 'lucide-react';
import PropertyCard from './PropertyCard';
import FlatDetailModal from './FlatDetailModal';
import { AddPropertyModal } from './AddPropertyModal';
import { fetchProperties } from '../services/apiService';
import { cn } from '@/lib';

function PropertiesPage() {
    const [properties, setProperties] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedFlatUuid, setSelectedFlatUuid] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);

    useEffect(() => {
        loadProperties();
    }, []);

    async function loadProperties() {
        try {
            setLoading(true);
            const data = await fetchProperties();
            setProperties(data);
            setError(null);
        } catch (err) {
            console.error('Error loading properties:', err);
            setError('Failed to load properties. Please check if the backend is running.');
        } finally {
            setLoading(false);
        }
    }

    const handlePropertyClick = (property) => {
        setSelectedFlatUuid(property.uuid);
    };

    const handleFlatUpdate = (updatedFlat) => {
        // Map FlatResponse to property structure expected by cards
        const mappedProperty = {
            id: updatedFlat.id,
            uuid: updatedFlat.uuid,
            name: `${updatedFlat.address || 'Building'} - Unit ${updatedFlat.flat_number}`,
            address: `${updatedFlat.address || 'Building'}, Floor ${updatedFlat.floor_number ?? 0}`,
            bedrooms: updatedFlat.bedrooms ?? 2,
            bathrooms: (updatedFlat.bedrooms ?? 2) + 1,
            image_url: updatedFlat.image_url || "https://images.unsplash.com/photo-1560448204-e02f11c3d0af?q=80&w=2574&auto=format&fit=crop",
            flat_number: updatedFlat.flat_number,
            floor_number: updatedFlat.floor_number ?? 0,
            tenant_uuid: updatedFlat.tenant_uuid,
            occupied: !!updatedFlat.tenant_uuid,
            created_at: updatedFlat.created_at
        };

        setProperties(prev => prev.map(p => p.uuid === updatedFlat.uuid ? mappedProperty : p));
    };

    const handleCloseModal = () => {
        setSelectedFlatUuid(null);
        // loadProperties(); // Removed to rely on in-place updates
    };

    const handleAddSuccess = () => {
        loadProperties(); // Refresh properties list after adding new property
    };

    // Container animation
    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
    };

    if (loading) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-foreground">Properties</h1>
                        <p className="text-muted-foreground mt-1">Loading properties...</p>
                    </div>
                </div>
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-foreground">Properties</h1>
                        <p className="text-muted-foreground mt-1">Error loading data</p>
                    </div>
                </div>
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500">
                    <p className="text-red-500">{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between"
            >
                <div>
                    <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
                        <Building2 className="w-8 h-8 text-primary" />
                        Properties
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        {properties.length} {properties.length === 1 ? 'property' : 'properties'} under management
                    </p>
                </div>
            </motion.div>

            {/* Properties Grid */}
            {properties.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 rounded-lg border border-border bg-card">
                    <Building2 className="w-16 h-16 text-muted-foreground opacity-50 mb-4" />
                    <p className="text-muted-foreground text-lg">No properties found</p>
                    <p className="text-muted-foreground text-sm mt-1">Properties will appear here once added</p>
                </div>
            ) : (
                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                >
                    {properties.map((property) => (
                        <motion.div key={property.uuid} variants={itemVariants}>
                            <PropertyCard property={property} onClick={handlePropertyClick} />
                        </motion.div>
                    ))}
                </motion.div>
            )}

            {/* Flat Detail Modal */}
            {selectedFlatUuid && (
                <FlatDetailModal
                    flatUuid={selectedFlatUuid}
                    onClose={handleCloseModal}
                    onFlatUpdate={handleFlatUpdate}
                />
            )}

            {/* Floating Add Property Button */}
            <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowAddModal(true)}
                className="fixed bottom-8 left-8 p-4 rounded-full bg-primary text-primary-foreground shadow-xl hover:shadow-2xl transition-all z-50 flex items-center gap-2 group">
                <Plus className="w-6 h-6" />
                <span className="max-w-0 overflow-hidden group-hover:max-w-xs transition-all duration-300 whitespace-nowrap font-medium">
                    Add Property
                </span>
            </motion.button>

            {/* Add Property Modal */}
            <AddPropertyModal
                isOpen={showAddModal}
                onClose={() => setShowAddModal(false)}
                onSuccess={handleAddSuccess}
            />
        </div>
    );
}

export default PropertiesPage;
