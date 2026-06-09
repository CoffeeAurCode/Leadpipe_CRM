import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Save, UserPlus, UserMinus, User, Home, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib';
import { updateFlat } from '../services/apiService';

const PHONE_RE = /^\+[1-9]\d{9,14}$/;
const validatePhone = val => !val || PHONE_RE.test(val) ? null : 'Enter a valid phone number with country code (e.g. +16135551234)';

export function FlatEditModal({ flat, isOpen, onClose, onUpdate, features }) {
    const { t } = useTranslation();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState("details");

    // Form States
    const [flatData, setFlatData] = useState({
        bedrooms: '',
        bathrooms: '',
        living_rooms: '1',
        kitchen: '1',
        floor_number: '',
        street_address: '',
        address_line: '',
        city: '',
        state: '',
        country: '',
    });

    const [tenantData, setTenantData] = useState({
        name: '',
        phone: ''
    });

    const f = features || { flat_details: true, tenant_details: true }; // fallback

    // Initialize data on open
    useEffect(() => {
        if (flat && isOpen) {
            setFlatData({
                bedrooms: flat.bedrooms || '',
                bathrooms: flat.bathrooms || '',
                living_rooms: flat.living_rooms ?? 1,
                kitchen: flat.kitchen ?? 1,
                floor_number: flat.floor_number || '',
                street_address: flat.street_address || flat.building_street_address || '',
                address_line: flat.address_line || '',
                city: flat.city || '',
                state: flat.state || '',
                country: flat.country || '',
            });

            if (flat.tenant) {
                setTenantData({
                    name: flat.tenant.name || '',
                    phone: flat.tenant.phone || ''
                });
            } else {
                setTenantData({ name: '', phone: '' });
            }

            // Set initial tab based on available features
            if (f.flat_details) setActiveTab("details");
            else if (f.tenant_details) setActiveTab("tenant");

            setError(null);
        }
    }, [flat, isOpen, features]);

    const handleSaveFlatDetails = async () => {
        setLoading(true);
        setError(null);
        try {
            const updatedFlat = await updateFlat(flat.uuid, {
                action: 'UPDATE_FLAT_ONLY',
                flat_details: {
                    bedrooms: parseInt(flatData.bedrooms) || null,
                    bathrooms: parseInt(flatData.bathrooms) || null,
                    living_rooms: parseInt(flatData.living_rooms) || 1,
                    kitchen: parseInt(flatData.kitchen) || 1,
                    floor_number: parseInt(flatData.floor_number) || null,
                    street_address: flatData.street_address || null,
                    address_line: flatData.address_line || null,
                    city: flatData.city || null,
                    state: flatData.state || null,
                    country: flatData.country || null,
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
        const phoneErr = validatePhone(tenantData.phone);
        if (phoneErr) { setError(phoneErr); return; }
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
        const phoneErr = validatePhone(tenantData.phone);
        if (phoneErr) { setError(phoneErr); return; }
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
        if (!confirm(t('unit.removeTenantConfirm'))) return;

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
                    <h2 className="text-2xl font-bold text-foreground">{t('unit.editTitle', { number: flat.flat_number })}</h2>
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
                        {f.flat_details && (
                            <button
                                onClick={() => setActiveTab("details")}
                                className={cn(
                                    "flex-1 px-6 py-3 text-sm font-medium transition-colors",
                                    activeTab === "details"
                                        ? "text-primary border-b-2 border-primary bg-primary/5"
                                        : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                                )}
                            >
                                {t('unit.details')}
                            </button>
                        )}
                        {f.tenant_details && (
                            <button
                                onClick={() => setActiveTab("tenant")}
                                className={cn(
                                    "flex-1 px-6 py-3 text-sm font-medium transition-colors",
                                    activeTab === "tenant"
                                        ? "text-primary border-b-2 border-primary bg-primary/5"
                                        : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                                )}
                            >
                                {hasTenant ? t('unit.tenantTabOccupied') : t('unit.tenantTabVacant')}
                            </button>
                        )}
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
                                <label className="block text-sm font-medium text-foreground mb-2">Street Address</label>
                                <input
                                    type="text"
                                    value={flatData.street_address}
                                    onChange={(e) => setFlatData({ ...flatData, street_address: e.target.value })}
                                    placeholder="e.g. Unit 4A"
                                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-2">Additional Address</label>
                                <input
                                    type="text"
                                    value={flatData.address_line}
                                    onChange={(e) => setFlatData({ ...flatData, address_line: e.target.value })}
                                    placeholder="e.g. Suite 4B"
                                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-2">City</label>
                                    <input
                                        type="text"
                                        value={flatData.city}
                                        onChange={(e) => setFlatData({ ...flatData, city: e.target.value })}
                                        placeholder="e.g. Toronto"
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-2">Province / State</label>
                                    <input
                                        type="text"
                                        value={flatData.state}
                                        onChange={(e) => setFlatData({ ...flatData, state: e.target.value })}
                                        placeholder="e.g. Ontario"
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-2">Country</label>
                                <input
                                    type="text"
                                    value={flatData.country}
                                    onChange={(e) => setFlatData({ ...flatData, country: e.target.value })}
                                    placeholder="Canada"
                                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="floor" className="block text-sm font-medium text-foreground mb-2">
                                        {t('unit.floorNumber')}
                                    </label>
                                    <input
                                        id="floor"
                                        type="number"
                                        min="0"
                                        value={flatData.floor_number}
                                        onChange={(e) => setFlatData({ ...flatData, floor_number: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="bedrooms" className="block text-sm font-medium text-foreground mb-2">
                                        {t('unit.bedrooms')}
                                    </label>
                                    <input
                                        id="bedrooms"
                                        type="number"
                                        min="0"
                                        max="10"
                                        value={flatData.bedrooms}
                                        onChange={(e) => setFlatData({ ...flatData, bedrooms: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="bathrooms" className="block text-sm font-medium text-foreground mb-2">
                                        {t('unit.bathrooms')}
                                    </label>
                                    <input
                                        id="bathrooms"
                                        type="number"
                                        min="0"
                                        max="10"
                                        value={flatData.bathrooms}
                                        onChange={(e) => setFlatData({ ...flatData, bathrooms: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="living_rooms" className="block text-sm font-medium text-foreground mb-2">
                                        Living rooms
                                    </label>
                                    <input
                                        id="living_rooms"
                                        type="number"
                                        min="0"
                                        max="20"
                                        value={flatData.living_rooms}
                                        onChange={(e) => setFlatData({ ...flatData, living_rooms: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="kitchen" className="block text-sm font-medium text-foreground mb-2">
                                        Kitchen
                                    </label>
                                    <input
                                        id="kitchen"
                                        type="number"
                                        min="0"
                                        max="5"
                                        value={flatData.kitchen}
                                        onChange={(e) => setFlatData({ ...flatData, kitchen: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    />
                                </div>
                            </div>
                            {(flatData.bedrooms || flatData.bathrooms) && (
                                <div className="px-3 py-2 rounded-lg bg-primary/5 border border-primary/20 text-sm text-foreground">
                                    Quebec size: <span className="font-semibold">
                                        {(() => {
                                            const bd = parseInt(flatData.bedrooms) || 0;
                                            const bt = parseInt(flatData.bathrooms) || 0;
                                            const lr = parseInt(flatData.living_rooms) || 1;
                                            const k = parseInt(flatData.kitchen) || 1;
                                            return `${bd + lr + k + Math.max(0, bt - 1)}½`;
                                        })()}
                                    </span>
                                </div>
                            )}
                            <div className="flex justify-end gap-3 pt-4">
                                <button
                                    onClick={onClose}
                                    className="px-4 py-2 rounded-lg bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
                                >
                                    {t('common.cancel')}
                                </button>
                                <button
                                    onClick={handleSaveFlatDetails}
                                    disabled={loading}
                                    className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? t('unit.rentSaving') : t('unit.saveChanges')}
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
                                                {t('unit.tenantName')}
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
                                                {t('unit.phoneNumber')}
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
                                            {t('unit.vacateFlat')}
                                        </button>
                                        <button
                                            onClick={handleUpdateTenant}
                                            disabled={loading}
                                            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {loading ? t('unit.rentSaving') : t('unit.updateTenant')}
                                        </button>
                                    </div>
                                </>
                            ) : (
                                // ADD NEW TENANT
                                <>
                                    <div className="bg-secondary/50 p-4 rounded-lg mb-4 text-sm text-muted-foreground flex items-center gap-2">
                                        <Home className="w-4 h-4" />
                                        {t('unit.vacantHint')}
                                    </div>
                                    <div className="space-y-4">
                                        <div>
                                            <label htmlFor="new-name" className="block text-sm font-medium text-foreground mb-2">
                                                {t('unit.tenantName')}
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
                                                {t('unit.phoneNumber')}
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
                                            {t('common.cancel')}
                                        </button>
                                        <button
                                            onClick={handleAddTenant}
                                            disabled={loading || !tenantData.name || !tenantData.phone}
                                            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                        >
                                            <UserPlus className="w-4 h-4" />
                                            {t('unit.addTenantBtn')}
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
