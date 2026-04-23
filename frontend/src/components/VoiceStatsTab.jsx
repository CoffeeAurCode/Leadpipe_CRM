import { useState, useEffect, useCallback } from 'react';
import { PhoneCall, RefreshCw, TrendingUp, CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import { fetchCallStats } from '../services/apiService';
import { cn } from '@/lib';

const DAY_OPTIONS = [
    { label: 'Last 7 days', value: 7 },
    { label: 'Last 30 days', value: 30 },
    { label: 'Last 90 days', value: 90 },
];

function StatCard({ icon: Icon, label, value, sub, color }) {
    return (
        <div className={cn('flex flex-col gap-2 p-5 rounded-xl border bg-card', color?.border || 'border-border')}>
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</span>
                <Icon className={cn('w-4 h-4', color?.text || 'text-muted-foreground')} />
            </div>
            <span className="text-3xl font-bold tabular-nums text-foreground">{value ?? '—'}</span>
            {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
        </div>
    );
}

function BarChart({ byDate }) {
    const entries = Object.entries(byDate || {}).sort((a, b) => a[0].localeCompare(b[0]));
    if (entries.length === 0) return <p className="text-sm text-muted-foreground py-4 text-center">No call data for this period.</p>;

    const maxVal = Math.max(...entries.map(([, v]) => v), 1);
    return (
        <div className="flex items-end gap-1 h-24 w-full overflow-x-auto py-1">
            {entries.map(([date, count]) => (
                <div key={date} className="flex flex-col items-center gap-1 flex-1 min-w-[18px]" title={`${date}: ${count} call${count !== 1 ? 's' : ''}`}>
                    <div
                        className="w-full rounded-t bg-primary/60 hover:bg-primary transition-colors"
                        style={{ height: `${Math.max(4, (count / maxVal) * 80)}px` }}
                    />
                    <span className="text-[9px] text-muted-foreground rotate-45 origin-left whitespace-nowrap hidden sm:block" style={{ fontSize: '8px' }}>
                        {date.slice(5)}
                    </span>
                </div>
            ))}
        </div>
    );
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

const OUTCOME_LABEL = {
    resolved: 'Resolved',
    closed: 'Closed',
    escalated: 'Escalated',
    pending: 'Pending',
};

const OUTCOME_COLOR = {
    resolved: 'text-emerald-500',
    closed: 'text-emerald-500',
    escalated: 'text-red-500',
    pending: 'text-muted-foreground',
};

export default function VoiceStatsTab() {
    const [days, setDays] = useState(30);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetchCallStats(days);
            setData(res);
        } catch (err) {
            setError('Failed to load voice agent stats.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [days]);

    useEffect(() => { load(); }, [load]);

    const pct = (n) => data?.total ? `${Math.round((n / data.total) * 100)}%` : '—';

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-3">
                    <PhoneCall className="w-6 h-6 text-primary" />
                    <h1 className="text-2xl font-bold text-foreground">Voice Agent Stats</h1>
                </div>
                <div className="flex items-center gap-2">
                    <select
                        value={days}
                        onChange={e => setDays(Number(e.target.value))}
                        className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm text-foreground cursor-pointer focus:outline-none"
                    >
                        {DAY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    <button
                        onClick={load}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-secondary transition-colors"
                    >
                        <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
                        Refresh
                    </button>
                </div>
            </div>

            {error && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500 text-red-500 text-sm">{error}</div>
            )}

            {/* Stat Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    icon={PhoneCall}
                    label="Total Calls"
                    value={loading ? '…' : data?.total ?? 0}
                    color={{ border: 'border-border', text: 'text-primary' }}
                />
                <StatCard
                    icon={CheckCircle}
                    label="Resolved"
                    value={loading ? '…' : data?.resolved ?? 0}
                    sub={data ? pct(data.resolved) : ''}
                    color={{ border: 'border-emerald-500/20', text: 'text-emerald-500' }}
                />
                <StatCard
                    icon={AlertTriangle}
                    label="Escalated"
                    value={loading ? '…' : data?.escalated ?? 0}
                    sub={data ? pct(data.escalated) : ''}
                    color={{ border: 'border-red-500/20', text: 'text-red-500' }}
                />
                <StatCard
                    icon={TrendingUp}
                    label="Other"
                    value={loading ? '…' : data ? data.total - data.resolved - data.escalated : 0}
                    color={{ border: 'border-border', text: 'text-muted-foreground' }}
                />
            </div>

            {/* Bar Chart */}
            <div className="bg-card border border-border rounded-xl p-5 space-y-3">
                <h2 className="text-sm font-semibold text-foreground">Call Volume</h2>
                {loading ? (
                    <div className="h-24 flex items-center justify-center text-muted-foreground text-sm">Loading…</div>
                ) : (
                    <BarChart byDate={data?.by_date} />
                )}
            </div>

            {/* Recent Calls */}
            <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="px-5 py-4 border-b border-border">
                    <h2 className="text-sm font-semibold text-foreground">Recent Calls</h2>
                </div>
                {loading ? (
                    <p className="px-5 py-8 text-center text-muted-foreground text-sm">Loading…</p>
                ) : !data?.recent?.length ? (
                    <p className="px-5 py-8 text-center text-muted-foreground text-sm">No recent calls found.</p>
                ) : (
                    <ul>
                        {data.recent.map((log, i) => (
                            <li key={log.id ?? i} className="border-b border-border last:border-0">
                                <button
                                    className="w-full px-5 py-3 flex items-center justify-between gap-3 hover:bg-secondary/40 transition-colors text-left"
                                    onClick={() => setExpanded(expanded === i ? null : i)}
                                >
                                    <div className="flex items-center gap-3 min-w-0">
                                        <PhoneCall className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                                        <div className="min-w-0">
                                            <p className="text-sm font-medium text-foreground truncate">
                                                {log.phone_number || 'Unknown'}
                                            </p>
                                            <p className={cn('text-xs', OUTCOME_COLOR[log.complaint_status] || 'text-muted-foreground')}>
                                                {OUTCOME_LABEL[log.complaint_status] || log.raw_event_type || 'No outcome'}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {timeAgo(log.created_at)}
                                        </span>
                                    </div>
                                </button>
                                {expanded === i && log.transcript && (
                                    <div className="px-5 pb-4">
                                        <p className="text-xs text-muted-foreground bg-secondary/50 rounded-lg p-3 whitespace-pre-wrap max-h-40 overflow-y-auto">
                                            {log.transcript}
                                        </p>
                                    </div>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
