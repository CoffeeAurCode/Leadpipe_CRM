import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Pencil, Trash2, ExternalLink, Phone, BedDouble, Banknote, PhoneCall, RefreshCw, Loader2 } from 'lucide-react';
import {
    getListings, deleteListing,
    getLeaseLeads, deleteLead,
    getLeasingMetrics, exportLeads,
    getUserVapiConfig, retryUserProvisioning,
} from '../services/apiService';
import AddListingModal from './AddListingModal';
import LeadDetailModal from './LeadDetailModal';

const STATUS_BADGE = {
    qualified:     'bg-green-500/10 text-green-500',
    not_qualified: 'bg-red-500/10 text-red-500',
    unmatched:     'bg-yellow-500/10 text-yellow-600',
    contacted:     'bg-blue-500/10 text-blue-500',
    toured:        'bg-purple-500/10 text-purple-500',
    converted:     'bg-emerald-500/10 text-emerald-500',
    lost:          'bg-muted text-muted-foreground',
};

function MetricCard({ label, value, sub }) {
    return (
        <div className="bg-card border border-border rounded-xl p-4">
            <p className="text-xs text-muted-foreground mb-1">{label}</p>
            <p className="text-2xl font-bold text-foreground">{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
        </div>
    );
}

function fmtDuration(secs) {
    if (!secs) return '—';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s}s`;
}

export default function LeasingTab() {
    const { t } = useTranslation();
    const [listings, setListings] = useState([]);
    const [leads, setLeads] = useState([]);
    const [metrics, setMetrics] = useState(null);
    const [vapiConfig, setVapiConfig] = useState(null);
    const [retrying, setRetrying] = useState(false);
    const [loading, setLoading] = useState(true);

    const [listingFilter, setListingFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');

    const [showAddListing, setShowAddListing] = useState(false);
    const [editListing, setEditListing] = useState(null);
    const [selectedLead, setSelectedLead] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [l, ld, m, vc] = await Promise.all([
                getListings(),
                getLeaseLeads(),
                getLeasingMetrics(),
                getUserVapiConfig(),
            ]);
            setListings(l);
            setLeads(ld);
            setMetrics(m);
            setVapiConfig(vc);
        } catch (e) {
            console.error('Leasing load error', e);
        } finally {
            setLoading(false);
        }
    }, []);

    async function handleRetryProvisioning() {
        if (retrying) return;
        setRetrying(true);
        try {
            await retryUserProvisioning();
            setVapiConfig(prev => ({ ...prev, vapi_provisioning_status: 'pending' }));
            // Poll once after 8s to catch quick success without user having to refresh.
            setTimeout(async () => {
                try {
                    const vc = await getUserVapiConfig();
                    setVapiConfig(vc);
                } catch (_) {}
                setRetrying(false);
            }, 8000);
        } catch (e) {
            console.error('Retry provisioning error', e);
            setRetrying(false);
        }
    }

    useEffect(() => { load(); }, [load]);

    async function handleDeleteListing(uuid) {
        if (!confirm(t('leasing.listings.confirmDelete'))) return;
        await deleteListing(uuid);
        setListings(prev => prev.filter(l => l.uuid !== uuid));
    }

    async function handleDeleteLead(uuid) {
        if (!confirm(t('leasing.leads.confirmDelete'))) return;
        await deleteLead(uuid);
        setLeads(prev => prev.filter(l => l.uuid !== uuid));
    }

    function handleListingSuccess(result) {
        if (editListing) {
            setListings(prev => prev.map(l => l.uuid === result.uuid ? result : l));
        } else {
            setListings(prev => [result, ...prev]);
        }
        setShowAddListing(false);
        setEditListing(null);
    }

    function handleLeadUpdated(updated) {
        setLeads(prev => prev.map(l => l.uuid === updated.uuid ? updated : l));
        setSelectedLead(null);
    }

    const filteredLeads = leads.filter(l => {
        if (listingFilter && l.listing_uuid !== listingFilter) return false;
        if (statusFilter && l.qualification_status !== statusFilter) return false;
        return true;
    });

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <p className="text-muted-foreground text-sm">{t('leasing.loading')}</p>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-foreground">{t('leasing.title')}</h1>
                    <p className="text-muted-foreground text-sm mt-1">{t('leasing.subtitle')}</p>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-2 border border-border rounded-lg px-3 py-2 text-sm text-foreground hover:bg-secondary transition-colors"
                >
                    <RefreshCw className="w-4 h-4" /> {t('leasing.refresh')}
                </button>
            </div>

            {/* Account-level lease line status */}
            {vapiConfig && (
                <div data-tour="leasing-phone" className="flex items-center gap-3 p-3 bg-card border border-border rounded-xl">
                    <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <PhoneCall className="w-4 h-4 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-xs text-muted-foreground">{t('leasing.leaseLine')}</p>
                        {vapiConfig.vapi_provisioning_status === 'active' && vapiConfig.vapi_phone_number && (
                            <p className="text-sm font-semibold text-foreground tracking-wide">{vapiConfig.vapi_phone_number}</p>
                        )}
                        {vapiConfig.vapi_provisioning_status === 'pending' && (
                            <span className="inline-flex items-center gap-2 text-xs text-amber-500 mt-0.5">
                                <Loader2 className="w-3 h-3 animate-spin" /> {t('leasing.settingUp')}
                                <button
                                    onClick={handleRetryProvisioning}
                                    disabled={retrying}
                                    className="underline hover:no-underline disabled:opacity-50"
                                >
                                    {retrying ? t('leasing.starting') : t('leasing.stuck')}
                                </button>
                            </span>
                        )}
                        {vapiConfig.vapi_provisioning_status === 'failed' && (
                            <span className="inline-flex items-center gap-2 text-xs text-red-500 mt-0.5">
                                {t('leasing.setupFailed')}
                                <button
                                    onClick={handleRetryProvisioning}
                                    disabled={retrying}
                                    className="underline hover:no-underline disabled:opacity-50"
                                >
                                    {retrying ? t('leasing.retrying') : t('leasing.retry')}
                                </button>
                            </span>
                        )}
                        {vapiConfig.vapi_provisioning_status === 'not_set_up' && (
                            <p className="text-xs text-muted-foreground mt-0.5">{t('leasing.activateHint')}</p>
                        )}
                    </div>
                </div>
            )}

            {/* Metrics */}
            {metrics && (
                <div data-tour="leasing-metrics" className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                    <MetricCard label={t('leasing.metrics.totalCalls')} value={metrics.total_calls} />
                    <MetricCard label={t('leasing.metrics.qualified')} value={metrics.qualified} />
                    <MetricCard label={t('leasing.metrics.notQualified')} value={metrics.not_qualified} />
                    <MetricCard label={t('leasing.metrics.qualRate')} value={`${metrics.qualification_rate}%`} />
                    <MetricCard label={t('leasing.metrics.avgDuration')} value={fmtDuration(metrics.avg_duration_seconds)} />
                </div>
            )}

            {/* Listings */}
            <section data-tour="leasing-listings">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-foreground">{t('leasing.listings.title')}</h2>
                    <button
                        onClick={() => { setEditListing(null); setShowAddListing(true); }}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-3 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                        <Plus className="w-4 h-4" /> {t('leasing.listings.add')}
                    </button>
                </div>

                {listings.length === 0 ? (
                    <div className="bg-card border border-border rounded-xl p-8 text-center">
                        <p className="text-muted-foreground text-sm">{t('leasing.listings.empty')}</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {listings.map(listing => (
                            <div key={listing.uuid} className="bg-card border border-border rounded-xl p-4 space-y-3">
                                <div className="flex items-start justify-between">
                                    <div>
                                        <p className="font-medium text-foreground">{listing.flat_number}</p>
                                        {listing.title && <p className="text-xs text-muted-foreground">{listing.title}</p>}
                                    </div>
                                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${listing.is_active ? 'bg-green-500/10 text-green-500' : 'bg-muted text-muted-foreground'}`}>
                                        {listing.is_active ? t('leasing.listings.active') : t('leasing.listings.inactive')}
                                    </span>
                                </div>
                                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                    <span className="flex items-center gap-1"><Banknote className="w-3.5 h-3.5" />${Number(listing.monthly_rent).toLocaleString('en-CA')}/mo</span>
                                    {listing.available_from && <span className="flex items-center gap-1"><ExternalLink className="w-3.5 h-3.5" />{t('leasing.listings.from')} {listing.available_from}</span>}
                                </div>
                                <div className="flex gap-2 pt-1">
                                    <button onClick={() => { setEditListing(listing); setShowAddListing(true); }}
                                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors">
                                        <Pencil className="w-3 h-3" /> {t('leasing.listings.edit')}
                                    </button>
                                    <button onClick={() => handleDeleteListing(listing.uuid)}
                                        className="flex items-center gap-1 text-xs text-red-500 hover:text-red-400 border border-red-500/20 rounded px-2 py-1 transition-colors">
                                        <Trash2 className="w-3 h-3" /> {t('leasing.listings.delete')}
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Leads */}
            <section data-tour="leasing-leads">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                    <h2 className="text-lg font-semibold text-foreground">{t('leasing.leads.title')}</h2>
                    <div className="flex flex-wrap items-center gap-2">
                        <select value={listingFilter} onChange={e => setListingFilter(e.target.value)}
                            className="bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-foreground">
                            <option value="">{t('leasing.leads.allListings')}</option>
                            {listings.map(l => <option key={l.uuid} value={l.uuid}>{l.flat_number}</option>)}
                        </select>
                        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                            className="bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-foreground">
                            <option value="">{t('leasing.leads.allStatuses')}</option>
                            {['qualified','not_qualified','unmatched','contacted','toured','converted','lost'].map(s => (
                                <option key={s} value={s}>{t(`leasing.leads.statuses.${s}`)}</option>
                            ))}
                        </select>
                        <button onClick={() => exportLeads({ listing_uuid: listingFilter, qualification_status: statusFilter })}
                            className="border border-border rounded-lg px-3 py-1.5 text-sm text-foreground hover:bg-secondary transition-colors">
                            {t('leasing.leads.exportCsv')}
                        </button>
                    </div>
                </div>

                {filteredLeads.length === 0 ? (
                    <div className="bg-card border border-border rounded-xl p-8 text-center">
                        <p className="text-muted-foreground text-sm">{t('leasing.leads.noLeads')}</p>
                    </div>
                ) : (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="bg-secondary border-b border-border">
                                    <tr>
                                        {[
                                            t('leasing.leads.name'),
                                            t('common.phone'),
                                            t('leasing.leads.budget'),
                                            t('leasing.leads.beds'),
                                            t('leasing.leads.listing'),
                                            t('leasing.leads.status'),
                                            t('leasing.leads.actions'),
                                        ].map(h => (
                                            <th key={h} className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                    {filteredLeads.map(lead => {
                                        const matchedListing = lead.listing_uuid
                                            ? listings.find(l => l.uuid === lead.listing_uuid)
                                            : null;
                                        return (
                                        <tr key={lead.uuid} className="hover:bg-secondary/50 transition-colors">
                                            <td className="px-4 py-3 font-medium text-foreground">{lead.caller_name}</td>
                                            <td className="px-4 py-3 text-muted-foreground">
                                                <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{lead.phone}</span>
                                            </td>
                                            <td className="px-4 py-3 text-muted-foreground">
                                                {lead.budget_max ? `$${Number(lead.budget_max).toLocaleString('en-CA')}` : '—'}
                                            </td>
                                            <td className="px-4 py-3 text-muted-foreground">
                                                <span className="flex items-center gap-1"><BedDouble className="w-3 h-3" />{lead.bedrooms ?? '—'}</span>
                                            </td>
                                            <td className="px-4 py-3 text-muted-foreground">
                                                {matchedListing
                                                    ? <span className="font-mono text-xs bg-secondary px-1.5 py-0.5 rounded">{matchedListing.flat_number}</span>
                                                    : '—'}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[lead.qualification_status] || ''}`}>
                                                    {t(`leasing.leads.statuses.${lead.qualification_status}`, { defaultValue: lead.qualification_status.replace('_', ' ') })}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-2">
                                                    <button onClick={() => setSelectedLead(lead)}
                                                        className="text-xs text-primary hover:underline">{t('common.view')}</button>
                                                    <button onClick={() => handleDeleteLead(lead.uuid)}
                                                        className="text-xs text-red-500 hover:underline">{t('common.delete')}</button>
                                                </div>
                                            </td>
                                        </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </section>

            <AddListingModal
                isOpen={showAddListing}
                onClose={() => { setShowAddListing(false); setEditListing(null); }}
                onSuccess={handleListingSuccess}
                listing={editListing}
            />

            {selectedLead && (
                <LeadDetailModal
                    lead={selectedLead}
                    listings={listings}
                    onClose={() => setSelectedLead(null)}
                    onUpdated={handleLeadUpdated}
                />
            )}
        </div>
    );
}
