import { useState, useEffect, useCallback } from 'react';
import { Plus, Pencil, Trash2, ExternalLink, Phone, BedDouble, Banknote } from 'lucide-react';
import {
    getListings, deleteListing,
    getLeaseLeads, deleteLead,
    getLeasingMetrics, exportLeads,
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
    const [listings, setListings] = useState([]);
    const [leads, setLeads] = useState([]);
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);

    const [listingFilter, setListingFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');

    const [showAddListing, setShowAddListing] = useState(false);
    const [editListing, setEditListing] = useState(null);
    const [selectedLead, setSelectedLead] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [l, ld, m] = await Promise.all([
                getListings(),
                getLeaseLeads(),
                getLeasingMetrics(),
            ]);
            setListings(l);
            setLeads(ld);
            setMetrics(m);
        } catch (e) {
            console.error('Leasing load error', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    async function handleDeleteListing(uuid) {
        if (!confirm('Delete this listing?')) return;
        await deleteListing(uuid);
        setListings(prev => prev.filter(l => l.uuid !== uuid));
    }

    async function handleDeleteLead(uuid) {
        if (!confirm('Delete this lead?')) return;
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
                <p className="text-muted-foreground text-sm">Loading leasing data…</p>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-foreground">Leasing</h1>
                <p className="text-muted-foreground text-sm mt-1">Manage listings and track voice leads from the lease agent.</p>
            </div>

            {/* Metrics */}
            {metrics && (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                    <MetricCard label="Total Calls" value={metrics.total_calls} />
                    <MetricCard label="Qualified" value={metrics.qualified} />
                    <MetricCard label="Not Qualified" value={metrics.not_qualified} />
                    <MetricCard label="Qual Rate" value={`${metrics.qualification_rate}%`} />
                    <MetricCard label="Avg Duration" value={fmtDuration(metrics.avg_duration_seconds)} />
                </div>
            )}

            {/* Listings */}
            <section>
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-foreground">Available Listings</h2>
                    <button
                        onClick={() => { setEditListing(null); setShowAddListing(true); }}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-3 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                        <Plus className="w-4 h-4" /> Add Listing
                    </button>
                </div>

                {listings.length === 0 ? (
                    <div className="bg-card border border-border rounded-xl p-8 text-center">
                        <p className="text-muted-foreground text-sm">No listings yet. Add one to make it available to the lease voice agent.</p>
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
                                        {listing.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </div>
                                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                    <span className="flex items-center gap-1"><Banknote className="w-3.5 h-3.5" />₹{Number(listing.monthly_rent).toLocaleString()}/mo</span>
                                    {listing.available_from && <span className="flex items-center gap-1"><ExternalLink className="w-3.5 h-3.5" />From {listing.available_from}</span>}
                                </div>
                                <div className="flex gap-2 pt-1">
                                    <button onClick={() => { setEditListing(listing); setShowAddListing(true); }}
                                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors">
                                        <Pencil className="w-3 h-3" /> Edit
                                    </button>
                                    <button onClick={() => handleDeleteListing(listing.uuid)}
                                        className="flex items-center gap-1 text-xs text-red-500 hover:text-red-400 border border-red-500/20 rounded px-2 py-1 transition-colors">
                                        <Trash2 className="w-3 h-3" /> Delete
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Leads */}
            <section>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                    <h2 className="text-lg font-semibold text-foreground">Leads</h2>
                    <div className="flex flex-wrap items-center gap-2">
                        <select value={listingFilter} onChange={e => setListingFilter(e.target.value)}
                            className="bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-foreground">
                            <option value="">All Listings</option>
                            {listings.map(l => <option key={l.uuid} value={l.uuid}>{l.flat_number}</option>)}
                        </select>
                        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                            className="bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-foreground">
                            <option value="">All Status</option>
                            {['qualified','not_qualified','unmatched','contacted','toured','converted','lost'].map(s => (
                                <option key={s} value={s}>{s.replace('_', ' ')}</option>
                            ))}
                        </select>
                        <button onClick={() => exportLeads({ listing_uuid: listingFilter, qualification_status: statusFilter })}
                            className="border border-border rounded-lg px-3 py-1.5 text-sm text-foreground hover:bg-secondary transition-colors">
                            Export CSV
                        </button>
                    </div>
                </div>

                {filteredLeads.length === 0 ? (
                    <div className="bg-card border border-border rounded-xl p-8 text-center">
                        <p className="text-muted-foreground text-sm">No leads yet. Once a caller dials the lease number and the voice agent captures their info, it will appear here.</p>
                    </div>
                ) : (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="bg-secondary border-b border-border">
                                    <tr>
                                        {['Name', 'Phone', 'Budget', 'Beds', 'Move-in', 'Status', 'Actions'].map(h => (
                                            <th key={h} className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                    {filteredLeads.map(lead => (
                                        <tr key={lead.uuid} className="hover:bg-secondary/50 transition-colors">
                                            <td className="px-4 py-3 font-medium text-foreground">{lead.caller_name}</td>
                                            <td className="px-4 py-3 text-muted-foreground">
                                                <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{lead.phone}</span>
                                            </td>
                                            <td className="px-4 py-3 text-muted-foreground">
                                                {lead.budget_max ? `₹${Number(lead.budget_max).toLocaleString()}` : '—'}
                                            </td>
                                            <td className="px-4 py-3 text-muted-foreground">
                                                <span className="flex items-center gap-1"><BedDouble className="w-3 h-3" />{lead.bedrooms ?? '—'}</span>
                                            </td>
                                            <td className="px-4 py-3 text-muted-foreground">{lead.move_in_timeline || '—'}</td>
                                            <td className="px-4 py-3">
                                                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[lead.qualification_status] || ''}`}>
                                                    {lead.qualification_status.replace('_', ' ')}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-2">
                                                    <button onClick={() => setSelectedLead(lead)}
                                                        className="text-xs text-primary hover:underline">View</button>
                                                    <button onClick={() => handleDeleteLead(lead.uuid)}
                                                        className="text-xs text-red-500 hover:underline">Delete</button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
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
                    onClose={() => setSelectedLead(null)}
                    onUpdated={handleLeadUpdated}
                />
            )}
        </div>
    );
}
