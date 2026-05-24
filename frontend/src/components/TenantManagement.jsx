import { useState, useEffect, useCallback } from 'react';
import { Users, ChevronUp, ChevronDown, Filter, RefreshCw, UserPlus, Upload } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchTenants } from '../services/apiService';
import TenantProfile from './TenantProfile';
import AddTenantModal from './AddTenantModal';
import CsvImportModal from './CsvImportModal';
import { cn } from '@/lib';

const RENT_STATUS_VALUES = ['On-time', 'Upcoming', 'Overdue', 'At Risk'];
const LEASE_STATUS_VALUES = ['Active', 'Expiring Soon', 'Expired', 'No Lease'];

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

function SortIcon({ field, sortBy, sortOrder }) {
    if (sortBy !== field) return null;
    return sortOrder === 'asc'
        ? <ChevronUp className="w-3 h-3" />
        : <ChevronDown className="w-3 h-3" />;
}

export default function TenantManagement() {
    const { t } = useTranslation();

    const RENT_STATUS_LABELS = {
        'On-time':  t('tenants.rentStatusOptions.onTime'),
        'Upcoming': t('tenants.rentStatusOptions.upcoming'),
        'Overdue':  t('tenants.rentStatusOptions.overdue'),
        'At Risk':  t('tenants.rentStatusOptions.atRisk'),
    };

    const LEASE_STATUS_LABELS = {
        'Active':        t('tenants.leaseStatusOptions.active'),
        'Expiring Soon': t('tenants.leaseStatusOptions.expiringSoon'),
        'Expired':       t('tenants.leaseStatusOptions.expired'),
        'No Lease':      t('tenants.leaseStatusOptions.noLease'),
    };
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedTenant, setSelectedTenant] = useState(null);
    const [rentStatus, setRentStatus] = useState('');
    const [leaseStatus, setLeaseStatus] = useState('');
    const [sortBy, setSortBy] = useState('');
    const [sortOrder, setSortOrder] = useState('asc');
    const [addModalOpen, setAddModalOpen] = useState(false);
    const [importModalOpen, setImportModalOpen] = useState(false);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            const data = await fetchTenants({
                rent_status: rentStatus || undefined,
                lease_status: leaseStatus || undefined,
                sort_by: sortBy || undefined,
                sort_order: sortOrder,
            });
            setTenants(data);
            setError(null);
        } catch (err) {
            setError(t('tenants.failedToLoad'));
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [rentStatus, leaseStatus, sortBy, sortOrder, t]);

    useEffect(() => { load(); }, [load]);

    const toggleSort = (field) => {
        if (sortBy === field) {
            setSortOrder(o => o === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(field);
            setSortOrder('asc');
        }
    };

    const clearFilters = () => {
        setRentStatus('');
        setLeaseStatus('');
        setSortBy('');
        setSortOrder('asc');
    };

    // Called by TenantProfile after a successful save
    const handleTenantUpdate = (updated) => {
        setTenants(prev => prev.map(t => t.uuid === updated.uuid ? updated : t));
        setSelectedTenant(updated);
    };

    const handleTenantDelete = (deletedUuid) => {
        setTenants(prev => prev.filter(t => t.uuid !== deletedUuid));
        setSelectedTenant(null);
    };

    const hasFilters = rentStatus || leaseStatus || sortBy;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-3">
                    <Users className="w-6 h-6 text-primary" />
                    <h1 className="text-2xl font-bold text-foreground">{t('tenants.title')}</h1>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setImportModalOpen(true)}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground border border-border hover:border-primary/50 hover:text-foreground hover:bg-secondary transition-colors"
                    >
                        <Upload className="w-4 h-4" />
                        <span className="hidden sm:inline">{t('tenants.importCsv')}</span>
                    </button>
                    <button
                        onClick={() => setAddModalOpen(true)}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20"
                    >
                        <UserPlus className="w-4 h-4" />
                        <span className="hidden sm:inline">{t('tenants.addTenant')}</span>
                    </button>
                    <button
                        onClick={load}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-secondary transition-colors"
                    >
                        <RefreshCw className="w-4 h-4" />
                        {t('tenants.refresh')}
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div data-tour="tenant-filters" className="flex flex-wrap gap-3 items-center p-4 bg-card border border-border rounded-xl">
                <Filter className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <select
                    value={rentStatus}
                    onChange={e => setRentStatus(e.target.value)}
                    className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm text-foreground"
                >
                    <option value="">{t('tenants.allRentStatuses')}</option>
                    {RENT_STATUS_VALUES.map(s => <option key={s} value={s}>{RENT_STATUS_LABELS[s]}</option>)}
                </select>
                <select
                    value={leaseStatus}
                    onChange={e => setLeaseStatus(e.target.value)}
                    className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm text-foreground"
                >
                    <option value="">{t('tenants.allLeaseStatuses')}</option>
                    {LEASE_STATUS_VALUES.map(s => <option key={s} value={s}>{LEASE_STATUS_LABELS[s]}</option>)}
                </select>
                {hasFilters && (
                    <button
                        onClick={clearFilters}
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
            <div data-tour="tenant-table" className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border bg-secondary/50">
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('tenants.tenant')}</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('tenants.flat')}</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('tenants.tenancy')}</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('tenants.leaseStatus')}</th>
                                <th
                                    className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground select-none"
                                    onClick={() => toggleSort('lease_end_date')}
                                >
                                    <span className="flex items-center gap-1">
                                        {t('tenants.leaseEnd')}
                                        <SortIcon field="lease_end_date" sortBy={sortBy} sortOrder={sortOrder} />
                                    </span>
                                </th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('tenants.rentStatus')}</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('tenants.rent')}</th>
                                <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t('tenants.dueDate')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr>
                                    <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                                        {t('tenants.loading')}
                                    </td>
                                </tr>
                            ) : tenants.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                                        {t('tenants.noTenants')}
                                    </td>
                                </tr>
                            ) : (
                                tenants.map(tenant => (
                                    <tr
                                        key={tenant.uuid}
                                        onClick={() => setSelectedTenant(tenant)}
                                        className="border-b border-border last:border-0 hover:bg-secondary/40 cursor-pointer transition-colors"
                                    >
                                        <td className="px-4 py-3">
                                            <div className="font-medium text-foreground">{tenant.name}</div>
                                            <div className="text-xs text-muted-foreground">{tenant.phone}</div>
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                                            {tenant.flat_number || '—'}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">
                                            {tenant.tenancy_duration_months != null
                                                ? `${tenant.tenancy_duration_months} ${t('tenants.mo')}`
                                                : '—'}
                                        </td>
                                        <td className="px-4 py-3">
                                            {tenant.lease_status ? (
                                                <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', LEASE_STATUS_COLORS[tenant.lease_status])}>
                                                    {LEASE_STATUS_LABELS[tenant.lease_status] || tenant.lease_status}
                                                </span>
                                            ) : '—'}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">
                                            {tenant.lease_end_date || '—'}
                                        </td>
                                        <td className="px-4 py-3">
                                            {tenant.rent_status ? (
                                                <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', RENT_STATUS_COLORS[tenant.rent_status] || 'bg-secondary text-muted-foreground')}>
                                                    {RENT_STATUS_LABELS[tenant.rent_status] || tenant.rent_status}
                                                </span>
                                            ) : '—'}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground tabular-nums">
                                            {tenant.rent_amount != null
                                                ? `$${Number(tenant.rent_amount).toLocaleString('en-CA')}`
                                                : '—'}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">
                                            {tenant.due_date || '—'}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <TenantProfile
                tenant={selectedTenant}
                onClose={() => setSelectedTenant(null)}
                onUpdate={handleTenantUpdate}
                onDelete={handleTenantDelete}
            />

            <AddTenantModal
                isOpen={addModalOpen}
                onClose={() => setAddModalOpen(false)}
                onSuccess={(newTenant) => {
                    setTenants(prev => [newTenant, ...prev]);
                    setAddModalOpen(false);
                }}
            />

            <CsvImportModal
                isOpen={importModalOpen}
                onClose={() => setImportModalOpen(false)}
                defaultTab="tenants"
                onSuccess={load}
            />
        </div>
    );
}
