import { useState, useEffect } from 'react';
import { MessageSquareMore, RefreshCw, Send } from 'lucide-react';
import { fetchTenants, sendWorkflowSms } from '../services/apiService';
import { cn } from '@/lib';

export default function SmsWorkflow() {
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [selectedUuids, setSelectedUuids] = useState(new Set());
    const [message, setMessage] = useState('');
    const [sending, setSending] = useState(false);
    const [banner, setBanner] = useState(null); // { type: 'success'|'error', text: string }
    const [rentStatusFilter, setRentStatusFilter] = useState('');

    const RENT_STATUS_OPTIONS = ['On-time', 'Upcoming', 'Overdue', 'At Risk'];

    async function load(filter = rentStatusFilter) {
        try {
            setLoading(true);
            setLoadError(null);
            const data = await fetchTenants(filter ? { rent_status: filter } : {});
            setTenants(data);
            setSelectedUuids(new Set());
        } catch (err) {
            setLoadError('Failed to load tenants. Check that the backend is running.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { load(rentStatusFilter); }, [rentStatusFilter]);

    function toggleOne(uuid) {
        setSelectedUuids(prev => {
            const next = new Set(prev);
            next.has(uuid) ? next.delete(uuid) : next.add(uuid);
            return next;
        });
    }

    function toggleAll() {
        if (selectedUuids.size === tenants.length) {
            setSelectedUuids(new Set());
        } else {
            setSelectedUuids(new Set(tenants.map(t => t.uuid)));
        }
    }

    async function handleSend() {
        if (selectedUuids.size === 0 || !message.trim()) return;
        setBanner(null);
        setSending(true);
        try {
            const data = await sendWorkflowSms([...selectedUuids], message.trim());
            const failed = data.results.filter(r => !r.success).length;
            const succeeded = data.results.filter(r => r.success).length;
            if (failed === 0) {
                setBanner({ type: 'success', text: `SMS sent successfully to ${succeeded} tenant(s).` });
            } else {
                setBanner({ type: 'error', text: `Failed to send SMS to ${failed} tenant(s).` });
            }
        } catch (err) {
            setBanner({ type: 'error', text: 'Request failed. Check that the backend is running.' });
            console.error(err);
        } finally {
            setSending(false);
        }
    }

    const allSelected = tenants.length > 0 && selectedUuids.size === tenants.length;
    const canSend = selectedUuids.size > 0 && message.trim().length > 0 && !sending;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3">
                <MessageSquareMore className="w-6 h-6 text-primary" />
                <h1 className="text-2xl font-bold text-foreground">SMS Workflow</h1>
            </div>

            {/* Banner */}
            {banner && (
                <div className={cn(
                    'px-4 py-3 rounded-lg border text-sm font-medium',
                    banner.type === 'success'
                        ? 'bg-emerald-500/10 border-emerald-500 text-emerald-500'
                        : 'bg-red-500/10 border-red-500 text-red-500'
                )}>
                    {banner.text}
                </div>
            )}

            {/* Message Composer */}
            <div className="bg-card border border-border rounded-xl p-5 space-y-4">
                <label className="block text-sm font-medium text-foreground">Message</label>
                <textarea
                    value={message}
                    onChange={e => setMessage(e.target.value)}
                    placeholder="Type your SMS message here…"
                    rows={4}
                    className="w-full bg-background border border-border rounded-lg px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <p className="text-xs text-muted-foreground">
                    Tip: Use <code className="px-1 py-0.5 rounded bg-secondary text-foreground">{'{'+'name}'}</code> and <code className="px-1 py-0.5 rounded bg-secondary text-foreground">{'{'+'unit}'}</code> to personalise your message — e.g. <span className="italic">"Hi {'{'+'name}'}, rent for flat {'{'+'unit}'} is due."</span>
                </p>
                <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                        {message.length} character{message.length !== 1 ? 's' : ''}
                    </span>
                    <button
                        onClick={handleSend}
                        disabled={!canSend}
                        className={cn(
                            'flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all',
                            canSend
                                ? 'bg-primary text-primary-foreground hover:opacity-90'
                                : 'bg-secondary text-muted-foreground cursor-not-allowed'
                        )}
                    >
                        <Send className="w-4 h-4" />
                        {sending ? 'Sending…' : `Send SMS${selectedUuids.size > 0 ? ` (${selectedUuids.size})` : ''}`}
                    </button>
                </div>
            </div>

            {/* Tenant Table */}
            <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-5 py-4 border-b border-border gap-3">
                    <span className="text-sm font-medium text-foreground">
                        {selectedUuids.size > 0
                            ? `${selectedUuids.size} tenant(s) selected`
                            : 'Select tenants to message'}
                    </span>
                    <div className="flex items-center gap-2">
                        <select
                            value={rentStatusFilter}
                            onChange={e => setRentStatusFilter(e.target.value)}
                            className="text-sm bg-secondary border border-border rounded-lg px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        >
                            <option value="">All Rent Statuses</option>
                            {RENT_STATUS_OPTIONS.map(s => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                        <button
                            onClick={() => load(rentStatusFilter)}
                            className="text-muted-foreground hover:text-foreground transition-colors"
                            title="Refresh"
                        >
                            <RefreshCw className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {loadError && (
                    <div className="px-5 py-4 text-sm text-red-500">{loadError}</div>
                )}

                {loading ? (
                    <div className="px-5 py-8 text-center text-muted-foreground text-sm">Loading tenants…</div>
                ) : (
                    <table className="w-full text-sm">
                        <thead className="bg-secondary/50">
                            <tr>
                                <th className="px-5 py-3 text-left w-10">
                                    <input
                                        type="checkbox"
                                        checked={allSelected}
                                        onChange={toggleAll}
                                        className="cursor-pointer accent-primary"
                                    />
                                </th>
                                <th className="px-5 py-3 text-left text-muted-foreground font-medium">#</th>
                                <th className="px-5 py-3 text-left text-muted-foreground font-medium">Name</th>
                                <th className="px-5 py-3 text-left text-muted-foreground font-medium">Phone</th>
                                <th className="px-5 py-3 text-left text-muted-foreground font-medium">Flat</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {tenants.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="px-5 py-8 text-center text-muted-foreground">
                                        No tenants found.
                                    </td>
                                </tr>
                            )}
                            {tenants.map(tenant => (
                                <tr
                                    key={tenant.uuid}
                                    className={cn(
                                        'cursor-pointer transition-colors',
                                        selectedUuids.has(tenant.uuid)
                                            ? 'bg-primary/5'
                                            : 'hover:bg-secondary/40'
                                    )}
                                    onClick={() => toggleOne(tenant.uuid)}
                                >
                                    <td className="px-5 py-3" onClick={e => e.stopPropagation()}>
                                        <input
                                            type="checkbox"
                                            checked={selectedUuids.has(tenant.uuid)}
                                            onChange={() => toggleOne(tenant.uuid)}
                                            className="cursor-pointer accent-primary"
                                        />
                                    </td>
                                    <td className="px-5 py-3 text-muted-foreground">{tenant.id}</td>
                                    <td className="px-5 py-3 text-foreground font-medium">{tenant.name}</td>
                                    <td className="px-5 py-3 text-muted-foreground">{tenant.phone || '—'}</td>
                                    <td className="px-5 py-3 text-muted-foreground">{tenant.flat_number || '—'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
