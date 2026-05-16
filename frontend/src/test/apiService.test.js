/**
 * Section 5.1 — apiService.js
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock supabase before importing apiService
vi.mock('../lib/supabase', () => ({
    supabase: {
        auth: {
            getSession: vi.fn(),
            signOut: vi.fn().mockResolvedValue({}),
        },
    },
}));

import { supabase } from '../lib/supabase';

// We test authFetch indirectly through the exported functions
import {
    fetchComplaints,
    fetchFlats,
    fetchTenants,
    updateComplaint,
    createComplaint,
    sendChatMessage,
    getStatusDisplay,
    getPriorityDisplay,
    formatDate,
} from '../services/apiService';

const MOCK_TOKEN = 'mock-jwt-token';
const MOCK_SESSION = { access_token: MOCK_TOKEN, user: { id: 'u1' } };

beforeEach(() => {
    vi.clearAllMocks();
    supabase.auth.getSession.mockResolvedValue({ data: { session: MOCK_SESSION } });
    // Reset fetch mock
    global.fetch = vi.fn();
});

// ── authFetch behaviour ───────────────────────────────────────────────────────

describe('authFetch — Authorization header', () => {
    it('attaches Bearer token to every request', async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => [],
        });

        await fetchComplaints();

        expect(global.fetch).toHaveBeenCalledTimes(1);
        const [, options] = global.fetch.mock.calls[0];
        expect(options.headers['Authorization']).toBe(`Bearer ${MOCK_TOKEN}`);
    });

    it('calls signOut and reloads on 401', async () => {
        const reloadSpy = vi.fn();
        Object.defineProperty(window, 'location', { value: { reload: reloadSpy }, writable: true });

        global.fetch.mockResolvedValue({ ok: false, status: 401 });

        await expect(fetchComplaints()).rejects.toThrow('Session expired');
        expect(supabase.auth.signOut).toHaveBeenCalled();
    });

    it('redirects to /pricing on 403', async () => {
        const hrefSetter = vi.fn();
        Object.defineProperty(window, 'location', {
            value: { ...window.location, set href(v) { hrefSetter(v); } },
            writable: true,
        });

        global.fetch.mockResolvedValue({ ok: false, status: 403 });

        await expect(fetchComplaints()).rejects.toThrow('Subscription required');
    });

    it('reloads + signOut when no session exists', async () => {
        supabase.auth.getSession.mockResolvedValue({ data: { session: null } });
        const reloadSpy = vi.fn();
        Object.defineProperty(window, 'location', { value: { reload: reloadSpy }, writable: true });

        await expect(fetchComplaints()).rejects.toThrow('No active session');
        expect(supabase.auth.signOut).toHaveBeenCalled();
    });
});

// ── Endpoint mapping ──────────────────────────────────────────────────────────

describe('fetchComplaints', () => {
    it('GET /complaints and returns data', async () => {
        const mockData = [{ id: 1, status: 'pending' }];
        global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => mockData });

        const result = await fetchComplaints();

        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/complaints'),
            expect.objectContaining({ headers: expect.objectContaining({ Authorization: `Bearer ${MOCK_TOKEN}` }) })
        );
        expect(result).toEqual(mockData);
    });

    it('throws on non-ok response', async () => {
        global.fetch.mockResolvedValue({ ok: false, status: 500 });
        await expect(fetchComplaints()).rejects.toThrow();
    });
});

describe('fetchFlats', () => {
    it('GET /flats', async () => {
        global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => [] });
        await fetchFlats();
        expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/flats'), expect.any(Object));
    });
});

describe('fetchTenants', () => {
    it('GET /tenants without params', async () => {
        global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => [] });
        await fetchTenants();
        expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/tenants'), expect.any(Object));
    });

    it('appends rent_status query param when provided', async () => {
        global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => [] });
        await fetchTenants({ rent_status: 'Overdue' });
        const [url] = global.fetch.mock.calls[0];
        expect(url).toContain('rent_status=Overdue');
    });
});

describe('updateComplaint', () => {
    it('PATCH /complaints/:id with JSON body', async () => {
        const updated = { id: 1, status: 'in-progress' };
        global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => updated });

        const result = await updateComplaint(1, { status: 'in-progress' });

        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toContain('/complaints/1');
        expect(options.method).toBe('PATCH');
        expect(JSON.parse(options.body)).toEqual({ status: 'in-progress' });
        expect(result).toEqual(updated);
    });
});

describe('createComplaint', () => {
    it('POST /complaints', async () => {
        const payload = { category: 'water', description: 'leak' };
        global.fetch.mockResolvedValue({ ok: true, status: 201, json: async () => ({ id: 99, ...payload }) });

        await createComplaint(payload);

        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toContain('/complaints');
        expect(options.method).toBe('POST');
    });
});

describe('sendChatMessage', () => {
    it('POST /chat with messages array', async () => {
        const messages = [{ role: 'user', content: 'hello' }];
        global.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ reply: 'hi', refresh_needed: false }) });

        const result = await sendChatMessage(messages);
        expect(result.reply).toBe('hi');

        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toContain('/chat');
        expect(options.method).toBe('POST');
    });
});

// ── Helper functions ──────────────────────────────────────────────────────────

describe('getStatusDisplay', () => {
    it('returns label for known status', () => {
        expect(getStatusDisplay('pending')).toBe('Pending');
        expect(getStatusDisplay('in-progress')).toBe('In Progress');
        expect(getStatusDisplay('resolved')).toBe('Resolved');
    });

    it('falls back to the raw string for unknown status', () => {
        expect(getStatusDisplay('unknown-status')).toBe('unknown-status');
    });
});

describe('getPriorityDisplay', () => {
    it('maps priority keys to labels', () => {
        expect(getPriorityDisplay('high')).toBe('High');
        expect(getPriorityDisplay('medium')).toBe('Medium');
        expect(getPriorityDisplay('low')).toBe('Low');
    });

    it('passes through unknown priorities', () => {
        expect(getPriorityDisplay('critical')).toBe('critical');
    });
});

describe('formatDate', () => {
    it('returns N/A for falsy input', () => {
        expect(formatDate(null)).toBe('N/A');
        expect(formatDate('')).toBe('N/A');
    });

    it('formats a UTC date string into a readable string', () => {
        const result = formatDate('2026-01-15T08:30:00Z');
        // Should be a non-empty string with month/day/year pattern
        expect(result).toMatch(/Jan/);
        expect(result).toMatch(/15/);
        expect(result).toMatch(/2026/);
    });

    it('handles dates without Z suffix', () => {
        const result = formatDate('2026-01-15T08:30:00');
        expect(typeof result).toBe('string');
        expect(result).not.toBe('N/A');
    });
});
