import { createContext, useContext, useEffect, useState } from 'react';

const ThemeContext = createContext(null);

/**
 * ThemeProvider wraps the app and manages the light/dark theme.
 * - Reads from localStorage on first load.
 * - Falls back to the system's preferred color scheme.
 * - Applies the 'dark' class to <html> for Tailwind's class-based dark mode.
 */
export function ThemeProvider({ children }) {
    const [theme, setTheme] = useState(() => {
        // 1. Check for a saved preference in localStorage
        const saved = localStorage.getItem('theme');
        if (saved === 'dark' || saved === 'light') return saved;

        // 2. Fall back to system preference
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';

        // 3. Default to light
        return 'light';
    });

    useEffect(() => {
        const root = document.documentElement;

        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }

        // Persist preference
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => {
        setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
    };

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

/**
 * Custom hook to access theme context.
 * Must be used within a <ThemeProvider>.
 */
export function useTheme() {
    const ctx = useContext(ThemeContext);
    if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
    return ctx;
}
