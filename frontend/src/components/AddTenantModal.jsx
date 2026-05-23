import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, UserPlus, Phone, Home, Calendar, DollarSign } from 'lucide-react';
import { cn } from '@/lib';
import { createTenant, fetchVacantFlats, setRent } from '../services/apiService';

const RENT_STATUS_OPTIONS = ['On-time', 'Upcoming', 'Overdue', 'At Risk'];

const inputCls = cn(
    'w-full px-3 py-2 rounded-lg text-sm text-foreground',
    'bg-secondary border border-border',
    'focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary',
    'placeholder:text-muted-foreground transition-all'
);

const EMPTY_FORM = {
    name: '',
    phone: '',
    flat_uuid: '',
    lease_start_date: '',
    lease_end_date: '',
    monthly_rent: '',
    rent_status: 'On-time',
    manager_notes: '',
};

export default function AddTenantModal({ isOpen, onClose, onSuccess }) {
    const [form, setForm] = useState(EMPTY_FORM);
    const [vacantFlats, setVacantFlats] = useState([]);
    const [loading, setLoading] = useState(false);
    const [loadingFlats, setLoadingFlats] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!isOpen) return;
        setForm(EMPTY_FORM);
        setError('');
        setLoadingFlats(true);
        fetchVacantFlats()
            .then(setVacantFlats)
            .catch(() => setVacantFlats([]))
            .finally(() => setLoadingFlats(false));
    }, [isOpen]);

    const handleChange = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.name.trim()) { setError('Tenant name is required.'); return; }
        if (!form.phone.trim()) { setError('Phone number is required.'); return; }

        setLoading(true);
        setError('');
        try {
            const payload = {
                name: form.name.trim(),
                phone: form.phone.trim(),
            };
            if (form.flat_uuid) payload.flat_uuid = form.flat_uuid;
            if (form.lease_start_date) payload.lease_start_date = form.lease_start_date;
            if (form.lease_end_date) payload.lease_end_date = form.lease_end_date;
            if (form.rent_status) payload.rent_status = form.rent_status;
            if (form.manager_notes.trim()) payload.manager_notes = form.manager_notes.trim();

            const newTenant = await createTenant(payload);

            // Set rent separately if provided
            if (form.monthly_rent && form.flat_uuid) {
                const today = new Date().toISOString().split('T')[0];
                await setRent(form.flat_uuid, parseFloat(form.monthly_rent), today);
            }

            onSuccess?.(newTenant);
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to add tenant. Please try again.');
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
                        className="w-full max-w-lg bg-card border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border flex-shrink-0">
                            <div className="flex items-center gap-2.5">
                                <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-primary/10">
                                    <UserPlus className="w-5 h-5 text-primary" />
                                </span>
                                <div>
                                    <h2 className="text-base font-semibold text-foreground">Add Tenant</h2>
                                    <p className="text-xs text-muted-foreground">Create a new tenant record</p>
                                </div>
                            </div>
                            <button
                                onClick={onClose}
                                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Body */}
                        <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
                            <div className="overflow-y-auto flex-1 px-6 py-5 space-y-4">
                                {error && (
                                    <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm">
                                        {error}
                                    </div>
                                )}

                                {/* Name */}
                                <div className="space-y-1.5">
                                    <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                        <UserPlus className="w-3.5 h-3.5" /> Tenant Name *
                                    </label>
                                    <input
                                        name="name"
                                        value={form.name}
                                        onChange={handleChange}
                                        placeholder="Full name"
                                        className={inputCls}
                                        autoFocus
                                    />
                                </div>

                                {/* Phone */}
                                <div className="space-y-1.5">
                                    <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                        <Phone className="w-3.5 h-3.5" /> Phone Number *
                                    </label>
                                    <input
                                        name="phone"
                                        value={form.phone}
                                        onChange={handleChange}
                                        placeholder="+91XXXXXXXXXX"
                                        className={inputCls}
                                    />
                                </div>

                                {/* Flat Assignment */}
                                <div className="space-y-1.5">
                                    <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                        <Home className="w-3.5 h-3.5" /> Assign to Flat (optional)
                                    </label>
                                    <select
                                        name="flat_uuid"
                                        value={form.flat_uuid}
                                        onChange={handleChange}
                                        className={cn(inputCls, 'cursor-pointer')}
                                        disabled={loadingFlats}
                                    >
                                        <option value="">— No flat assigned —</option>
                                        {vacantFlats.map(f => (
                                            <option key={f.uuid} value={f.uuid}>
                                                {f.flat_number}{f.address ? ` · ${f.address}` : ''}
                                            </option>
                                        ))}
                                    </select>
                                    {loadingFlats && (
                                        <p className="text-xs text-muted-foreground">Loading vacant flats…</p>
                                    )}
                                </div>

                                {/* Lease dates */}
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1.5">
                                        <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                            <Calendar className="w-3.5 h-3.5" /> Lease Start
                                        </label>
                                        <input
                                            type="date"
                                            name="lease_start_date"
                                            value={form.lease_start_date}
                                            onChange={handleChange}
                                            className={inputCls}
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                            <Calendar className="w-3.5 h-3.5" /> Lease End
                                        </label>
                                        <input
                                            type="date"
                                            name="lease_end_date"
                                            value={form.lease_end_date}
                                            onChange={handleChange}
                                            className={inputCls}
                                        />
                                    </div>
                                </div>

                                {/* Monthly Rent */}
                                {form.flat_uuid && (
                                    <div className="space-y-1.5">
                                        <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                            <DollarSign className="w-3.5 h-3.5" /> Monthly Rent ($)
                                        </label>
                                        <input
                                            type="number"
                                            name="monthly_rent"
                                            value={form.monthly_rent}
                                            onChange={handleChange}
                                            placeholder="e.g. 12000"
                                            min={0}
                                            className={inputCls}
                                        />
                                    </div>
                                )}

                                {/* Rent Status */}
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                        Rent Status
                                    </label>
                                    <select
                                        name="rent_status"
                                        value={form.rent_status}
                                        onChange={handleChange}
                                        className={cn(inputCls, 'cursor-pointer')}
                                    >
                                        {RENT_STATUS_OPTIONS.map(s => (
                                            <option key={s} value={s}>{s}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Manager Notes */}
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                        Manager Notes
                                    </label>
                                    <textarea
                                        name="manager_notes"
                                        value={form.manager_notes}
                                        onChange={handleChange}
                                        placeholder="Internal notes (not shown to tenant)"
                                        rows={2}
                                        className={cn(inputCls, 'resize-none')}
                                    />
                                </div>
                            </div>

                            {/* Footer */}
                            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-card flex-shrink-0">
                                <button
                                    type="button"
                                    onClick={onClose}
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
                                    {loading
                                        ? <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground" />
                                        : <UserPlus className="w-4 h-4" />
                                    }
                                    {loading ? 'Adding…' : 'Add Tenant'}
                                </motion.button>
                            </div>
                        </form>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
