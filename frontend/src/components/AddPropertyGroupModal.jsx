import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Building2, MapPin, Tag, Image, AlignLeft } from 'lucide-react';
import { cn } from '@/lib';
import { createPropertyGroup, fetchPropertyTypes } from '../services/apiService';

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

/**
 * AddPropertyGroupModal
 * Simple form to create a new top-level property entity.
 *
 * Props:
 *  - isOpen: boolean
 *  - onClose: () => void
 *  - onSuccess: (newPropertyGroup) => void
 */
function AddPropertyGroupModal({ isOpen, onClose, onSuccess }) {
    const [form, setForm] = useState({ name: '', description: '', address: '', image_url: '', property_type_id: '' });
    const [propertyTypes, setPropertyTypes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Load property types once
    useEffect(() => {
        if (!isOpen) return;
        fetchPropertyTypes()
            .then(setPropertyTypes)
            .catch(() => setPropertyTypes([]));
    }, [isOpen]);

    const reset = () => {
        setForm({ name: '', description: '', address: '', image_url: '', property_type_id: '' });
        setError('');
    };

    const handleClose = () => { reset(); onClose(); };

    const handleChange = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.name.trim()) { setError('Property name is required.'); return; }
        setLoading(true);
        setError('');
        try {
            const payload = { name: form.name.trim() };
            if (form.description.trim()) payload.description = form.description.trim();
            if (form.address.trim()) payload.address = form.address.trim();
            if (form.image_url.trim()) payload.image_url = form.image_url.trim();
            if (form.property_type_id) payload.property_type_id = form.property_type_id;

            const created = await createPropertyGroup(payload);
            onSuccess?.(created);
            handleClose();
        } catch (err) {
            setError(err.message || 'Failed to create property. Please try again.');
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
                        className="w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl overflow-hidden"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                            <div className="flex items-center gap-2.5">
                                <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-primary/10">
                                    <Building2 className="w-5 h-5 text-primary" />
                                </span>
                                <div>
                                    <h2 className="text-base font-semibold text-foreground">Add Property</h2>
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
                        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
                            {error && (
                                <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm">
                                    {error}
                                </div>
                            )}

                            <FieldGroup label="Property Name *" icon={Building2}>
                                <input
                                    name="name"
                                    value={form.name}
                                    onChange={handleChange}
                                    placeholder="e.g. Sunrise Estate"
                                    className={inputCls}
                                    autoFocus
                                />
                            </FieldGroup>

                            <FieldGroup label="Description" icon={AlignLeft}>
                                <textarea
                                    name="description"
                                    value={form.description}
                                    onChange={handleChange}
                                    placeholder="Brief description (optional)"
                                    rows={2}
                                    className={cn(inputCls, 'resize-none')}
                                />
                            </FieldGroup>

                            <FieldGroup label="Address" icon={MapPin}>
                                <input
                                    name="address"
                                    value={form.address}
                                    onChange={handleChange}
                                    placeholder="e.g. 123 Main Street, Delhi"
                                    className={inputCls}
                                />
                            </FieldGroup>

                            {/* Property Type */}
                            <FieldGroup label="Property Type" icon={Tag}>
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

                            <FieldGroup label="Cover Image URL" icon={Image}>
                                <input
                                    name="image_url"
                                    value={form.image_url}
                                    onChange={handleChange}
                                    placeholder="https://... (optional)"
                                    className={inputCls}
                                />
                            </FieldGroup>

                            {/* Actions */}
                            <div className="flex items-center justify-end gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={handleClose}
                                    className="px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                                >
                                    Cancel
                                </button>
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    type="submit"
                                    disabled={loading}
                                    className={cn(
                                        'flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold transition-all',
                                        'bg-primary text-primary-foreground hover:bg-primary/90',
                                        loading && 'opacity-60 cursor-not-allowed'
                                    )}
                                >
                                    {loading ? (
                                        <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground" />
                                    ) : (
                                        <Building2 className="w-4 h-4" />
                                    )}
                                    {loading ? 'Creating...' : 'Create Property'}
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
