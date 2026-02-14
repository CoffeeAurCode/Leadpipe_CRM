import { motion, AnimatePresence } from 'framer-motion';
import { X, MapPin, Bed, Bath, User, Phone, CheckCircle2, XCircle, Home, Edit } from 'lucide-react';
import { cn } from '@/lib';
import { useEffect, useState } from 'react';
import { fetchFlatDetails } from '../services/apiService';
import { FlatEditModal } from './FlatEditModal';

function FlatDetailModal({ flatUuid, onClose }) {
    const [flatDetails, setFlatDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);

    useEffect(() => {
        loadFlatDetails();
    }, [flatUuid]);

    async function loadFlatDetails() {
        try {
            setLoading(true);
            const data = await fetchFlatDetails(flatUuid);
            setFlatDetails(data);
            setError(null);
        } catch (err) {
            console.error('Error loading flat details:', err);
            setError('Failed to load flat details');
        } finally {
            setLoading(false);
        }
    }

    const handleBackdropClick = (e) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    const handleEditSuccess = () => {
        loadFlatDetails(); // Reload details after edit
    };

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                onClick={handleBackdropClick}
            >
                <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    className={cn(
                        "bg-card border border-border rounded-xl shadow-2xl",
                        "w-full max-w-2xl max-h-[90vh] overflow-y-auto",
                        "relative"
                    )}
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header Actions */}
                    <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
                        <button
                            onClick={() => setIsEditModalOpen(true)}
                            className={cn(
                                "p-2 rounded-lg",
                                "bg-primary/10 hover:bg-primary/20",
                                "text-primary hover:text-primary/80",
                                "transition-colors"
                            )}
                            title="Edit Flat"
                        >
                            <Edit className="w-5 h-5" />
                        </button>
                        <button
                            onClick={onClose}
                            className={cn(
                                "p-2 rounded-lg",
                                "bg-secondary hover:bg-primary/20",
                                "text-muted-foreground hover:text-primary",
                                "transition-colors"
                            )}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center p-12">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                        </div>
                    ) : error ? (
                        <div className="p-8">
                            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500">
                                <p className="text-red-500">{error}</p>
                            </div>
                        </div>
                    ) : flatDetails ? (
                        <div className="p-6 space-y-6">
                            {/* Header */}
                            <div className="flex items-start gap-4 pr-20">
                                <div className="p-3 rounded-lg bg-primary/10">
                                    <Home className="w-8 h-8 text-primary" />
                                </div>
                                <div className="flex-1">
                                    <h2 className="text-2xl font-bold text-foreground">
                                        Unit #{flatDetails.flat_number}
                                    </h2>
                                    <div className="flex items-center gap-2 mt-1 text-muted-foreground">
                                        <MapPin className="w-4 h-4" />
                                        <span>{flatDetails.address || 'Address not specified'}</span>
                                    </div>
                                </div>
                                {/* Occupancy Badge */}
                                <div className="mt-2">
                                    {flatDetails.occupied ? (
                                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-500/10 text-red-500 text-sm font-medium border border-red-500/20">
                                            <XCircle className="w-4 h-4" />
                                            <span>Occupied</span>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-500/10 text-green-500 text-sm font-medium border border-green-500/20">
                                            <CheckCircle2 className="w-4 h-4" />
                                            <span>Available</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="h-px bg-border" />

                            {/* Flat Details */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                                        <Bed className="w-4 h-4 text-primary" />
                                        <span className="text-sm">Bedrooms</span>
                                    </div>
                                    <p className="text-2xl font-bold text-foreground">
                                        {flatDetails.bedrooms || 'N/A'}
                                    </p>
                                </div>
                                <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                                        <Bath className="w-4 h-4 text-primary" />
                                        <span className="text-sm">Bathrooms</span>
                                    </div>
                                    <p className="text-2xl font-bold text-foreground">
                                        {flatDetails.bedrooms ? flatDetails.bedrooms + 1 : 'N/A'}
                                    </p>
                                </div>
                            </div>

                            {/* Floor Info */}
                            {flatDetails.floor_number !== null && flatDetails.floor_number !== undefined && (
                                <div className="p-4 rounded-lg bg-secondary/30 border border-border">
                                    <p className="text-sm text-muted-foreground mb-1">Floor</p>
                                    <p className="text-lg font-semibold text-foreground">
                                        Floor {flatDetails.floor_number}
                                    </p>
                                </div>
                            )}

                            <div className="h-px bg-border" />

                            {/* Tenant Information */}
                            <div>
                                <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                                    <User className="w-5 h-5 text-primary" />
                                    Tenant Information
                                </h3>

                                {flatDetails.tenant ? (
                                    <div className="space-y-3">
                                        <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                            <p className="text-sm text-muted-foreground mb-1">Name</p>
                                            <p className="text-lg font-medium text-foreground">
                                                {flatDetails.tenant.name}
                                            </p>
                                        </div>
                                        {flatDetails.tenant.phone && (
                                            <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                                                    <Phone className="w-4 h-4" />
                                                    <span>Contact</span>
                                                </div>
                                                <p className="text-lg font-medium text-foreground">
                                                    {flatDetails.tenant.phone}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="p-6 rounded-lg bg-secondary/30 border border-dashed border-border text-center">
                                        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-muted/50 mb-3">
                                            <User className="w-6 h-6 text-muted-foreground" />
                                        </div>
                                        <p className="text-muted-foreground font-medium">Currently Vacant</p>
                                        <p className="text-sm text-muted-foreground/70 mt-1">
                                            No tenant assigned to this unit
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : null}
                </motion.div>
            </motion.div>

            {/* Edit Modal */}
            <FlatEditModal
                isOpen={isEditModalOpen}
                onClose={() => setIsEditModalOpen(false)}
                flat={flatDetails}
                onUpdate={handleEditSuccess}
            />
        </AnimatePresence>
    );
}

export default FlatDetailModal;
