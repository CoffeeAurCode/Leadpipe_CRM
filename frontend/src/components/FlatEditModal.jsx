import { useState, useEffect } from 'react';
import { X, Save, UserPlus, UserMinus, User, Home, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib';
import { updateFlat } from '../services/apiService';

export function FlatEditModal({ flat, isOpen, onClose, onUpdate }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState("details");

    // Form States
    const [flatData, setFlatData] = useState({
        bedrooms: '',
        bathrooms: '',
        floor_number: '',
        address: ''
    });

    const [tenantData, setTenantData] = useState({
        name: '',
        phone: ''
    });

    // Initialize data on open
    useEffect(() => {
        if (flat && isOpen) {
            setFlatData({
                bedrooms: flat.bedrooms || '',
                bathrooms: flat.bathrooms || '',
                floor_number: flat.floor_number || '',
                address: flat.address || ''
            });

            if (flat.tenant) {
                setTenantData({
                    name: flat.tenant.name || '',
                    phone: flat.tenant.phone || ''
                });
            } else {
                setTenantData({ name: '', phone: '' });
            }
            setError(null);
        }
    }, [flat, isOpen]);

    const handleSaveFlatDetails = async () => {
        setLoading(true);
        setError(null);
        try {
            const updatedFlat = await updateFlat(flat.uuid, {
                action: 'UPDATE_FLAT_ONLY',
                flat_details: {
                    bedrooms: parseInt(flatData.bedrooms),
                    bathrooms: parseInt(flatData.bathrooms),
                    floor_number: parseInt(flatData.floor_number),
                    address: flatData.address
                }
            });
            onUpdate(updatedFlat); // Pass updated flat to parent
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to update flat details');
        } finally {
            setLoading(false);
        }
    };

    const handleAddTenant = async () => {
        setLoading(true);
        setError(null);
        try {
            const updatedFlat = await updateFlat(flat.uuid, {
                action: 'ADD_TENANT',
                tenant_data: tenantData
            });
            onUpdate(updatedFlat);
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to add tenant');
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateTenant = async () => {
        setLoading(true);
        setError(null);
        try {
            const updatedFlat = await updateFlat(flat.uuid, {
                action: 'UPDATE_TENANT',
                tenant_data: tenantData
            });
            onUpdate(updatedFlat);
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to update tenant');
        } finally {
            setLoading(false);
        }
    };

    const handleRemoveTenant = async () => {
        if (!confirm("Are you sure you want to remove this tenant? This action cannot be undone.")) return;

        setLoading(true);
        setError(null);
        try {
            const updatedFlat = await updateFlat(flat.uuid, {
                action: 'REMOVE_TENANT'
            });
            onUpdate(updatedFlat);
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to remove tenant');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen || !flat) return null;

    const hasTenant = !!flat.tenant_uuid;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4" onClick={onClose}>
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-card border border-border rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl"
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-border">
                    <h2 className="text-2xl font-bold text-foreground">Edit Flat {flat.flat_number}</h2>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-secondary transition-colors"
                    >
                        <X className="w-5 h-5 text-muted-foreground" />
                    </button>
                </div>

                {/* Tabs */}
                <div className="border-b border-border">
                    <div className="flex">
                        <button
                            onClick={() => setActiveTab("details")}
                            className={cn(
                                "flex-1 px-6 py-3 text-sm font-medium transition-colors",
                                activeTab === "details"
                                    ? "text-primary border-b-2 border-primary bg-primary/5"
                                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                            )}
                        >
                            Flat Details
                        </button>
                        <button
                            onClick={() => setActiveTab("tenant")}
                            className={cn(
                                "flex-1 px-6 py-3 text-sm font-medium transition-colors",
                                activeTab === "tenant"
                                    ? "text-primary border-b-2 border-primary bg-primary/5"
                                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                            )}
                        >
                            Tenant ({hasTenant ? 'Occupied' : 'Vacant'})
                        </button>
                    </div>
                </div>

                {/* Error Alert */}
                {error && (
                    <div className="mx-6 mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/50 flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-red-500">{error}</p>
                    </div>
                )}

                {/* Content */}
                <div className="p-6">
                    {activeTab === "details" ? (
                        // FLAT DETAILS TAB
                        <div className="space-y-4">
                            <div>
                                <label htmlFor="address" className="block text-sm font-medium text-foreground mb-2">
                                    Building / Address
                                </label>
                                <input
                                    id="address"
                                    type="text"
                                    value={flatData.address}
                                    onChange={(e) => setFlatData({ ...flatData, address: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="floor" className="block text-sm font-medium text-foreground mb-2">
                                        Floor Number
                                    </label>
                                    <input
                                        id="floor"
                                        type="number"
                                        value={flatData.floor_number}
                                        onChange={(e) => setFlatData({ ...flatData, floor_number: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="bedrooms" className="block text-sm font-medium text-foreground mb-2">
                                        Bedrooms
                                    </label>
                                    <select
                                        id="bedrooms"
                                        value={String(flatData.bedrooms)}
                                        onChange={(e) => setFlatData({ ...flatData, bedrooms: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    >
                                        <option value="">Select</option>
                                        {[1, 2, 3, 4, 5].map(num => (
                                            <option key={num} value={String(num)}>{num} BHK</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label htmlFor="bathrooms" className="block text-sm font-medium text-foreground mb-2">
                                        Bathrooms
                                    </label>
                                    <select
                                        id="bathrooms"
                                        value={String(flatData.bathrooms)}
                                        onChange={(e) => setFlatData({ ...flatData, bathrooms: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    >
                                        <option value="">Select</option>
                                        {[1, 2, 3, 4, 5].map(num => (
                                            <option key={num} value={String(num)}>{num} Bath</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div className="flex justify-end gap-3 pt-4">
                                <button
                                    onClick={onClose}
                                    className="px-4 py-2 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSaveFlatDetails}
                                    disabled={loading}
                                    className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? 'Saving...' : 'Save Changes'}
                                </button>
                            </div>
                        </div>
                    ) : (
                        // TENANT TAB
                        <div className="space-y-4">
                            {hasTenant ? (
                                // EDIT EXISTING TENANT
                                <>
                                    <div className="space-y-4">
                                        <div>
                                            <label htmlFor="t-name" className="block text-sm font-medium text-foreground mb-2">
                                                Tenant Name
                                            </label>
                                            <input
                                                id="t-name"
                                                type="text"
                                                value={tenantData.name}
                                                onChange={(e) => setTenantData({ ...tenantData, name: e.target.value })}
                                                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                            />
                                        </div>
                                        <div>
                                            <label htmlFor="t-phone" className="block text-sm font-medium text-foreground mb-2">
                                                Phone Number
                                            </label>
                                            <input
                                                id="t-phone"
                                                type="text"
                                                value={tenantData.phone}
                                                onChange={(e) => setTenantData({ ...tenantData, phone: e.target.value })}
                                                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                            />
                                        </div>
                                    </div>
                                    <div className="flex justify-between items-center pt-4 border-t border-border mt-4">
                                        <button
                                            onClick={handleRemoveTenant}
                                            disabled={loading}
                                            className="px-4 py-2 rounded-lg bg-red-500/10 text-red-500 border border-red-500/30 hover:bg-red-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                        >
                                            <UserMinus className="w-4 h-4" />
                                            Vacate Flat
                                        </button>
                                        <button
                                            onClick={handleUpdateTenant}
                                            disabled={loading}
                                            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {loading ? 'Updating...' : 'Update Tenant'}
                                        </button>
                                    </div>
                                </>
                            ) : (
                                // ADD NEW TENANT
                                <>
                                    <div className="bg-secondary/50 p-4 rounded-lg mb-4 text-sm text-muted-foreground flex items-center gap-2">
                                        <Home className="w-4 h-4" />
                                        This flat is currently vacant. Add a tenant to mark it as occupied.
                                    </div>
                                    <div className="space-y-4">
                                        <div>
                                            <label htmlFor="new-name" className="block text-sm font-medium text-foreground mb-2">
                                                Tenant Name
                                            </label>
                                            <input
                                                id="new-name"
                                                type="text"
                                                placeholder="Jane Doe"
                                                value={tenantData.name}
                                                onChange={(e) => setTenantData({ ...tenantData, name: e.target.value })}
                                                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary placeholder:text-muted-foreground/50"
                                            />
                                        </div>
                                        <div>
                                            <label htmlFor="new-phone" className="block text-sm font-medium text-foreground mb-2">
                                                Phone Number
                                            </label>
                                            <input
                                                id="new-phone"
                                                type="text"
                                                placeholder="+1 234 567 8900"
                                                value={tenantData.phone}
                                                onChange={(e) => setTenantData({ ...tenantData, phone: e.target.value })}
                                                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary placeholder:text-muted-foreground/50"
                                            />
                                        </div>
                                    </div>
                                    <div className="flex justify-end gap-3 pt-4">
                                        <button
                                            onClick={onClose}
                                            className="px-4 py-2 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={handleAddTenant}
                                            disabled={loading || !tenantData.name || !tenantData.phone}
                                            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                        >
                                            <UserPlus className="w-4 h-4" />
                                            Add Tenant
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
}
