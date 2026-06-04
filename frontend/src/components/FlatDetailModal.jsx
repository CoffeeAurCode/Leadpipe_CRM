import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { X, MapPin, Bed, Bath, User, Phone, CheckCircle2, XCircle, Home, Edit, DollarSign, Trash2 } from 'lucide-react';
import { cn } from '@/lib';
import { useEffect, useState } from 'react';
import { fetchFlatDetails, fetchActiveRent, setRent as setRentAPI, fetchUnitSettings, deleteFlat } from '../services/apiService';
import { FlatEditModal } from './FlatEditModal';

function FlatDetailModal({ flatUuid, onClose, onFlatUpdate, onDelete }) {
    const { t } = useTranslation();
    const [flatDetails, setFlatDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState(false);
    const [error, setError] = useState(null);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [rent, setRent] = useState(null);
    const [rentForm, setRentForm] = useState({ amount: '', effectiveFrom: new Date().toISOString().split('T')[0] });
    const [rentSaving, setRentSaving] = useState(false);
    const [showRentForm, setShowRentForm] = useState(false);
    const [features, setFeatures] = useState({
        rent_management: true,
        rent_due_date: false,
        flat_details: true,
        tenant_details: true,
        tenant_documents: false,
        voice_calls: false,
        sms_reminders: false,
        email_reminders: false
    });

    useEffect(() => {
        loadFlatDetails();
    }, [flatUuid]);

    async function loadFeatureFlags(unitIntId) {
        try {
            const data = await fetchUnitSettings(unitIntId);
            if (data?.features) {
                const f = data.features;
                const rentEnabled = f.rent_management?.enabled ?? true;
                setFeatures({
                    rent_management: rentEnabled,
                    rent_due_date: f.rent_due_date?.enabled ?? false,
                    flat_details: f.flat_details?.enabled ?? true,
                    tenant_details: f.tenant_details?.enabled ?? true,
                    tenant_documents: f.tenant_documents?.enabled ?? false,
                    voice_calls: f.voice_calls?.enabled ?? false,
                    sms_reminders: f.sms_reminders?.enabled ?? false,
                    email_reminders: f.email_reminders?.enabled ?? false,
                });
                if (rentEnabled) loadRent();
            } else {
                loadRent(); // fallback: no flags found, show rent
            }
        } catch {
            loadRent(); // fallback on error
        }
    }



    async function loadRent() {
        const data = await fetchActiveRent(flatUuid);
        setRent(data);
        if (data) setRentForm(prev => ({ ...prev, amount: data.monthly_rent }));
    }

    async function handleSetRent(e) {
        e.preventDefault();
        if (!rentForm.amount) return;
        try {
            setRentSaving(true);
            await setRentAPI(flatUuid, parseFloat(rentForm.amount), rentForm.effectiveFrom);
            await loadRent();
            setShowRentForm(false);
        } catch (err) {
            console.error('Failed to set rent:', err);
        } finally {
            setRentSaving(false);
        }
    }

    async function loadFlatDetails() {
        try {
            setLoading(true);
            const data = await fetchFlatDetails(flatUuid);
            setFlatDetails(data);
            setError(null);
            // Load feature flags using the integer unit id (data.id)
            if (data?.id) {
                await loadFeatureFlags(data.id);
            } else {
                loadRent(); // fallback if no integer id
            }
        } catch (err) {
            console.error('Error loading flat details:', err);
            setError(t('unit.failedLoad'));
            loadRent(); // fallback
        } finally {
            setLoading(false);
        }
    }

    const handleBackdropClick = (e) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    const handleEditSuccess = (updatedFlat) => {
        if (updatedFlat) {
            setFlatDetails(updatedFlat); // Update local state immediately
            onFlatUpdate?.(updatedFlat); // Update parent state
        } else {
            loadFlatDetails(); // Fallback if no data returned
        }
    };

    const handleDelete = async () => {
        const label = flatDetails?.flat_number ? `Unit #${flatDetails.flat_number}` : 'this unit';
        const isOccupied = !!flatDetails?.tenant_uuid;
        const msg = isOccupied
            ? t('unit.deleteConfirmOccupied', { label })
            : t('unit.deleteConfirm', { label });
        if (!window.confirm(msg)) return;
        setDeleting(true);
        try {
            await deleteFlat(flatUuid);
            onDelete?.(flatUuid);
            onClose();
        } catch (err) {
            alert(err.message || t('unit.failedDelete'));
        } finally {
            setDeleting(false);
        }
    };

    return (
        <AnimatePresence>
            <motion.div
                key={`flat-modal-${flatUuid}`}
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
                        {flatDetails && (
                            <button
                                onClick={handleDelete}
                                disabled={deleting}
                                className="p-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-500 transition-colors disabled:opacity-60"
                                title="Delete Unit"
                            >
                                <Trash2 className="w-5 h-5" />
                            </button>
                        )}
                        {(features.flat_details || features.tenant_details) && (
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
                        )}
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
                            <div className="flex items-start gap-4 pr-32">
                                <div className="p-3 rounded-lg bg-primary/10">
                                    <Home className="w-8 h-8 text-primary" />
                                </div>
                                <div className="flex-1">
                                    <h2 className="text-2xl font-bold text-foreground">
                                        Unit #{flatDetails.flat_number}
                                    </h2>
                                    <div className="flex items-center gap-2 mt-1 text-muted-foreground">
                                        <MapPin className="w-4 h-4" />
                                        <span>{
                                            (() => {
                                                const parts = [flatDetails.street_address, flatDetails.address_line, flatDetails.city, flatDetails.state, flatDetails.country].filter(Boolean);
                                                return parts.length > 0 ? parts.join(', ') : (flatDetails.address || t('unit.addressNotSpecified'));
                                            })()
                                        }</span>
                                    </div>
                                    {/* Occupancy Badge */}
                                    <div className="mt-2">
                                        {!!flatDetails.tenant_uuid ? (
                                            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-500/10 text-red-500 text-sm font-medium border border-red-500/20">
                                                <XCircle className="w-4 h-4" />
                                                <span>{t('properties.unitStatus.occupied')}</span>
                                            </div>
                                        ) : (
                                            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-500/10 text-green-500 text-sm font-medium border border-green-500/20">
                                                <CheckCircle2 className="w-4 h-4" />
                                                <span>{t('unit.available')}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="h-px bg-border" />

                            {/* Flat Details */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                                        <Bed className="w-4 h-4 text-primary" />
                                        <span className="text-sm">{t('unit.bedrooms')}</span>
                                    </div>
                                    <p className="text-2xl font-bold text-foreground">
                                        {flatDetails.bedrooms || 'N/A'}
                                    </p>
                                </div>
                                <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                                        <Bath className="w-4 h-4 text-primary" />
                                        <span className="text-sm">{t('unit.bathrooms')}</span>
                                    </div>
                                    <p className="text-2xl font-bold text-foreground">
                                        {flatDetails.bathrooms || 'N/A'}
                                    </p>
                                </div>
                            </div>

                            {/* Floor Info */}
                            {flatDetails.floor_number !== null && flatDetails.floor_number !== undefined && (
                                <div className="p-4 rounded-lg bg-secondary/30 border border-border">
                                    <p className="text-sm text-muted-foreground mb-1">{t('properties.floor')}</p>
                                    <p className="text-lg font-semibold text-foreground">
                                        {t('properties.floor')} {flatDetails.floor_number}
                                    </p>
                                </div>
                            )}

                            <div className="h-px bg-border" />

                            {/* Rent Information — each flag is independent */}
                            {(features.rent_management || features.rent_due_date) && (
                                <div>
                                    <div className="flex items-center justify-between mb-3">
                                        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                                            <DollarSign className="w-5 h-5 text-primary" />
                                            {t('unit.rentLabel')}
                                        </h3>
                                        {(features.rent_management || features.rent_due_date) && (
                                            <button
                                                onClick={() => setShowRentForm(v => !v)}
                                                className="text-sm text-primary hover:underline"
                                            >
                                                {showRentForm ? t('unit.cancel') : rent ? t('unit.updateRent') : t('unit.setRent')}
                                            </button>
                                        )}
                                    </div>

                                    {!showRentForm && (
                                        rent ? (
                                            <div className="grid grid-cols-2 gap-3">
                                                {/* Rent amount — gated by rent_management */}
                                                {features.rent_management && (
                                                    <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                                        <p className="text-sm text-muted-foreground mb-1">{t('rent.monthlyRent')}</p>
                                                        <p className="text-2xl font-bold text-foreground">
                                                            ${Number(rent.monthly_rent).toLocaleString('en-CA')}
                                                        </p>
                                                    </div>
                                                )}
                                                {/* Due date — gated by rent_due_date */}
                                                {features.rent_due_date && (
                                                    <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                                        <p className="text-sm text-muted-foreground mb-1">{t('rent.effectiveFrom')}</p>
                                                        <p className="text-lg font-semibold text-foreground">
                                                            {new Date(rent.effective_from).toLocaleDateString('en-CA', { day: 'numeric', month: 'short', year: 'numeric' })}
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="p-4 rounded-lg bg-secondary/30 border border-dashed border-border text-center">
                                                <p className="text-muted-foreground text-sm">{t('unit.noRentForUnit')}</p>
                                            </div>
                                        )
                                    )}

                                    {showRentForm && (
                                        <form onSubmit={handleSetRent} className="space-y-3">
                                            <div className="p-4 rounded-lg bg-secondary/50 border border-border space-y-3">
                                                {/* Amount field — only if rent_management enabled */}
                                                {features.rent_management && (
                                                    <div>
                                                        <label className="text-sm text-muted-foreground block mb-1">{t('unit.monthlyRentLabel')}</label>
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            step="0.01"
                                                            required={features.rent_management}
                                                            value={rentForm.amount}
                                                            onChange={e => setRentForm(p => ({ ...p, amount: e.target.value }))}
                                                            className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                                            placeholder="e.g. 15000"
                                                        />
                                                    </div>
                                                )}
                                                {/* Date field — only if rent_due_date enabled */}
                                                {features.rent_due_date && (
                                                    <div>
                                                        <label className="text-sm text-muted-foreground block mb-1">{t('unit.effectiveFromLabel')}</label>
                                                        <input
                                                            type="date"
                                                            required={features.rent_due_date}
                                                            value={rentForm.effectiveFrom}
                                                            onChange={e => setRentForm(p => ({ ...p, effectiveFrom: e.target.value }))}
                                                            className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                                        />
                                                    </div>
                                                )}
                                                <button
                                                    type="submit"
                                                    disabled={rentSaving}
                                                    className="w-full py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-60"
                                                >
                                                    {rentSaving ? t('unit.rentSaving') : t('unit.saveRent')}
                                                </button>
                                            </div>
                                        </form>
                                    )}
                                </div>
                            )}

                            <div className="h-px bg-border" />

                            {/* Tenant Information — only if tenant_details is enabled */}
                            {features.tenant_details && (
                                <div>
                                    <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                                        <User className="w-5 h-5 text-primary" />
                                        {t('unit.tenantInfo')}
                                    </h3>

                                    {flatDetails.tenant ? (
                                        <div className="space-y-3">
                                            <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                                <p className="text-sm text-muted-foreground mb-1">{t('common.name')}</p>
                                                <p className="text-lg font-medium text-foreground">
                                                    {flatDetails.tenant.name}
                                                </p>
                                            </div>
                                            {flatDetails.tenant.phone && (
                                                <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                                                    <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                                                        <Phone className="w-4 h-4" />
                                                        <span>{t('unit.contact')}</span>
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
                                            <p className="text-muted-foreground font-medium">{t('unit.currentlyVacant')}</p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Tenant Documents — only if tenant_documents is enabled */}
                            {features.tenant_documents && flatDetails.tenant && (
                                <>
                                    <div className="h-px bg-border" />
                                    <div>
                                        <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><line x1="10" y1="9" x2="8" y2="9" /></svg>
                                            {t('unit.tenantDocs')}
                                        </h3>
                                        <div className="p-6 rounded-lg bg-secondary/30 border border-dashed border-border text-center">
                                            <p className="text-muted-foreground font-medium">{t('unit.docStorage')}</p>
                                            <p className="text-sm text-muted-foreground/70 mt-1 mb-3">
                                                {t('unit.docStorageHint')}
                                            </p>
                                            <button className="px-4 py-2 border border-primary text-primary rounded-lg text-sm font-medium hover:bg-primary/5 transition-colors">
                                                {t('unit.uploadDoc')}
                                            </button>
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    ) : null}
                </motion.div>
            </motion.div>

            {/* Edit Modal */}
            {isEditModalOpen && (
                <FlatEditModal
                    key="flat-edit-modal"
                    isOpen={isEditModalOpen}
                    onClose={() => setIsEditModalOpen(false)}
                    flat={flatDetails}
                    onUpdate={handleEditSuccess}
                    features={features}
                />
            )}
        </AnimatePresence>
    );
}

export default FlatDetailModal;
