import { useState, useEffect, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
    MessageSquareMore, RefreshCw, Send, ChevronUp, ChevronDown,
    ChevronsUpDown, Search, LayoutTemplate, X, Plus, Pencil, Trash2, Check,
} from 'lucide-react';
import { fetchTenants, sendWorkflowSms } from '../services/apiService';
import { cn } from '@/lib';

// ── localStorage template helpers ────────────────────────────────────────────

const STORAGE_KEY = 'sms_templates';

const DEFAULT_TEMPLATES = [
    {
        id: 'default-1',
        name: 'Rent Reminder',
        body: 'Hi {name}, this is a reminder that your rent of {rent} for flat {unit} is due on {date}. Please ensure timely payment.',
    },
    {
        id: 'default-2',
        name: 'Complaint Update',
        body: 'Hi {name}, we wanted to let you know that your complaint for flat {unit} has been updated. Please contact us if you have any questions.',
    },
    {
        id: 'default-3',
        name: 'Appointment Reminder',
        body: 'Hi {name}, you have an upcoming appointment for flat {unit} on {date}. Please be available during the scheduled time.',
    },
];

function loadTemplates() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : DEFAULT_TEMPLATES;
    } catch {
        return DEFAULT_TEMPLATES;
    }
}

function saveTemplates(templates) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(templates));
}

// ── Variable chips config ─────────────────────────────────────────────────────

const VARIABLES = [
    { token: '{name}',  sample: 'John' },
    { token: '{unit}',  sample: 'A101' },
    { token: '{rent}',  sample: '$1,200' },
    { token: '{date}',  sample: 'April 5' },
];

function buildPreview(message) {
    let out = message;
    VARIABLES.forEach(({ token, sample }) => {
        out = out.replaceAll(token, `**${sample}**`);
    });
    // Convert **bold** to <strong> for display
    out = out.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    return out;
}

// ── Sort helpers ──────────────────────────────────────────────────────────────

const RENT_STATUS_ORDER = { 'On-time': 0, Upcoming: 1, 'At Risk': 2, Overdue: 3 };

const RENT_STATUS_KEY_MAP = {
    'On-time': 'onTime',
    'Upcoming': 'upcoming',
    'Overdue': 'overdue',
    'At Risk': 'atRisk',
};

function sortTenants(tenants, field, dir) {
    if (!field) return tenants;
    return [...tenants].sort((a, b) => {
        let av, bv;
        if (field === 'name') {
            av = (a.name || '').toLowerCase();
            bv = (b.name || '').toLowerCase();
        } else if (field === 'flat') {
            av = (a.flat_number || '').toLowerCase();
            bv = (b.flat_number || '').toLowerCase();
        } else if (field === 'rent_status') {
            av = RENT_STATUS_ORDER[a.rent_status] ?? 99;
            bv = RENT_STATUS_ORDER[b.rent_status] ?? 99;
        }
        if (av < bv) return dir === 'asc' ? -1 : 1;
        if (av > bv) return dir === 'asc' ? 1 : -1;
        return 0;
    });
}

// ── Rent status badge ─────────────────────────────────────────────────────────

const STATUS_STYLES = {
    'On-time':   'bg-emerald-500/10 text-emerald-500',
    'Upcoming':  'bg-blue-500/10 text-blue-500',
    'At Risk':   'bg-amber-500/10 text-amber-500',
    'Overdue':   'bg-red-500/10 text-red-500',
};

function RentStatusBadge({ status }) {
    const { t } = useTranslation();
    if (!status) return <span className="text-muted-foreground">—</span>;
    const key = RENT_STATUS_KEY_MAP[status];
    const label = key ? t(`tenants.rentStatusOptions.${key}`) : status;
    return (
        <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', STATUS_STYLES[status] ?? 'bg-secondary text-foreground')}>
            {label}
        </span>
    );
}

// ── Sort icon ─────────────────────────────────────────────────────────────────

function SortIcon({ field, sortField, sortDir }) {
    if (sortField !== field) return <ChevronsUpDown className="w-3 h-3 opacity-40" />;
    return sortDir === 'asc'
        ? <ChevronUp className="w-3 h-3" />
        : <ChevronDown className="w-3 h-3" />;
}

// ── Templates Modal ───────────────────────────────────────────────────────────

function TemplatesModal({ templates, onClose, onSave }) {
    const { t } = useTranslation();
    const [list, setList] = useState(templates);
    const [editing, setEditing] = useState(null); // { id, name, body } | null
    const [isNew, setIsNew] = useState(false);

    function startNew() {
        setEditing({ id: `t-${Date.now()}`, name: '', body: '' });
        setIsNew(true);
    }

    function startEdit(tpl) {
        setEditing({ ...tpl });
        setIsNew(false);
    }

    function cancelEdit() {
        setEditing(null);
        setIsNew(false);
    }

    function commitEdit() {
        if (!editing.name.trim() || !editing.body.trim()) return;
        const updated = isNew
            ? [...list, editing]
            : list.map(t => t.id === editing.id ? editing : t);
        setList(updated);
        setEditing(null);
        setIsNew(false);
    }

    function deleteTemplate(id) {
        setList(prev => prev.filter(t => t.id !== id));
    }

    function handleSave() {
        onSave(list);
        onClose();
    }

    return (
        <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
            onClick={onClose}
        >
            <div
                className="bg-card border border-border rounded-xl w-full max-w-lg max-h-[85vh] flex flex-col shadow-2xl"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
                    <h2 className="text-lg font-semibold text-foreground">{t('sms.manageTemplates')}</h2>
                    <button onClick={onClose} className="p-2 rounded-lg hover:bg-secondary transition-colors">
                        <X className="w-4 h-4 text-muted-foreground" />
                    </button>
                </div>

                {/* List */}
                <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
                    {list.map(tpl => (
                        <div key={tpl.id} className="p-3 rounded-lg border border-border bg-secondary/40 space-y-1">
                            {editing && editing.id === tpl.id ? (
                                <div className="space-y-2">
                                    <input
                                        autoFocus
                                        value={editing.name}
                                        onChange={e => setEditing(prev => ({ ...prev, name: e.target.value }))}
                                        placeholder={t('sms.templateName')}
                                        className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                                    />
                                    <textarea
                                        value={editing.body}
                                        onChange={e => setEditing(prev => ({ ...prev, body: e.target.value }))}
                                        placeholder={t('sms.messageBody')}
                                        rows={3}
                                        className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                                    />
                                    <div className="flex gap-2">
                                        <button
                                            onClick={commitEdit}
                                            disabled={!editing.name.trim() || !editing.body.trim()}
                                            className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground disabled:opacity-50"
                                        >
                                            <Check className="w-3 h-3" /> {t('common.save')}
                                        </button>
                                        <button
                                            onClick={cancelEdit}
                                            className="px-3 py-1.5 rounded-md text-xs font-medium bg-secondary text-foreground"
                                        >
                                            {t('common.cancel')}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex items-start justify-between gap-2">
                                    <div className="min-w-0">
                                        <p className="text-sm font-medium text-foreground">{tpl.name}</p>
                                        <p className="text-xs text-muted-foreground truncate mt-0.5">{tpl.body}</p>
                                    </div>
                                    <div className="flex gap-1 shrink-0">
                                        <button onClick={() => startEdit(tpl)} className="p-1.5 rounded hover:bg-secondary transition-colors">
                                            <Pencil className="w-3.5 h-3.5 text-muted-foreground" />
                                        </button>
                                        <button onClick={() => deleteTemplate(tpl.id)} className="p-1.5 rounded hover:bg-secondary transition-colors">
                                            <Trash2 className="w-3.5 h-3.5 text-red-500" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}

                    {/* New template inline form */}
                    {isNew && (
                        <div className="p-3 rounded-lg border border-primary/50 bg-primary/5 space-y-2">
                            <input
                                autoFocus
                                value={editing?.name ?? ''}
                                onChange={e => setEditing(prev => ({ ...prev, name: e.target.value }))}
                                placeholder="Template name"
                                className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                            <textarea
                                value={editing?.body ?? ''}
                                onChange={e => setEditing(prev => ({ ...prev, body: e.target.value }))}
                                placeholder="Message body…"
                                rows={3}
                                className="w-full bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                            <div className="flex gap-2">
                                <button
                                    onClick={commitEdit}
                                    disabled={!editing?.name.trim() || !editing?.body.trim()}
                                    className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground disabled:opacity-50"
                                >
                                    <Check className="w-3 h-3" /> Save
                                </button>
                                <button onClick={cancelEdit} className="px-3 py-1.5 rounded-md text-xs font-medium bg-secondary text-foreground">
                                    Cancel
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between px-6 py-3 border-t border-border shrink-0">
                    <button
                        onClick={startNew}
                        disabled={isNew || (editing !== null)}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-primary hover:bg-primary/10 transition-colors disabled:opacity-40"
                    >
                        <Plus className="w-4 h-4" /> {t('sms.newTemplate')}
                    </button>
                    <button
                        onClick={handleSave}
                        className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
                    >
                        {t('sms.saveChanges')}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Main component ────────────────────────────────────────────────────────────

const RENT_STATUS_OPTIONS = ['On-time', 'Upcoming', 'Overdue', 'At Risk'];

export default function SmsWorkflow() {
    const { t } = useTranslation();
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [selectedUuids, setSelectedUuids] = useState(new Set());
    const [message, setMessage] = useState('');
    const [sending, setSending] = useState(false);
    const [banner, setBanner] = useState(null);
    const [rentStatusFilter, setRentStatusFilter] = useState('');

    // Templates
    const [templates, setTemplates] = useState(loadTemplates);
    const [showTemplatesModal, setShowTemplatesModal] = useState(false);
    const [selectedTemplateId, setSelectedTemplateId] = useState('');

    // Table controls
    const [searchQuery, setSearchQuery] = useState('');
    const [sortField, setSortField] = useState(null);
    const [sortDir, setSortDir] = useState('asc');

    // Textarea ref for cursor-position variable insertion
    const textareaRef = useRef(null);

    async function load(filter = rentStatusFilter) {
        try {
            setLoading(true);
            setLoadError(null);
            const data = await fetchTenants(filter ? { rent_status: filter } : {});
            setTenants(data);
            setSelectedUuids(new Set());
        } catch (err) {
            setLoadError(t('sms.failedLoad'));
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
        if (selectedUuids.size === displayTenants.length) {
            setSelectedUuids(new Set());
        } else {
            setSelectedUuids(new Set(displayTenants.map(t => t.uuid)));
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
                setBanner({ type: 'success', text: t('sms.smsSentSuccess', { count: succeeded }) });
            } else {
                setBanner({ type: 'error', text: t('sms.smsSentFailed', { count: failed }) });
            }
        } catch (err) {
            setBanner({ type: 'error', text: t('sms.requestFailed') });
            console.error(err);
        } finally {
            setSending(false);
        }
    }

    function insertVariable(token) {
        const el = textareaRef.current;
        if (!el) {
            setMessage(prev => prev + token);
            return;
        }
        const start = el.selectionStart ?? message.length;
        const end = el.selectionEnd ?? message.length;
        const updated = message.slice(0, start) + token + message.slice(end);
        setMessage(updated);
        // Restore cursor after the inserted token
        requestAnimationFrame(() => {
            el.focus();
            el.setSelectionRange(start + token.length, start + token.length);
        });
    }

    function handleSortToggle(field) {
        if (sortField === field) {
            setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDir('asc');
        }
    }

    function handleTemplatesChange(updated) {
        setTemplates(updated);
        saveTemplates(updated);
    }

    // Derived tenant list: search filter → sort
    const displayTenants = useMemo(() => {
        const q = searchQuery.trim().toLowerCase();
        const filtered = q
            ? tenants.filter(t =>
                (t.name || '').toLowerCase().includes(q) ||
                (t.flat_number || '').toLowerCase().includes(q)
              )
            : tenants;
        return sortTenants(filtered, sortField, sortDir);
    }, [tenants, searchQuery, sortField, sortDir]);

    const allSelected = displayTenants.length > 0 && displayTenants.every(t => selectedUuids.has(t.uuid));
    const canSend = selectedUuids.size > 0 && message.trim().length > 0 && !sending;

    return (
        <div className="space-y-6">
            {/* ── Header ── */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <MessageSquareMore className="w-6 h-6 text-primary" />
                    <h1 className="text-2xl font-bold text-foreground">{t('sms.title')}</h1>
                </div>
                <button
                    onClick={() => setShowTemplatesModal(true)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card text-sm font-medium text-foreground hover:border-primary hover:text-primary transition-all duration-200 shadow-sm"
                >
                    <LayoutTemplate className="w-4 h-4" />
                    {t('sms.manageTemplates')}
                </button>
            </div>

            {/* ── Banner ── */}
            {banner && (
                <div className={cn(
                    'px-4 py-3 rounded-lg border text-sm font-medium flex items-center justify-between',
                    banner.type === 'success'
                        ? 'bg-emerald-500/10 border-emerald-500 text-emerald-500'
                        : 'bg-red-500/10 border-red-500 text-red-500'
                )}>
                    {banner.text}
                    <button onClick={() => setBanner(null)} className="ml-4 opacity-60 hover:opacity-100">
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {/* ── Composer + Preview ── */}
            <div data-tour="sms-composer" className="grid grid-cols-1 lg:grid-cols-2 gap-4">

                {/* Composer */}
                <div className="bg-card border border-border rounded-xl p-5 space-y-4 shadow-sm hover:shadow-md transition-shadow duration-300">
                    {/* Template selector */}
                    <div className="space-y-1.5">
                        <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            {t('sms.loadTemplate')}
                        </label>
                        <select
                            value={selectedTemplateId}
                            onChange={e => {
                                const id = e.target.value;
                                const tpl = templates.find(tmpl => tmpl.id === id);
                                if (tpl) setMessage(tpl.body);
                                setSelectedTemplateId('');
                            }}
                            className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                            <option value="" disabled>{t('sms.selectTemplate')}</option>
                            {templates.map(t => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Variable chips */}
                    <div className="space-y-1.5">
                        <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            {t('sms.insertVariable')}
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {VARIABLES.map(({ token }) => (
                                <button
                                    key={token}
                                    onClick={() => insertVariable(token)}
                                    className="px-2.5 py-1 rounded-md bg-primary/10 text-primary border border-primary/20 text-xs font-mono font-medium hover:bg-primary/20 hover:border-primary/40 transition-all duration-150"
                                >
                                    {token}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Textarea */}
                    <div className="space-y-1.5">
                        <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            {t('sms.message')}
                        </label>
                        <textarea
                            ref={textareaRef}
                            value={message}
                            onChange={e => setMessage(e.target.value)}
                            placeholder={t('sms.typePlaceholder')}
                            rows={5}
                            className="w-full bg-background border border-border rounded-lg px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary transition-shadow"
                        />
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-muted-foreground">
                                {t('sms.charCount', { count: message.length })}
                            </span>
                            <button
                                onClick={handleSend}
                                disabled={!canSend}
                                className={cn(
                                    'flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                                    canSend
                                        ? 'bg-primary text-primary-foreground hover:opacity-90 shadow-sm hover:shadow-md'
                                        : 'bg-secondary text-muted-foreground cursor-not-allowed'
                                )}
                            >
                                <Send className="w-4 h-4" />
                                {sending ? t('sms.sending') : selectedUuids.size > 0 ? t('sms.sendSmsCount', { count: selectedUuids.size }) : t('sms.sendSmsBtn')}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Live Preview */}
                <div className="bg-card border border-border rounded-xl p-5 shadow-sm flex flex-col">
                    <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
                        {t('sms.livePreview')}
                    </label>
                    <div className="flex-1 flex flex-col items-center justify-center">
                        {/* Phone mockup */}
                        <div className="w-full max-w-xs mx-auto border-2 border-border rounded-3xl p-3 bg-secondary/30">
                            <div className="flex justify-center mb-2">
                                <div className="w-16 h-1.5 bg-border rounded-full" />
                            </div>
                            <div className="bg-background rounded-2xl p-3 min-h-[120px] flex flex-col justify-end gap-2">
                                <div className="self-start max-w-[85%] bg-secondary rounded-2xl rounded-tl-sm px-3 py-2 text-sm text-foreground leading-relaxed">
                                    {message.trim() ? (
                                        <span
                                            dangerouslySetInnerHTML={{ __html: buildPreview(message) }}
                                        />
                                    ) : (
                                        <span className="text-muted-foreground italic text-xs">
                                            {t('sms.previewPlaceholder')}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <p className="text-center text-xs text-muted-foreground mt-2 opacity-60">
                                {t('sms.sampleValues')}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Tenant Table ── */}
            <div className="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
                {/* Table toolbar */}
                <div data-tour="sms-recipients" className="flex flex-col sm:flex-row sm:items-center justify-between px-5 py-4 border-b border-border gap-3">
                    <span className="text-sm font-medium text-foreground shrink-0">
                        {selectedUuids.size > 0
                            ? t('sms.selectedTenants', { count: selectedUuids.size })
                            : t('sms.selectTenants')}
                    </span>
                    <div className="flex items-center gap-2 flex-wrap">
                        {/* Search */}
                        <div className="relative">
                            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                placeholder={t('sms.searchPlaceholder')}
                                className="pl-8 pr-3 py-1.5 text-sm bg-secondary border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary w-44"
                            />
                        </div>
                        {/* Rent status filter */}
                        <select
                            value={rentStatusFilter}
                            onChange={e => setRentStatusFilter(e.target.value)}
                            className="text-sm bg-secondary border border-border rounded-lg px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        >
                            <option value="">{t('sms.allStatuses')}</option>
                            {RENT_STATUS_OPTIONS.map(s => {
                                const k = RENT_STATUS_KEY_MAP[s];
                                return <option key={s} value={s}>{k ? t(`tenants.rentStatusOptions.${k}`) : s}</option>;
                            })}
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
                    <div className="px-5 py-8 text-center text-muted-foreground text-sm">{t('tenants.loading')}</div>
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
                                {/* Sortable column headers */}
                                {[
                                    { key: 'name', label: t('sms.name') },
                                    { key: 'flat', label: t('sms.flat') },
                                ].map(col => (
                                    <th
                                        key={col.key}
                                        className="px-5 py-3 text-left text-muted-foreground font-medium cursor-pointer select-none hover:text-foreground transition-colors"
                                        onClick={() => handleSortToggle(col.key)}
                                    >
                                        <span className="flex items-center gap-1">
                                            {col.label}
                                            <SortIcon field={col.key} sortField={sortField} sortDir={sortDir} />
                                        </span>
                                    </th>
                                ))}
                                <th className="px-5 py-3 text-left text-muted-foreground font-medium">{t('sms.phone')}</th>
                                <th
                                    className="px-5 py-3 text-left text-muted-foreground font-medium cursor-pointer select-none hover:text-foreground transition-colors"
                                    onClick={() => handleSortToggle('rent_status')}
                                >
                                    <span className="flex items-center gap-1">
                                        {t('sms.rentStatus')}
                                        <SortIcon field="rent_status" sortField={sortField} sortDir={sortDir} />
                                    </span>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {displayTenants.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="px-5 py-8 text-center text-muted-foreground">
                                        {searchQuery ? t('sms.noMatch') : t('sms.noTenants')}
                                    </td>
                                </tr>
                            )}
                            {displayTenants.map(tenant => {
                                const selected = selectedUuids.has(tenant.uuid);
                                return (
                                    <tr
                                        key={tenant.uuid}
                                        className={cn(
                                            'cursor-pointer transition-colors duration-150',
                                            selected
                                                ? 'bg-primary/10 hover:bg-primary/15'
                                                : 'hover:bg-secondary/40'
                                        )}
                                        onClick={() => toggleOne(tenant.uuid)}
                                    >
                                        <td className="px-5 py-3" onClick={e => e.stopPropagation()}>
                                            <div className={cn(
                                                'w-4 h-4 rounded border flex items-center justify-center transition-colors',
                                                selected
                                                    ? 'bg-primary border-primary'
                                                    : 'border-border bg-background'
                                            )}>
                                                {selected && <Check className="w-2.5 h-2.5 text-primary-foreground" />}
                                            </div>
                                        </td>
                                        <td className="px-5 py-3 text-foreground font-medium">{tenant.name}</td>
                                        <td className="px-5 py-3 text-muted-foreground">{tenant.flat_number || '—'}</td>
                                        <td className="px-5 py-3 text-muted-foreground">{tenant.phone || '—'}</td>
                                        <td className="px-5 py-3">
                                            <RentStatusBadge status={tenant.rent_status} />
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* ── Templates modal ── */}
            {showTemplatesModal && (
                <TemplatesModal
                    templates={templates}
                    onClose={() => setShowTemplatesModal(false)}
                    onSave={handleTemplatesChange}
                />
            )}
        </div>
    );
}
