import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X, ChevronDown, ChevronUp } from 'lucide-react';
import { createListing, updateListing, fetchVacantFlats } from '../services/apiService';

const DEFAULT_RULES = {
    max_occupants: null,
    income_required: false,
    pets_allowed: 'no',
    vegetarian_only: false,
    lease_term_months: 11,
    custom_question: '',
    non_smoking: true,
};

const UTILITY_OPTIONS = [
    { key: 'heat', label: 'Heat' },
    { key: 'water', label: 'Water' },
    { key: 'electricity', label: 'Electricity' },
    { key: 'internet', label: 'Internet' },
    { key: 'cable', label: 'Cable' },
    { key: 'gas', label: 'Gas' },
];

const PARKING_OPTIONS = [
    { value: 'none', label: 'None' },
    { value: 'indoor', label: 'Indoor (included)' },
    { value: 'outdoor', label: 'Outdoor (included)' },
    { value: 'street', label: 'Street parking' },
];

const LAUNDRY_OPTIONS = [
    { value: 'none', label: 'None' },
    { value: 'in-unit', label: 'In-unit washer/dryer' },
    { value: 'in-building', label: 'In-building' },
    { value: 'coin-operated', label: 'Coin-operated' },
];

export default function AddListingModal({ isOpen, onClose, onSuccess, listing = null }) {
    const { t } = useTranslation();
    const isEdit = Boolean(listing);
    const [vacantFlats, setVacantFlats] = useState([]);
    const [rulesOpen, setRulesOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const [form, setForm] = useState({
        flat_uuid: '',
        title: '',
        monthly_rent: '',
        description: '',
        available_from: '',
        is_active: true,
        square_footage: '',
        included_utilities: [],
        parking: 'none',
        laundry: 'none',
        custom_rules: { ...DEFAULT_RULES },
    });

    useEffect(() => {
        if (!isOpen) return;
        if (isEdit && listing) {
            setForm({
                flat_uuid: listing.flat_uuid,
                title: listing.title || '',
                monthly_rent: String(listing.monthly_rent),
                description: listing.description || '',
                available_from: listing.available_from || '',
                is_active: listing.is_active,
                square_footage: listing.square_footage ? String(listing.square_footage) : '',
                included_utilities: listing.included_utilities || [],
                parking: listing.parking || 'none',
                laundry: listing.laundry || 'none',
                custom_rules: { ...DEFAULT_RULES, ...(listing.custom_rules || {}) },
            });
        } else {
            setForm({
                flat_uuid: '', title: '', monthly_rent: '', description: '',
                available_from: '', is_active: true, square_footage: '',
                included_utilities: [], parking: 'none', laundry: 'none',
                custom_rules: { ...DEFAULT_RULES },
            });
        }
        setError('');
    }, [isOpen, listing, isEdit]);

    useEffect(() => {
        if (!isOpen || isEdit) return;
        fetchVacantFlats().then(setVacantFlats).catch(() => {});
    }, [isOpen, isEdit]);

    function set(field, value) {
        setForm(f => ({ ...f, [field]: value }));
    }

    function setRule(key, value) {
        setForm(f => ({ ...f, custom_rules: { ...f.custom_rules, [key]: value } }));
    }

    function toggleUtility(key) {
        setForm(f => ({
            ...f,
            included_utilities: f.included_utilities.includes(key)
                ? f.included_utilities.filter(u => u !== key)
                : [...f.included_utilities, key],
        }));
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setError('');
        if (!form.monthly_rent || isNaN(Number(form.monthly_rent))) {
            setError(t('leasing.listings.rentError'));
            return;
        }
        setSaving(true);
        try {
            const payload = {
                ...form,
                monthly_rent: Number(form.monthly_rent),
                available_from: form.available_from || null,
                square_footage: form.square_footage ? Number(form.square_footage) : null,
                custom_rules: form.custom_rules,
            };
            let result;
            if (isEdit) {
                const { flat_uuid, ...updatePayload } = payload;
                result = await updateListing(listing.uuid, updatePayload);
            } else {
                result = await createListing(payload);
            }
            onSuccess(result);
        } catch (err) {
            setError(err.message || t('leasing.listings.failedSave'));
        } finally {
            setSaving(false);
        }
    }

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-card border border-border rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between p-5 border-b border-border">
                    <h2 className="text-lg font-semibold text-foreground">
                        {isEdit ? t('leasing.listings.editTitle') : t('leasing.listings.add')}
                    </h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-5 space-y-4">
                    {!isEdit && (
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">{t('leasing.listings.vacantFlat')}</label>
                            <select
                                value={form.flat_uuid}
                                onChange={e => set('flat_uuid', e.target.value)}
                                required
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                            >
                                <option value="">{t('leasing.listings.selectVacant')}</option>
                                {vacantFlats.map(f => {
                                    const location = [f.building_name, f.property_name].filter(Boolean).join(', ') || f.street_address || t('leasing.listings.noAddress');
                                    return <option key={f.uuid} value={f.uuid}>{f.flat_number} — {location}</option>;
                                })}
                            </select>
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1">{t('leasing.listings.titleLabel')}</label>
                        <input
                            type="text"
                            value={form.title}
                            onChange={e => set('title', e.target.value)}
                            placeholder="e.g. Spacious 2 BHK near metro"
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1">{t('leasing.listings.monthlyRentLabel')}</label>
                        <input
                            type="number"
                            value={form.monthly_rent}
                            onChange={e => set('monthly_rent', e.target.value)}
                            required
                            min={0}
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1">{t('leasing.listings.availableFrom')}</label>
                        <input
                            type="date"
                            value={form.available_from}
                            onChange={e => set('available_from', e.target.value)}
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                        />
                    </div>

                    {/* Unit Details */}
                    <div className="border border-border rounded-lg p-4 space-y-3 bg-background">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{t('leasing.listings.unitDetails')}</p>

                        <div>
                            <label className="block text-sm text-foreground mb-1">{t('leasing.listings.squareFootage')}</label>
                            <input
                                type="number"
                                min={1}
                                value={form.square_footage}
                                onChange={e => set('square_footage', e.target.value)}
                                placeholder="e.g. 850"
                                className="w-32 bg-background border border-border rounded px-2 py-1 text-sm text-foreground"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-sm text-foreground mb-1">{t('leasing.listings.parking')}</label>
                                <select
                                    value={form.parking}
                                    onChange={e => set('parking', e.target.value)}
                                    className="w-full bg-background border border-border rounded px-2 py-1 text-sm text-foreground"
                                >
                                    {PARKING_OPTIONS.map(o => (
                                        <option key={o.value} value={o.value}>{o.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm text-foreground mb-1">{t('leasing.listings.laundry')}</label>
                                <select
                                    value={form.laundry}
                                    onChange={e => set('laundry', e.target.value)}
                                    className="w-full bg-background border border-border rounded px-2 py-1 text-sm text-foreground"
                                >
                                    {LAUNDRY_OPTIONS.map(o => (
                                        <option key={o.value} value={o.value}>{o.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm text-foreground mb-2">{t('leasing.listings.includedUtilities')}</label>
                            <div className="flex flex-wrap gap-2">
                                {UTILITY_OPTIONS.map(u => (
                                    <label key={u.key} className="flex items-center gap-1.5 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={form.included_utilities.includes(u.key)}
                                            onChange={() => toggleUtility(u.key)}
                                            className="w-4 h-4"
                                        />
                                        <span className="text-sm text-foreground">{u.label}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1">{t('common.description')}</label>
                        <textarea
                            value={form.description}
                            onChange={e => set('description', e.target.value)}
                            rows={3}
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground resize-none"
                        />
                    </div>

                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="is_active"
                            checked={form.is_active}
                            onChange={e => set('is_active', e.target.checked)}
                            className="w-4 h-4"
                        />
                        <label htmlFor="is_active" className="text-sm text-foreground">{t('leasing.listings.activeHint')}</label>
                    </div>

                    {/* Qualifying Rules collapsible */}
                    <div className="border border-border rounded-lg overflow-hidden">
                        <button
                            type="button"
                            onClick={() => setRulesOpen(o => !o)}
                            className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-foreground bg-secondary"
                        >
                            {t('leasing.listings.qualifyingRules')}
                            {rulesOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                        {rulesOpen && (
                            <div className="p-4 space-y-3 bg-background">
                                <div className="flex items-center gap-2">
                                    <input type="checkbox" id="non_smoking" checked={form.custom_rules.non_smoking}
                                        onChange={e => setRule('non_smoking', e.target.checked)} className="w-4 h-4" />
                                    <label htmlFor="non_smoking" className="text-sm text-foreground">{t('leasing.listings.nonSmoking')}</label>
                                </div>
                                <div className="flex items-center gap-2">
                                    <input type="checkbox" id="income_required" checked={form.custom_rules.income_required}
                                        onChange={e => setRule('income_required', e.target.checked)} className="w-4 h-4" />
                                    <label htmlFor="income_required" className="text-sm text-foreground">{t('leasing.listings.incomeRequired')}</label>
                                </div>
                                <div className="flex items-center gap-2">
                                    <input type="checkbox" id="vegetarian_only" checked={form.custom_rules.vegetarian_only}
                                        onChange={e => setRule('vegetarian_only', e.target.checked)} className="w-4 h-4" />
                                    <label htmlFor="vegetarian_only" className="text-sm text-foreground">{t('leasing.listings.vegetarianOnly')}</label>
                                </div>
                                <div>
                                    <label className="block text-sm text-foreground mb-1">{t('leasing.listings.petsAllowed')}</label>
                                    <select value={form.custom_rules.pets_allowed}
                                        onChange={e => setRule('pets_allowed', e.target.value)}
                                        className="bg-background border border-border rounded px-2 py-1 text-sm text-foreground">
                                        <option value="yes">{t('common.yes')}</option>
                                        <option value="no">{t('common.no')}</option>
                                        <option value="small_only">{t('leasing.listings.petsSmallOnly')}</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-foreground mb-1">{t('leasing.listings.maxOccupants')}</label>
                                    <input type="number" min={1} value={form.custom_rules.max_occupants ?? ''}
                                        onChange={e => setRule('max_occupants', e.target.value ? Number(e.target.value) : null)}
                                        placeholder={t('leasing.listings.noLimit')}
                                        className="w-28 bg-background border border-border rounded px-2 py-1 text-sm text-foreground" />
                                </div>
                                <div>
                                    <label className="block text-sm text-foreground mb-1">{t('leasing.listings.leaseTerm')}</label>
                                    <input type="number" min={1} value={form.custom_rules.lease_term_months ?? ''}
                                        onChange={e => setRule('lease_term_months', e.target.value ? Number(e.target.value) : null)}
                                        className="w-28 bg-background border border-border rounded px-2 py-1 text-sm text-foreground" />
                                </div>
                                <div>
                                    <label className="block text-sm text-foreground mb-1">{t('leasing.listings.customQuestion')}</label>
                                    <input type="text" value={form.custom_rules.custom_question}
                                        onChange={e => setRule('custom_question', e.target.value)}
                                        placeholder={t('leasing.listings.customQuestionPlaceholder')}
                                        className="w-full bg-background border border-border rounded px-2 py-1 text-sm text-foreground" />
                                </div>
                            </div>
                        )}
                    </div>

                    {error && <p className="text-red-500 text-sm">{error}</p>}

                    <div className="flex gap-3 pt-2">
                        <button type="button" onClick={onClose}
                            className="flex-1 border border-border rounded-lg py-2 text-sm text-foreground hover:bg-secondary transition-colors">
                            {t('common.cancel')}
                        </button>
                        <button type="submit" disabled={saving}
                            className="flex-1 bg-primary text-primary-foreground rounded-lg py-2 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
                            {saving ? t('leasing.listings.saving') : isEdit ? t('settings.saveChanges') : t('leasing.listings.create')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
