import { useState, useEffect } from 'react';
import { X, Building2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib';
import { fetchPropertyTypes, createBuilding } from '../services/apiService';
import ImageUploadField from './ImageUploadField';

function AddBuildingModal({ isOpen, onClose, onSuccess, initialPropertyId = null }) {
    const { t } = useTranslation();
    const [propertyTypes, setPropertyTypes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [uploadingImage, setUploadingImage] = useState(false);
    const [error, setError] = useState(null);
    const [form, setForm] = useState({
        name: '',
        description: '',
        address: '',
        image_url: '',
        property_type_id: '',
    });

    useEffect(() => {
        if (isOpen && propertyTypes.length === 0) {
            fetchPropertyTypes()
                .then(setPropertyTypes)
                .catch(() => { });
        }
    }, [isOpen]);

    const reset = () => {
        setForm({ name: '', description: '', address: '', image_url: '', property_type_id: '' });
        setError(null);
        setUploadingImage(false);
    };

    const handleClose = () => { reset(); onClose(); };

    const handleSubmit = async e => {
        e.preventDefault();
        if (!form.name.trim()) { setError(t('building.nameRequired')); return; }
        setLoading(true);
        setError(null);
        try {
            const payload = { name: form.name.trim() };
            if (form.description) payload.description = form.description.trim();
            if (form.address) payload.address = form.address.trim();
            if (form.image_url) payload.image_url = form.image_url.trim();
            if (form.property_type_id) payload.property_type_id = form.property_type_id;
            if (initialPropertyId) payload.property_id = initialPropertyId;

            const newBuilding = await createBuilding(payload);
            reset();
            onSuccess(newBuilding);
            onClose();
        } catch (err) {
            setError(err.message || t('building.failed'));
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4"
            onClick={handleClose}
        >
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                onClick={e => e.stopPropagation()}
                className="bg-card border border-border rounded-xl max-w-lg w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-border bg-gradient-to-r from-primary/10 to-transparent">
                    <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                        <Building2 className="w-5 h-5 text-primary" />
                        {t('building.title')}
                    </h2>
                    <button onClick={handleClose} className="p-2 rounded-lg hover:bg-secondary transition-colors">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
                    <div className="overflow-y-auto flex-1 p-6 space-y-4">
                        {error && (
                            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/50 text-red-500 text-sm">
                                {error}
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium mb-1.5">
                                {t('building.name')} <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                required
                                value={form.name}
                                onChange={e => setForm({ ...form, name: e.target.value })}
                                placeholder="e.g. Sunrise Tower A"
                                className={inputClass}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1.5">{t('building.propertyType')}</label>
                            <select
                                value={form.property_type_id}
                                onChange={e => setForm({ ...form, property_type_id: e.target.value })}
                                className={inputClass}
                            >
                                <option value="">{t('common.selectType')}</option>
                                {propertyTypes.map(pt => (
                                    <option key={pt.id} value={pt.id}>{pt.name}</option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1.5">{t('building.description')}</label>
                            <textarea
                                rows={2}
                                value={form.description}
                                onChange={e => setForm({ ...form, description: e.target.value })}
                                placeholder="Brief description of the building..."
                                className={cn(inputClass, 'resize-none')}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1.5">{t('building.address')}</label>
                            <input
                                type="text"
                                value={form.address}
                                onChange={e => setForm({ ...form, address: e.target.value })}
                                placeholder="e.g. 42 Oak Street, Mumbai"
                                className={inputClass}
                            />
                        </div>

                        <ImageUploadField
                            entityType="building"
                            label={t('imageUpload.coverImage')}
                            disabled={loading}
                            onUploadStart={() => setUploadingImage(true)}
                            onUploadComplete={(url) => { setUploadingImage(false); setForm(prev => ({ ...prev, image_url: url })); }}
                        />
                    </div>

                    {/* Sticky footer */}
                    <div className="flex justify-end gap-3 px-6 py-4 border-t border-border bg-card flex-shrink-0">
                        <button
                            type="button"
                            onClick={handleClose}
                            disabled={loading}
                            className="px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors font-medium disabled:opacity-50 text-sm"
                        >
                            {t('building.cancel')}
                        </button>
                        <button
                            type="submit"
                            disabled={loading || uploadingImage}
                            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-medium disabled:opacity-50 text-sm flex items-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <div className="w-3.5 h-3.5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                                    {t('building.creating')}
                                </>
                            ) : uploadingImage ? (
                                <>
                                    <div className="w-3.5 h-3.5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                                    {t('building.uploadingImage')}
                                </>
                            ) : (
                                <>
                                    <Building2 className="w-3.5 h-3.5" />
                                    {t('building.create')}
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </motion.div>
        </div>
    );
}

const inputClass = "w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-transparent transition-all text-sm";

export default AddBuildingModal;
