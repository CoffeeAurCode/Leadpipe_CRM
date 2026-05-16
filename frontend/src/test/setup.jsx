import '@testing-library/jest-dom';
import { vi } from 'vitest';

// SVG imports return a string stub
vi.mock('../components/icon.svg', () => ({ default: 'icon-svg-stub' }));
vi.mock('./icon.svg', () => ({ default: 'icon-svg-stub' }));

// CSS module imports are no-ops
vi.mock('./CalendarView.css', () => ({}));
vi.mock('./Dashboard.css', () => ({}));
vi.mock('./AppointmentModal.css', () => ({}));

// Supabase — full mock so no real network calls are made
vi.mock('../lib/supabase', () => ({
    supabase: {
        auth: {
            getSession: vi.fn().mockResolvedValue({
                data: { session: { access_token: 'mock-token', user: { id: 'user-1', email: 'test@example.com' } } },
            }),
            onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
            signOut: vi.fn().mockResolvedValue({}),
            signInWithOAuth: vi.fn().mockResolvedValue({}),
            signInWithPassword: vi.fn().mockResolvedValue({ error: null }),
            signUp: vi.fn().mockResolvedValue({ data: { user: { id: 'user-1' } }, error: null }),
        },
        from: vi.fn().mockReturnValue({
            select: vi.fn().mockReturnThis(),
            insert: vi.fn().mockReturnThis(),
            update: vi.fn().mockReturnThis(),
            eq: vi.fn().mockReturnThis(),
            maybeSingle: vi.fn().mockResolvedValue({ data: null, error: null }),
            single: vi.fn().mockResolvedValue({ data: null, error: null }),
        }),
    },
}));

// framer-motion — render children directly, skip animations
vi.mock('framer-motion', () => {
    const mockMotionValue = (initial) => {
        let _val = initial;
        const listeners = [];
        return {
            get: () => _val,
            set: (v) => { _val = v; listeners.forEach(l => l(v)); },
            onChange: (cb) => { listeners.push(cb); return () => {}; },
            destroy: vi.fn(),
        };
    };

    return {
        motion: new Proxy({}, {
            get: (_, tag) => {
                const Component = ({ children, ...props }) => {
                    const {
                        initial, animate, exit, transition, whileHover, whileTap,
                        variants, layout, layoutId, ...rest
                    } = props;
                    const Tag = tag;
                    return <Tag {...rest}>{children}</Tag>;
                };
                Component.displayName = `motion.${tag}`;
                return Component;
            },
        }),
        AnimatePresence: ({ children }) => children,
        useAnimation: () => ({ start: vi.fn() }),
        useMotionValue: (v) => mockMotionValue(v),
        useSpring: (initial) => mockMotionValue(initial),
        useTransform: (_mv, _from, _to) => mockMotionValue(0),
        useMotionValueEvent: (mv, _event, cb) => {
            // no-op in tests — spring animations don't run in jsdom
        },
        useReducedMotion: () => false,
        useInView: () => true,
        useScroll: () => ({ scrollY: mockMotionValue(0), scrollYProgress: mockMotionValue(0) }),
    };
});

// ThemeContext — mock so components using useTheme work outside ThemeProvider
vi.mock('../context/ThemeContext', () => ({
    useTheme: () => ({ theme: 'light', toggleTheme: vi.fn() }),
    ThemeProvider: ({ children }) => children,
}));

// window.matchMedia — jsdom doesn't implement it
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

// ResizeObserver — used by recharts
global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}));

// IntersectionObserver — used by some scroll/visibility libraries
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}));

// scrollIntoView — not implemented in jsdom 29
window.HTMLElement.prototype.scrollIntoView = vi.fn();
