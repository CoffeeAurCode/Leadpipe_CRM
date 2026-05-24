import { useState, useEffect, useCallback } from 'react';
import { DollarSign, RefreshCw, Search, Filter, Edit2, Check, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchRentSummary, updateTenantRentStatus, setRent } from '../services/apiService';
import { cn } from '@/lib';

const RENT_STATUS_OPTIONS = ['On-time', 'Upcoming', 'Overdue', 'At Risk'];

const STATUS_COLORS = {
    'On-time':  'bg-emerald-500/15 text-emerald-500 border-emerald-500/30',
    'Upcoming': 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    'Overdue':  'bg-red-500/15 text-red-500 border-red-500/30',
    'At Risk':  'bg-orange-500/15 text-orange-400 border-orange-500/30',
};

const CARD_COLORS = {
    'On-time':  { bg: 'bg-emerald-500/10', text: 'text-emerald-500', border: 'border-emerald-500/20' },
    'Upcoming': { bg: 'bg-blue-500/10',    text: 'text-blue-400',    border: 'border-blue-500/20' },
    'Overdue':  { bg: 'bg-red-500/10',     text: 'text-red-500',     border: 'border-red-500/20' },
    'At Risk':  { bg: 'bg-orange-500/10',  text: 'text-orange-400',  border: 'border-orange-500/20' },
};

function SummaryCard({ label, count }) {
    const c = CARD_COLORS[label] || {};
    return (
        <div className={cn('flex flex-col gap-1 px-5 py-4 rounded-xl border', c.bg, c.border)}>
            <span className={cn('text-2xl font-bold tabular-nums', c.text)}>{count}</span>
            <span className="text-xs text-muted-foreground font-medium">{label}</span>
        </div>
    );
}

export default function RentTab() {
    const { t } = useTranslation();
    const RENT_STATUS_LABELS = {
        'On-time':  t('tenants.rentStatusOptions.onTime'),
        'Upcoming': t('tenants.rentStatusOptions.upcoming'),
        'Overdue':  t('tenants.rentStatusOptions.overdue'),
        'At Risk':  t('tenants.rentStatusOptions.atRisk'),
    };
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');
    const [filter, setFilter] = useState('');
    const [editingRent, setEditingRent] = useState(null); // { tenant_uuid, flat_uuid, value }
    const [savingRent, setSavingRent] = useState(false);
    const [updatingStatus, setUpdatingStatus] = useState(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            const res = await fetchRentSummary();
            setData(res);
            setError(null);
        } catch (err) {
            setError('Failed to load rent summary.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const rows = (data?.rows || []).filter(row => {
        const matchSearch = !search ||
            (row.tenant_name || '').toLowerCase().includes(search.toLowerCase()) ||
            (row.flat_number || '').toLowerCase().includes(search.toLowerCase());
        const matchFilter = !filter || row.rent_status === filter;
        return matchSearch && matchFilter;
    });

    const handleStatusChange = async (tenantUuid, newStatus) => {
        setUpdatingStatus(tenantUuid);
        try {
            await updateTenantRentStatus(tenantUuid, newStatus);
            setData(prev => ({
                ...prev,
                rows: prev.rows.map(r =>
                    r.tenant_uuid === tenantUuid ? { ...r, rent_status: newStatus } : r
                ),
            }));
        } catch (err) {
            console.error('Failed to update status:', err);
        } finally {
            setUpdatingStatus(null);
        }
    };

    const handleSaveRent = async () => {
        if (!editingRent?.flat_uuid || !editingRent?.value) return;
        setSavingRent(true);
        try {
            const today = new Date().toISOString().split('T')[0];
            await setRent(editingRent.flat_uuid, parseFloat(editingRent.value), today);
            setData(prev => ({
                ...prev,
                rows: prev.rows.map(r =>
                    r.flat_uuid === editingRent.flat_uuid
                        ? { ...r, monthly_rent: parseFloat(editingRent.value) }
                        : r
                ),
            }));
            setEditingRent(null);
        } catch (err) {
            console.error('Failed to save rent:', err);
        } finally {
            setSavingRent(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <DollarSign className="w-6 h-6 text-primary" />
                    <h1 className="text-2xl font-bold text-foreground">{t('rent.overview')}</h1>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-secondary transition-colors"
                >
                    <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
                    {t('voiceStats.refresh')}
                </button>
            </div>

            {/* Summary Cards */}
            {data?.summary && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {RENT_STATUS_OPTIONS.map(s => (
                        <SummaryCard key={s} label={RENT_STATUS_LABELS[s] || s} count={data.summary[s] ?? 0} />
                    ))}
                </div>
            )}

            {/* Search + Filter */}
            <div className="flex flex-wrap gap-3 items-center p-4 bg-card border border-border rounded-xl">
                <Filter className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="relative flex-1 min-w-48">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                    <input
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="Search tenant or flat…"
                        className="w-full pl-8 pr-3 py-1.5 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                </div>
                <select
                    value={filter}
                    onChange={e => setFilter(e.target.value)}
                    className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm text-foreground cursor-pointer"
                >
                    <option value="">{t('rent.allStatuses')}</option>
                    {RENT_STATUS_OPTIONS.map(s => <option key={s} value={s}>{RENT_STATUS_LABELS[s] || s}</option>)}
                </select>
                {(search || filter) && (
                    <button
                        onClick={() => { setSearch(''); setFilter(''); }}
                        className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                        {t('tenants.clear')}
                    </button>
                )}
            </div>

            {/* Error */}
            {error && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500 text-red-500 text-sm">
                    {error}
                </div>
            )}

            {/* Table */}
            <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border bg-secondary/50">
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('tenants.flat')}</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('tenants.tenant')}</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('rent.moLabel')}</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('common.status')}</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('leasing.leads.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr>
                                    <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">
                                        {t('rent.loading')}
                                    </td>
                                </tr>
                            ) : rows.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">
                                        {t('tenants.noTenants')}
                                    </td>
                                </tr>
                            ) : rows.map(row => (
                                <tr key={row.tenant_uuid} className="border-b border-border last:border-0 hover:bg-secondary/30 transition-colors">
                                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                                        {row.flat_number || '—'}
                                    </td>
                                    <td className="px-4 py-3">
                                        <div className="font-medium text-foreground">{row.tenant_name}</div>
                                        <div className="text-xs text-muted-foreground">{row.tenant_phone}</div>
                                    </td>
                                    <td className="px-4 py-3">
                                        {editingRent?.tenant_uuid === row.tenant_uuid ? (
                                            <div className="flex items-center gap-1">
                                                <span className="text-muted-foreground text-xs">$</span>
                                                <input
                                                    type="number"
                                                    value={editingRent.value}
                                                    onChange={e => setEditingRent(p => ({ ...p, value: e.target.value }))}
                                                    className="w-24 px-2 py-0.5 rounded text-sm bg-secondary border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                                                    autoFocus
                                                />
                                                <button
                                                    onClick={handleSaveRent}
                                                    disabled={savingRent}
                                                    className="p-1 rounded text-emerald-500 hover:bg-emerald-500/10 transition-colors"
                                                >
                                                    {savingRent ? <span className="animate-spin block w-3 h-3 border-b border-emerald-500 rounded-full" /> : <Check className="w-3.5 h-3.5" />}
                                                </button>
                                                <button onClick={() => setEditingRent(null)} className="p-1 rounded text-muted-foreground hover:bg-secondary transition-colors">
                                                    <X className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        ) : (
                                            <span className="tabular-nums text-muted-foreground">
                                                {row.monthly_rent != null ? `$${Number(row.monthly_rent).toLocaleString('en-CA')}` : '—'}
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-4 py-3">
                                        <select
                                            value={row.rent_status || ''}
                                            onChange={e => handleStatusChange(row.tenant_uuid, e.target.value)}
                                            disabled={updatingStatus === row.tenant_uuid}
                                            className={cn(
                                                'px-2 py-0.5 rounded-full text-xs font-medium border cursor-pointer focus:outline-none',
                                                STATUS_COLORS[row.rent_status] || 'bg-secondary text-muted-foreground border-border'
                                            )}
                                        >
                                            <option value="">{t('rent.unset')}</option>
                                            {RENT_STATUS_OPTIONS.map(s => (
                                                <option key={s} value={s}>{RENT_STATUS_LABELS[s] || s}</option>
                                            ))}
                                        </select>
                                    </td>
                                    <td className="px-4 py-3">
                                        {row.flat_uuid && (
                                            <button
                                                onClick={() => setEditingRent({ tenant_uuid: row.tenant_uuid, flat_uuid: row.flat_uuid, value: row.monthly_rent || '' })}
                                                className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                                            >
                                                <Edit2 className="w-3 h-3" />
                                                {t('rent.editRent')}
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
