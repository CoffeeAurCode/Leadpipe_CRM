import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Building2, MapPin, Tag, Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib';
import { createPropertyGroup, fetchPropertyTypes } from '../services/apiService';
import ImageUploadField from './ImageUploadField';

const ICON_MAP = {
    house: '🏠',
    shop: '🏪',
    apartment: '🏢',
};

function FieldGroup({ label, icon: Icon, children }) {
    return (
        <div className="space-y-1.5">
            <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {Icon && <Icon className="w-3.5 h-3.5" />}
                {label}
            </label>
            {children}
        </div>
    );
}

function AddPropertyGroupModal({ isOpen, onClose, onSuccess }) {
    const { t } = useTranslation();
    const [form, setForm] = useState({ name: '', description: '', street_address: '', city: '', state: '', country: 'Canada', image_url: '', property_type_id: '' });
    const [propertyTypes, setPropertyTypes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [uploadingImage, setUploadingImage] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!isOpen) return;
        fetchPropertyTypes()
            .then(setPropertyTypes)
            .catch(() => setPropertyTypes([]));
    }, [isOpen]);

    const reset = () => {
        setForm({ name: '', description: '', street_address: '', city: '', state: '', country: 'Canada', image_url: '', property_type_id: '' });
        setError('');
        setUploadingImage(false);
    };

    const handleClose = () => { reset(); onClose(); };

    const handleChange = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.name.trim()) { setError(t('propertyGroup.nameRequired')); return; }
        if (!form.street_address.trim()) { setError('Street address is required.'); return; }
        if (!form.city.trim()) { setError('City is required.'); return; }
        if (!form.state.trim()) { setError('Province / State is required.'); return; }
        if (!form.country.trim()) { setError('Country is required.'); return; }
        setLoading(true);
        setError('');
        try {
            const payload = {
                name: form.name.trim(),
                street_address: form.street_address.trim(),
                city: form.city.trim(),
                state: form.state.trim(),
                country: form.country.trim(),
            };
            if (form.description.trim()) payload.description = form.description.trim();
            if (form.image_url.trim()) payload.image_url = form.image_url.trim();
            if (form.property_type_id) payload.property_type_id = form.property_type_id;

            const created = await createPropertyGroup(payload);
            onSuccess?.(created);
            handleClose();
        } catch (err) {
            setError(err.message || t('propertyGroup.failed'));
        } finally {
            setLoading(false);
        }
    };

    const inputCls = cn(
        'w-full px-3 py-2 rounded-lg text-sm text-foreground',
        'bg-secondary border border-border',
        'focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary',
        'placeholder:text-muted-foreground transition-all'
    );

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
                    onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
                >
                    <motion.div
                        initial={{ opacity: 0, scale: 0.96, y: 12 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.96, y: 12 }}
                        transition={{ duration: 0.2 }}
                        className="w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                            <div className="flex items-center gap-2.5">
                                <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-primary/10">
                                    <Building2 className="w-5 h-5 text-primary" />
                                </span>
                                <div>
                                    <h2 className="text-base font-semibold text-foreground">{t('propertyGroup.title')}</h2>
                                    <p className="text-xs text-muted-foreground">Create a top-level property estate</p>
                                </div>
                            </div>
                            <button
                                onClick={handleClose}
                                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
                            {/* Scrollable body */}
                            <div className="overflow-y-auto flex-1 px-6 py-5 space-y-4">
                                {error && (
                                    <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm">
                                        {error}
                                    </div>
                                )}

                                <FieldGroup label={`${t('propertyGroup.name')} *`} icon={Building2}>
                                    <input
                                        name="name"
                                        value={form.name}
                                        onChange={handleChange}
                                        placeholder="e.g. Sunrise Estate"
                                        className={inputCls}
                                        autoFocus
                                    />
                                </FieldGroup>

                                <FieldGroup label={t('propertyGroup.description')}>
                                    <textarea
                                        name="description"
                                        value={form.description}
                                        onChange={handleChange}
                                        placeholder="Brief description (optional)"
                                        rows={2}
                                        className={cn(inputCls, 'resize-none')}
                                    />
                                </FieldGroup>

                                <FieldGroup label="Street Address *" icon={MapPin}>
                                    <input
                                        name="street_address"
                                        value={form.street_address}
                                        onChange={handleChange}
                                        placeholder="e.g. 123 Main Street"
                                        className={inputCls}
                                    />
                                </FieldGroup>

                                <div className="grid grid-cols-2 gap-3">
                                    <FieldGroup label="City *">
                                        <input
                                            name="city"
                                            value={form.city}
                                            onChange={handleChange}
                                            placeholder="e.g. Toronto"
                                            className={inputCls}
                                        />
                                    </FieldGroup>
                                    <FieldGroup label="Province / State *">
                                        <input
                                            name="state"
                                            value={form.state}
                                            onChange={handleChange}
                                            placeholder="e.g. Ontario"
                                            className={inputCls}
                                        />
                                    </FieldGroup>
                                </div>

                                <FieldGroup label="Country *" icon={Globe}>
                                    <input
                                        name="country"
                                        value={form.country}
                                        onChange={handleChange}
                                        placeholder="Canada"
                                        className={inputCls}
                                    />
                                </FieldGroup>

                                <FieldGroup label={t('propertyGroup.propertyType')} icon={Tag}>
                                    <select
                                        name="property_type_id"
                                        value={form.property_type_id}
                                        onChange={handleChange}
                                        className={cn(inputCls, 'cursor-pointer')}
                                    >
                                        <option value="">— Select type —</option>
                                        {propertyTypes.map(pt => (
                                            <option key={pt.id} value={pt.id}>
                                                {ICON_MAP[pt.icon_type] || '🏢'} {pt.name}
                                            </option>
                                        ))}
                                    </select>
                                </FieldGroup>

                                <ImageUploadField
                                    entityType="property"
                                    label={t('imageUpload.coverImage')}
                                    disabled={loading}
                                    onUploadStart={() => setUploadingImage(true)}
                                    onUploadComplete={(url) => { setUploadingImage(false); setForm(prev => ({ ...prev, image_url: url })); }}
                                />
                            </div>

                            {/* Sticky footer */}
                            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-card flex-shrink-0">
                                <button
                                    type="button"
                                    onClick={handleClose}
                                    className="px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                                >
                                    {t('propertyGroup.cancel')}
                                </button>
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    type="submit"
                                    disabled={loading || uploadingImage}
                                    className={cn(
                                        'flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold transition-all',
                                        'bg-primary text-primary-foreground hover:bg-primary/90',
                                        (loading || uploadingImage) && 'opacity-60 cursor-not-allowed'
                                    )}
                                >
                                    {loading || uploadingImage ? (
                                        <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground" />
                                    ) : (
                                        <Building2 className="w-4 h-4" />
                                    )}
                                    {loading ? t('propertyGroup.creating') : uploadingImage ? t('propertyGroup.uploadingImage') : t('propertyGroup.create')}
                                </motion.button>
                            </div>
                        </form>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

export default AddPropertyGroupModal;
