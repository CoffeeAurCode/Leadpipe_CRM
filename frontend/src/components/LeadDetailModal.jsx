import { useState } from 'react';
import { X, Phone, Mail, BedDouble, Calendar, Banknote, MessageSquare } from 'lucide-react';
import { updateLead } from '../services/apiService';

const STATUS_COLORS = {
    qualified: 'bg-green-500/10 text-green-500 border-green-500/20',
    not_qualified: 'bg-red-500/10 text-red-500 border-red-500/20',
    unmatched: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
    contacted: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    toured: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
    converted: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    lost: 'bg-muted text-muted-foreground border-border',
};

const MANAGER_STATUSES = ['contacted', 'toured', 'converted', 'lost'];

export default function LeadDetailModal({ lead, listings = [], onClose, onUpdated }) {
    function findListing(uuid) {
        return listings.find(l => l.uuid === uuid || String(l.uuid) === String(uuid));
    }
    const [notes, setNotes] = useState(lead?.manager_notes || '');
    const [status, setStatus] = useState(lead?.qualification_status || '');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    if (!lead) return null;

    const isVoiceSet = ['qualified', 'not_qualified', 'unmatched'].includes(lead.qualification_status);
    const qualifyingAnswers = lead.qualifying_answers || {};
    const hasAnswers = Object.keys(qualifyingAnswers).length > 0;

    async function handleSave() {
        setSaving(true);
        setError('');
        try {
            const payload = {};
            if (notes !== (lead.manager_notes || '')) payload.manager_notes = notes;
            if (status !== lead.qualification_status) payload.qualification_status = status;
            if (Object.keys(payload).length === 0) { onClose(); return; }
            const updated = await updateLead(lead.uuid, payload);
            onUpdated(updated);
        } catch (err) {
            setError(err.message || 'Failed to save.');
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-card border border-border rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between p-5 border-b border-border">
                    <div>
                        <h2 className="text-lg font-semibold text-foreground">{lead.caller_name}</h2>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border mt-1 ${STATUS_COLORS[lead.qualification_status] || ''}`}>
                            {lead.qualification_status.replace('_', ' ')}
                        </span>
                    </div>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-5 space-y-5">
                    {/* Contact */}
                    <section>
                        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Contact</h3>
                        <div className="space-y-2">
                            <div className="flex items-center gap-2 text-sm text-foreground">
                                <Phone className="w-4 h-4 text-muted-foreground" />
                                {lead.phone || '—'}
                            </div>
                            {lead.email && (
                                <div className="flex items-center gap-2 text-sm text-foreground">
                                    <Mail className="w-4 h-4 text-muted-foreground" />
                                    {lead.email}
                                </div>
                            )}
                        </div>
                    </section>

                    {/* Preferences */}
                    <section>
                        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Preferences</h3>
                        <div className="grid grid-cols-2 gap-3">
                            {lead.bedrooms != null && (
                                <div className="flex items-center gap-2 text-sm text-foreground">
                                    <BedDouble className="w-4 h-4 text-muted-foreground" />
                                    {lead.bedrooms} BHK
                                </div>
                            )}
                            {lead.budget_max != null && (
                                <div className="flex items-center gap-2 text-sm text-foreground">
                                    <Banknote className="w-4 h-4 text-muted-foreground" />
                                    ${Number(lead.budget_max).toLocaleString('en-CA')}/mo
                                </div>
                            )}
                            {lead.move_in_timeline && (
                                <div className="flex items-center gap-2 text-sm text-foreground">
                                    <Calendar className="w-4 h-4 text-muted-foreground" />
                                    {lead.move_in_timeline}
                                </div>
                            )}
                            {lead.floor_preference && (
                                <div className="text-sm text-foreground text-muted-foreground">
                                    Floor: {lead.floor_preference}
                                </div>
                            )}
                            {lead.occupants != null && (
                                <div className="text-sm text-foreground text-muted-foreground">
                                    Occupants: {lead.occupants}
                                </div>
                            )}
                        </div>
                    </section>

                    {/* Matched Listings */}
                    {(lead.listing_uuid || (lead.interested_listing_ids && lead.interested_listing_ids.length > 0)) && (
                        <section>
                            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Matched Listings</h3>
                            <div className="space-y-2">
                                {lead.listing_uuid && (() => {
                                    const primary = findListing(lead.listing_uuid);
                                    return (
                                        <div className="flex items-center gap-2 text-sm">
                                            <span className="text-muted-foreground">Primary:</span>
                                            <span className="font-mono text-xs bg-primary/10 text-primary px-2 py-0.5 rounded font-medium">
                                                {primary ? `${primary.flat_number}${primary.monthly_rent ? ` — $${Number(primary.monthly_rent).toLocaleString('en-CA')}/mo` : ''}` : lead.listing_uuid}
                                            </span>
                                        </div>
                                    );
                                })()}
                                {lead.interested_listing_ids && lead.interested_listing_ids.length > 0 && (
                                    <div className="flex items-start gap-2 text-sm">
                                        <span className="text-muted-foreground shrink-0">Also interested:</span>
                                        <div className="flex flex-wrap gap-1">
                                            {lead.interested_listing_ids
                                                .filter(id => id !== lead.listing_uuid)
                                                .map(id => {
                                                    const l = findListing(id);
                                                    return (
                                                        <span key={id} className="font-mono text-xs bg-secondary text-foreground px-2 py-0.5 rounded">
                                                            {l ? l.flat_number : id}
                                                        </span>
                                                    );
                                                })}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </section>
                    )}

                    {/* Qualifying Answers */}
                    {hasAnswers && (
                        <section>
                            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Qualifying Answers</h3>
                            <div className="space-y-2">
                                {Object.entries(qualifyingAnswers).map(([q, a]) => (
                                    <div key={q} className="text-sm">
                                        <span className="text-muted-foreground">{q}: </span>
                                        <span className="text-foreground">{String(a)}</span>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Disqualifying reason */}
                    {lead.disqualifying_reason && (
                        <section>
                            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Disqualified Because</h3>
                            <p className="text-sm text-red-500">{lead.disqualifying_reason}</p>
                        </section>
                    )}

                    {/* Call info */}
                    <section>
                        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Call Info</h3>
                        <div className="text-sm text-muted-foreground space-y-1">
                            {lead.call_id && <div>Call ID: <span className="font-mono text-xs">{lead.call_id}</span></div>}
                            {lead.call_duration_seconds != null && (
                                <div>Duration: {Math.floor(lead.call_duration_seconds / 60)}m {lead.call_duration_seconds % 60}s</div>
                            )}
                            <div>Received: {new Date(lead.created_at).toLocaleString()}</div>
                        </div>
                    </section>

                    {/* Status pipeline */}
                    <section>
                        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Pipeline Status</h3>
                        {isVoiceSet ? (
                            <div className="space-y-2">
                                <p className="text-xs text-muted-foreground">
                                    Voice set this to <strong>{lead.qualification_status.replace('_', ' ')}</strong>. Move it forward:
                                </p>
                                <select
                                    value={status}
                                    onChange={e => setStatus(e.target.value)}
                                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                                >
                                    <option value={lead.qualification_status}>{lead.qualification_status.replace('_', ' ')} (current)</option>
                                    {MANAGER_STATUSES.map(s => (
                                        <option key={s} value={s}>{s}</option>
                                    ))}
                                </select>
                            </div>
                        ) : (
                            <select
                                value={status}
                                onChange={e => setStatus(e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                            >
                                {MANAGER_STATUSES.map(s => (
                                    <option key={s} value={s}>{s}</option>
                                ))}
                            </select>
                        )}
                    </section>

                    {/* Manager Notes */}
                    <section>
                        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1">
                            <MessageSquare className="w-3.5 h-3.5" /> Manager Notes
                        </h3>
                        <textarea
                            value={notes}
                            onChange={e => setNotes(e.target.value)}
                            rows={3}
                            placeholder="Add private notes about this lead…"
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground resize-none"
                        />
                    </section>

                    {error && <p className="text-red-500 text-sm">{error}</p>}

                    <div className="flex gap-3 pt-1">
                        <button onClick={onClose}
                            className="flex-1 border border-border rounded-lg py-2 text-sm text-foreground hover:bg-secondary transition-colors">
                            Cancel
                        </button>
                        <button onClick={handleSave} disabled={saving}
                            className="flex-1 bg-primary text-primary-foreground rounded-lg py-2 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
                            {saving ? 'Saving…' : 'Save'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
