import { useState, useEffect } from 'react';
import { X, Upload, UserPlus, Home, Building, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { cn } from '../lib';
import { createProperty } from '../services/apiService';

export function AddPropertyModal({ isOpen, onClose, onSuccess, initialBuildingId = null, initialAddress = null, initialStreetAddress = null, initialCity = null, initialState = null, initialCountry = null }) {
    const { t } = useTranslation();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [imagePreview, setImagePreview] = useState(null);
    const [assignTenant, setAssignTenant] = useState(false);
    const [addressAutoFilled, setAddressAutoFilled] = useState(false);

    const [formData, setFormData] = useState({
        flat_number: '',
        street_address: '',
        address_line: '',
        city: '',
        state: '',
        country: 'Canada',
        floor_number: '',
        bedrooms: '',
        bathrooms: '',
        living_rooms: '1',
        kitchen: '1',
        tenant_name: '',
        tenant_phone: '',
        image: null
    });

    useEffect(() => {
        if (isOpen) {
            const updates = {};
            if (initialStreetAddress) updates.street_address = initialStreetAddress;
            if (initialCity) updates.city = initialCity;
            if (initialState) updates.state = initialState;
            if (initialCountry) updates.country = initialCountry;
            if (Object.keys(updates).length > 0) {
                setFormData(prev => ({ ...prev, ...updates }));
                setAddressAutoFilled(true);
            }
        }
    }, [isOpen, initialStreetAddress, initialCity, initialState, initialCountry]);

    const resetForm = () => {
        setFormData({
            flat_number: '',
            street_address: '',
            address_line: '',
            city: '',
            state: '',
            country: 'Canada',
            floor_number: '',
            bedrooms: '',
            bathrooms: '',
            living_rooms: '1',
            kitchen: '1',
            tenant_name: '',
            tenant_phone: '',
            image: null
        });
        setImagePreview(null);
        setAssignTenant(false);
        setAddressAutoFilled(false);
        setError(null);
    };

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                setError('Please select an image file');
                return;
            }
            if (file.size > 10 * 1024 * 1024) {
                setError('Image must be less than 10MB');
                return;
            }
            setFormData({ ...formData, image: file });
            setImagePreview(URL.createObjectURL(file));
            setError(null);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const formDataToSend = new FormData();
            formDataToSend.append('flat_number', formData.flat_number.trim().toUpperCase());

            if (formData.street_address) formDataToSend.append('street_address', formData.street_address.trim());
            if (formData.address_line) formDataToSend.append('address_line', formData.address_line.trim());
            if (formData.city) formDataToSend.append('city', formData.city.trim());
            if (formData.state) formDataToSend.append('state', formData.state.trim());
            if (formData.country) formDataToSend.append('country', formData.country.trim());

            if (formData.floor_number) {
                formDataToSend.append('floor_number', formData.floor_number);
            }

            if (formData.bedrooms) {
                formDataToSend.append('bedrooms', formData.bedrooms);
            }

            if (formData.bathrooms) {
                formDataToSend.append('bathrooms', formData.bathrooms);
            }

            if (formData.living_rooms) {
                formDataToSend.append('living_rooms', formData.living_rooms);
            }

            if (formData.kitchen) {
                formDataToSend.append('kitchen', formData.kitchen);
            }

            if (assignTenant) {
                formDataToSend.append('tenant_name', formData.tenant_name.trim());
                formDataToSend.append('tenant_phone', formData.tenant_phone.trim());
            }

            if (initialBuildingId) {
                formDataToSend.append('building_id', initialBuildingId);
            }

            if (formData.image) {
                formDataToSend.append('image', formData.image);
            }

            await createProperty(formDataToSend);
            resetForm();
            onSuccess();
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to create property');
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        resetForm();
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4"
            onClick={handleClose}>
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-card border border-border rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-2xl flex flex-col">

                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-border bg-gradient-to-r from-primary/10 to-transparent">
                    <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
                        <Building className="w-6 h-6 text-primary" />
                        {t('unit.title')}
                    </h2>
                    <button onClick={handleClose}
                        className="p-2 rounded-lg hover:bg-secondary transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
                    {/* Scrollable body */}
                    <div className="overflow-y-auto flex-1 p-6 space-y-6">
                        {/* Error Alert */}
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="p-4 rounded-lg bg-red-500/10 border border-red-500/50 text-red-500 text-sm">
                                {error}
                            </motion.div>
                        )}

                        {/* Flat Details */}
                        <div className="space-y-4">
                            <h3 className="font-semibold text-lg flex items-center gap-2">
                                <Home className="w-5 h-5 text-primary" />
                                {t('unit.details')}
                            </h3>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-2">
                                        {t('unit.flatNumber')} <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.flat_number}
                                        onChange={(e) => setFormData({ ...formData, flat_number: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                        placeholder="A401"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">Street Address <span className="text-red-500">*</span></label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.street_address}
                                        onChange={(e) => { setFormData({ ...formData, street_address: e.target.value }); setAddressAutoFilled(false); }}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                        placeholder="e.g. 123 Maple St"
                                    />
                                    {addressAutoFilled && formData.street_address && (
                                        <p className="mt-1 text-xs text-muted-foreground flex items-center gap-1">
                                            <Info className="w-3 h-3" />
                                            Auto-filled from building
                                        </p>
                                    )}
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">Additional Address</label>
                                    <input
                                        type="text"
                                        value={formData.address_line}
                                        onChange={(e) => setFormData({ ...formData, address_line: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                        placeholder="e.g. Suite 4B"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">City <span className="text-red-500">*</span></label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.city}
                                        onChange={(e) => { setFormData({ ...formData, city: e.target.value }); setAddressAutoFilled(false); }}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                        placeholder="e.g. Toronto"
                                    />
                                    {addressAutoFilled && formData.city && (
                                        <p className="mt-1 text-xs text-muted-foreground flex items-center gap-1">
                                            <Info className="w-3 h-3" />
                                            Auto-filled from building
                                        </p>
                                    )}
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">Province / State <span className="text-red-500">*</span></label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.state}
                                        onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                        placeholder="e.g. Ontario"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">Country <span className="text-red-500">*</span></label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.country}
                                        onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                        placeholder="Canada"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">{t('unit.floorNumber')}</label>
                                    <input
                                        type="number"
                                        value={formData.floor_number}
                                        onChange={(e) => setFormData({ ...formData, floor_number: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                        min="0"
                                        placeholder="4"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">{t('unit.bedrooms')} <span className="text-red-500">*</span></label>
                                    <input
                                        type="number"
                                        required
                                        min="1"
                                        max="10"
                                        value={formData.bedrooms}
                                        onChange={(e) => setFormData({ ...formData, bedrooms: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                        placeholder="2"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">{t('unit.bathrooms')} <span className="text-red-500">*</span></label>
                                    <input
                                        type="number"
                                        required
                                        min="0"
                                        max="10"
                                        value={formData.bathrooms}
                                        onChange={(e) => setFormData({ ...formData, bathrooms: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                        placeholder="1"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">Living rooms <span className="text-red-500">*</span></label>
                                    <input
                                        type="number"
                                        required
                                        min="0"
                                        max="20"
                                        value={formData.living_rooms}
                                        onChange={(e) => setFormData({ ...formData, living_rooms: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2">Kitchen <span className="text-red-500">*</span></label>
                                    <input
                                        type="number"
                                        required
                                        min="0"
                                        max="5"
                                        value={formData.kitchen}
                                        onChange={(e) => setFormData({ ...formData, kitchen: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                    />
                                </div>
                            </div>
                            {(formData.bedrooms || formData.bathrooms) && (
                                <div className="px-3 py-2 rounded-lg bg-primary/5 border border-primary/20 text-sm text-foreground">
                                    Quebec size: <span className="font-semibold">
                                        {(() => {
                                            const bd = parseInt(formData.bedrooms) || 0;
                                            const bt = parseInt(formData.bathrooms) || 0;
                                            const lr = parseInt(formData.living_rooms) || 1;
                                            const k = parseInt(formData.kitchen) || 1;
                                            return `${bd + lr + k + Math.max(0, bt - 1)}½`;
                                        })()}
                                    </span>
                                </div>
                            )}

                            {/* Image Upload */}
                            <div>
                                <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                                    <Upload className="w-4 h-4" />
                                    {t('unit.propertyImage')}
                                </label>
                                <input
                                    type="file"
                                    accept="image/*"
                                    onChange={handleImageChange}
                                    className="w-full px-3 py-2 rounded-lg border border-border bg-background file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-primary file:text-primary-foreground file:cursor-pointer hover:file:bg-primary/90 transition-all"
                                />
                                {imagePreview && (
                                    <motion.img
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        src={imagePreview}
                                        alt="Preview"
                                        className="mt-3 h-40 w-full rounded-lg object-cover border border-border"
                                    />
                                )}
                            </div>
                        </div>

                        {/* Tenant Section */}
                        <div className="space-y-4 pt-4 border-t border-border">
                            <label className="flex items-center gap-2 cursor-pointer group">
                                <input
                                    type="checkbox"
                                    checked={assignTenant}
                                    onChange={(e) => setAssignTenant(e.target.checked)}
                                    className="w-4 h-4 rounded border-border text-primary focus:ring-2 focus:ring-primary"
                                />
                                <UserPlus className="w-4 h-4 text-primary" />
                                <span className="font-semibold group-hover:text-primary transition-colors">
                                    {t('unit.assignTenant')}
                                </span>
                            </label>

                            <AnimatePresence>
                                {assignTenant && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        className="grid grid-cols-2 gap-4 pl-6 overflow-hidden">
                                        <div>
                                            <label className="block text-sm font-medium mb-2">
                                                {t('unit.tenantName')} <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="text"
                                                required={assignTenant}
                                                value={formData.tenant_name}
                                                onChange={(e) => setFormData({ ...formData, tenant_name: e.target.value })}
                                                className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                                placeholder="John Doe"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium mb-2">
                                                {t('unit.phoneNumber')} <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="tel"
                                                required={assignTenant}
                                                value={formData.tenant_phone}
                                                onChange={(e) => setFormData({ ...formData, tenant_phone: e.target.value })}
                                                className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                                                placeholder="+1234567890"
                                            />
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                    </div>

                    {/* Sticky footer */}
                    <div className="flex justify-end gap-3 px-6 py-4 border-t border-border bg-card flex-shrink-0">
                        <button
                            type="button"
                            onClick={handleClose}
                            disabled={loading}
                            className="px-5 py-2.5 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors font-medium disabled:opacity-50">
                            {t('unit.cancel')}
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-5 py-2.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-medium disabled:opacity-50 flex items-center gap-2">
                            {loading ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                                    {t('unit.creating')}
                                </>
                            ) : (
                                <>
                                    <Building className="w-4 h-4" />
                                    {t('unit.create')}
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </motion.div>
        </div>
    );
}
