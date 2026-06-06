import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, UserPlus, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib';
import {
    fetchUnassignedTenants,
    assignTenantToFlat,
    createTenant,
} from '../services/apiService';

const inputCls = cn(
    'w-full px-3 py-2 rounded-lg text-sm text-foreground',
    'bg-secondary border border-border',
    'focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary',
    'placeholder:text-muted-foreground transition-all'
);

export default function AssignTenantModal({ isOpen, flatUuid, flatNumber, onClose, onSuccess }) {
    const { t } = useTranslation();
    const [tab, setTab] = useState('existing'); // 'existing' | 'new'
    const [unassigned, setUnassigned] = useState([]);
    const [selectedUuid, setSelectedUuid] = useState('');
    const [newForm, setNewForm] = useState({ name: '', phone: '' });
    const [loading, setLoading] = useState(false);
    const [loadingTenants, setLoadingTenants] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!isOpen) return;
        setTab('existing');
        setSelectedUuid('');
        setNewForm({ name: '', phone: '' });
        setError('');
        setLoadingTenants(true);
        fetchUnassignedTenants()
            .then(setUnassigned)
            .catch(() => setUnassigned([]))
            .finally(() => setLoadingTenants(false));
    }, [isOpen]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            if (tab === 'existing') {
                if (!selectedUuid) { setError('Please select a tenant.'); setLoading(false); return; }
                await assignTenantToFlat(flatUuid, selectedUuid);
            } else {
                if (!newForm.name.trim() || !newForm.phone.trim()) {
                    setError('Name and phone are required.'); setLoading(false); return;
                }
                const created = await createTenant({ name: newForm.name.trim(), phone: newForm.phone.trim(), flat_uuid: flatUuid });
                await assignTenantToFlat(flatUuid, created.uuid);
            }
            window.dispatchEvent(new Event('refresh-listings'));
            onSuccess?.();
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to assign tenant.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
                    onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
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
                            <div>
                                <h2 className="text-base font-semibold text-foreground">{t('tenants.assignTenant')}</h2>
                                <p className="text-xs text-muted-foreground">{t('tenants.flatLabel')} {flatNumber}</p>
                            </div>
                            <button onClick={onClose} className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-all">
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Tabs */}
                        <div className="flex border-b border-border">
                            {[
                                { id: 'existing', label: t('tenants.existingTenant'), icon: Users },
                                { id: 'new', label: t('tenants.newTenant'), icon: UserPlus },
                            ].map(({ id, label, icon: Icon }) => (
                                <button
                                    key={id}
                                    onClick={() => { setTab(id); setError(''); }}
                                    className={cn(
                                        'flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors',
                                        tab === id
                                            ? 'text-primary border-b-2 border-primary'
                                            : 'text-muted-foreground hover:text-foreground'
                                    )}
                                >
                                    <Icon className="w-4 h-4" />
                                    {label}
                                </button>
                            ))}
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
                            {error && (
                                <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm">
                                    {error}
                                </div>
                            )}

                            {tab === 'existing' ? (
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                        {t('tenants.selectUnassigned')}
                                    </label>
                                    {loadingTenants ? (
                                        <p className="text-sm text-muted-foreground py-2">{t('tenants.loading')}</p>
                                    ) : unassigned.length === 0 ? (
                                        <p className="text-sm text-muted-foreground py-2">{t('tenants.noUnassigned')}</p>
                                    ) : (
                                        <select
                                            value={selectedUuid}
                                            onChange={e => setSelectedUuid(e.target.value)}
                                            className={cn(inputCls, 'cursor-pointer')}
                                        >
                                            <option value="">{t('tenants.selectTenantPlaceholder')}</option>
                                            {unassigned.map(t => (
                                                <option key={t.uuid} value={t.uuid}>
                                                    {t.name} · {t.phone}
                                                </option>
                                            ))}
                                        </select>
                                    )}
                                </div>
                            ) : (
                                <>
                                    <div className="space-y-1.5">
                                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                            {t('unit.tenantName')} *
                                        </label>
                                        <input
                                            value={newForm.name}
                                            onChange={e => setNewForm(p => ({ ...p, name: e.target.value }))}
                                            placeholder="Full name"
                                            className={inputCls}
                                            autoFocus
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                            {t('common.phone')} *
                                        </label>
                                        <input
                                            value={newForm.phone}
                                            onChange={e => setNewForm(p => ({ ...p, phone: e.target.value }))}
                                            placeholder="+91XXXXXXXXXX"
                                            className={inputCls}
                                        />
                                    </div>
                                </>
                            )}

                            <div className="flex items-center justify-end gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                                >
                                    {t('common.cancel')}
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
                                    {loading
                                        ? <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground" />
                                        : <UserPlus className="w-4 h-4" />
                                    }
                                    {loading ? t('tenants.assigning') : t('tenants.confirm')}
                                </motion.button>
                            </div>
                        </form>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
