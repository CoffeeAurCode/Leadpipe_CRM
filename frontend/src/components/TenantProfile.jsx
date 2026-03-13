import { useState, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, User, Calendar, CreditCard, FileText, Home, Pencil, Save, Lock, Paperclip, ExternalLink, Trash2 } from 'lucide-react';
import { updateTenant } from '../services/apiService';
import { cn } from '@/lib';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const RENT_STATUS_OPTIONS = ['On-time', 'Upcoming', 'Overdue', 'At Risk'];
const PAYMENT_SCHEDULE_OPTIONS = ['monthly', 'quarterly', 'custom'];

const RENT_STATUS_COLORS = {
    'On-time':  'bg-emerald-500/15 text-emerald-500',
    'Upcoming': 'bg-blue-500/15 text-blue-400',
    'Overdue':  'bg-red-500/15 text-red-500',
    'At Risk':  'bg-orange-500/15 text-orange-400',
};

const LEASE_STATUS_COLORS = {
    'Active':        'bg-emerald-500/15 text-emerald-500',
    'Expiring Soon': 'bg-amber-500/15 text-amber-400',
    'Expired':       'bg-red-500/15 text-red-500',
    'No Lease':      'bg-secondary text-muted-foreground',
};

function InfoRow({ label, value, className }) {
    return (
        <div className="flex justify-between items-start py-2 border-b border-border last:border-0">
            <span className="text-sm text-muted-foreground">{label}</span>
            <span className={cn('text-sm font-medium text-foreground text-right ml-4', className)}>
                {value ?? '—'}
            </span>
        </div>
    );
}

function FieldRow({ label, children }) {
    return (
        <div className="py-2 border-b border-border last:border-0 space-y-1">
            <label className="text-xs text-muted-foreground">{label}</label>
            {children}
        </div>
    );
}

const inputCls = 'w-full px-2 py-1.5 bg-secondary border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary';

export default function TenantProfile({ tenant, onClose, onUpdate }) {
    const [editing, setEditing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState(null);
    const [form, setForm] = useState({});
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef(null);

    if (!tenant) return null;

    const featureEnabled = tenant.tenant_details_enabled !== false; // true by default

    const startEdit = () => {
        setForm({
            email: tenant.email || '',
            lease_start_date: tenant.lease_start_date || '',
            lease_end_date: tenant.lease_end_date || '',
            rent_status: tenant.rent_status || '',
            payment_schedule: tenant.payment_schedule || '',
            manager_notes: tenant.manager_notes || '',
            document_urls: tenant.document_urls || [],
        });
        setSaveError(null);
        setEditing(true);
    };

    const cancelEdit = () => {
        setEditing(false);
        setSaveError(null);
    };

    const handleSave = async () => {
        setSaving(true);
        setSaveError(null);
        try {
            // Only send non-empty values; convert empty strings to null
            const payload = Object.fromEntries(
                Object.entries(form).map(([k, v]) => [k, v === '' ? null : v])
            );
            const updated = await updateTenant(tenant.uuid, payload);
            // Merge joined fields back (they aren't returned by PATCH)
            const merged = {
                ...updated,
                flat_number: tenant.flat_number,
                rent_amount: tenant.rent_amount,
                due_date: tenant.due_date,
                tenant_details_enabled: tenant.tenant_details_enabled,
                tenant_documents_enabled: tenant.tenant_documents_enabled,
            };
            onUpdate(merged);
            setEditing(false);
        } catch (err) {
            setSaveError(err.message || 'Failed to save changes.');
        } finally {
            setSaving(false);
        }
    };

    const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }));

    const handleDocUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        try {
            const fd = new FormData();
            fd.append('file', file);
            fd.append('entity_type', 'tenant_document');
            const res = await fetch(`${API_BASE_URL}/upload/image`, { method: 'POST', body: fd });
            if (!res.ok) throw new Error('Upload failed');
            const { url } = await res.json();
            setForm(f => ({ ...f, document_urls: [...(f.document_urls || []), url] }));
        } catch {
            setSaveError('Document upload failed.');
        } finally {
            setUploading(false);
            e.target.value = '';
        }
    };

    const removeDoc = (url) =>
        setForm(f => ({ ...f, document_urls: f.document_urls.filter(u => u !== url) }));

    return (
        <AnimatePresence>
            {tenant && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        className="fixed inset-0 bg-black/50 z-40"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={editing ? undefined : onClose}
                    />

                    {/* Slide-in panel */}
                    <motion.div
                        className="fixed right-0 top-0 h-full w-full max-w-md bg-card border-l border-border shadow-2xl z-50 flex flex-col"
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between p-6 border-b border-border flex-shrink-0">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                                    <User className="w-5 h-5 text-primary" />
                                </div>
                                <div>
                                    <h2 className="font-semibold text-foreground">{tenant.name}</h2>
                                    <p className="text-sm text-muted-foreground">{tenant.phone}</p>
                                    {tenant.email && (
                                        <p className="text-xs text-muted-foreground">{tenant.email}</p>
                                    )}
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {featureEnabled && !editing && (
                                    <button
                                        onClick={startEdit}
                                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
                                    >
                                        <Pencil className="w-3.5 h-3.5" /> Edit
                                    </button>
                                )}
                                <button
                                    onClick={editing ? cancelEdit : onClose}
                                    className="p-2 rounded-lg hover:bg-secondary transition-colors"
                                >
                                    <X className="w-5 h-5 text-muted-foreground" />
                                </button>
                            </div>
                        </div>

                        {/* Feature disabled state */}
                        {!featureEnabled ? (
                            <div className="flex-1 flex flex-col items-center justify-center gap-3 p-8 text-center">
                                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                                    <Lock className="w-6 h-6 text-muted-foreground" />
                                </div>
                                <p className="font-medium text-foreground">Tenant Details Disabled</p>
                                <p className="text-sm text-muted-foreground">
                                    This feature is not enabled for this unit. Enable it in Settings to view and edit tenant details.
                                </p>
                            </div>
                        ) : (
                            /* Scrollable body */
                            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                                {/* Status badges */}
                                <div className="flex gap-2 flex-wrap">
                                    {tenant.lease_status && (
                                        <span className={cn('px-3 py-1 rounded-full text-xs font-medium', LEASE_STATUS_COLORS[tenant.lease_status])}>
                                            {tenant.lease_status}
                                        </span>
                                    )}
                                    {tenant.rent_status && (
                                        <span className={cn('px-3 py-1 rounded-full text-xs font-medium', RENT_STATUS_COLORS[tenant.rent_status] || 'bg-secondary text-muted-foreground')}>
                                            {tenant.rent_status}
                                        </span>
                                    )}
                                </div>

                                {/* Property */}
                                <section>
                                    <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
                                        <Home className="w-4 h-4 text-primary" /> Property
                                    </h3>
                                    <InfoRow label="Flat" value={tenant.flat_number} />
                                    <InfoRow
                                        label="Tenancy Duration"
                                        value={tenant.tenancy_duration_months != null ? `${tenant.tenancy_duration_months} months` : null}
                                    />
                                    {editing ? (
                                        <FieldRow label="Email">
                                            <input
                                                type="email"
                                                className={inputCls}
                                                value={form.email}
                                                onChange={set('email')}
                                                placeholder="tenant@example.com"
                                            />
                                        </FieldRow>
                                    ) : (
                                        <InfoRow label="Email" value={tenant.email} />
                                    )}
                                </section>

                                {/* Contract Details */}
                                <section>
                                    <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
                                        <Calendar className="w-4 h-4 text-primary" /> Contract Details
                                    </h3>
                                    {editing ? (
                                        <>
                                            <FieldRow label="Lease Start">
                                                <input type="date" className={inputCls} value={form.lease_start_date} onChange={set('lease_start_date')} />
                                            </FieldRow>
                                            <FieldRow label="Lease End">
                                                <input type="date" className={inputCls} value={form.lease_end_date} onChange={set('lease_end_date')} />
                                            </FieldRow>
                                            <FieldRow label="Payment Schedule">
                                                <select className={inputCls} value={form.payment_schedule} onChange={set('payment_schedule')}>
                                                    <option value="">— Select —</option>
                                                    {PAYMENT_SCHEDULE_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
                                                </select>
                                            </FieldRow>
                                        </>
                                    ) : (
                                        <>
                                            <InfoRow label="Lease Start" value={tenant.lease_start_date} />
                                            <InfoRow label="Lease End" value={tenant.lease_end_date} />
                                            <InfoRow
                                                label="Lease Duration"
                                                value={tenant.lease_duration_months != null ? `${tenant.lease_duration_months} months` : null}
                                            />
                                            <InfoRow
                                                label="Days Remaining"
                                                value={tenant.remaining_time_on_lease_days != null ? `${tenant.remaining_time_on_lease_days} days` : null}
                                                className={tenant.remaining_time_on_lease_days != null && tenant.remaining_time_on_lease_days <= 30 ? 'text-amber-400' : ''}
                                            />
                                            <InfoRow label="Payment Schedule" value={tenant.payment_schedule} />
                                        </>
                                    )}
                                </section>

                                {/* Payment Summary */}
                                <section>
                                    <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
                                        <CreditCard className="w-4 h-4 text-primary" /> Payment Summary
                                    </h3>
                                    {editing ? (
                                        <FieldRow label="Rent Status">
                                            <select className={inputCls} value={form.rent_status} onChange={set('rent_status')}>
                                                <option value="">— Select —</option>
                                                {RENT_STATUS_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
                                            </select>
                                        </FieldRow>
                                    ) : (
                                        <InfoRow label="Rent Status" value={tenant.rent_status} />
                                    )}
                                    {/* Rent and due_date are read-only — come from rents table */}
                                    <InfoRow
                                        label="Monthly Rent"
                                        value={tenant.rent_amount != null ? `₹${Number(tenant.rent_amount).toLocaleString()}` : null}
                                    />
                                    <InfoRow label="Due Date" value={tenant.due_date} />
                                </section>

                                {/* Manager Notes */}
                                <section>
                                    <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
                                        <FileText className="w-4 h-4 text-primary" /> Manager Notes
                                    </h3>
                                    {editing ? (
                                        <textarea
                                            className={cn(inputCls, 'min-h-[100px] resize-y')}
                                            value={form.manager_notes}
                                            onChange={set('manager_notes')}
                                            placeholder="Add notes about this tenant…"
                                        />
                                    ) : (
                                        tenant.manager_notes ? (
                                            <p className="text-sm text-muted-foreground bg-secondary rounded-lg p-3 leading-relaxed">
                                                {tenant.manager_notes}
                                            </p>
                                        ) : (
                                            <p className="text-sm text-muted-foreground italic">No notes added.</p>
                                        )
                                    )}
                                </section>

                                {/* Documents */}
                                {tenant.tenant_documents_enabled !== false && (
                                    <section>
                                        <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
                                            <Paperclip className="w-4 h-4 text-primary" /> Documents
                                        </h3>
                                        {(editing ? form.document_urls : tenant.document_urls || []).length === 0 ? (
                                            <p className="text-sm text-muted-foreground italic">No documents uploaded.</p>
                                        ) : (
                                            <div className="space-y-2">
                                                {(editing ? form.document_urls : tenant.document_urls || []).map((url, i) => (
                                                    <div key={i} className="flex items-center justify-between gap-2 p-2 rounded-lg bg-secondary">
                                                        <a
                                                            href={url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="flex items-center gap-1.5 text-sm text-primary hover:underline truncate"
                                                        >
                                                            <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                                                            Document {i + 1}
                                                        </a>
                                                        {editing && (
                                                            <button onClick={() => removeDoc(url)} className="flex-shrink-0 text-muted-foreground hover:text-red-400 transition-colors">
                                                                <Trash2 className="w-3.5 h-3.5" />
                                                            </button>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {editing && (
                                            <div className="mt-3">
                                                <input
                                                    ref={fileInputRef}
                                                    type="file"
                                                    accept="image/*,application/pdf"
                                                    className="hidden"
                                                    onChange={handleDocUpload}
                                                />
                                                <button
                                                    onClick={() => fileInputRef.current?.click()}
                                                    disabled={uploading}
                                                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-secondary hover:bg-secondary/80 text-foreground transition-colors disabled:opacity-60"
                                                >
                                                    <Paperclip className="w-3.5 h-3.5" />
                                                    {uploading ? 'Uploading…' : 'Upload Document'}
                                                </button>
                                            </div>
                                        )}
                                    </section>
                                )}

                                {/* Save / error */}
                                {editing && (
                                    <div className="space-y-2">
                                        {saveError && (
                                            <p className="text-sm text-red-400">{saveError}</p>
                                        )}
                                        <button
                                            onClick={handleSave}
                                            disabled={saving}
                                            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm disabled:opacity-60 transition-opacity"
                                        >
                                            <Save className="w-4 h-4" />
                                            {saving ? 'Saving…' : 'Save Changes'}
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
