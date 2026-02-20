import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { cn } from '@/lib';

/**
 * ThemeToggle renders a Sun/Moon icon button that switches between
 * light and dark mode using the ThemeContext.
 */
function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();
    const isDark = theme === 'dark';

    return (
        <button
            onClick={toggleTheme}
            aria-label={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            className={cn(
                'relative p-2 rounded-lg transition-all duration-200',
                'hover:bg-secondary',
                'focus:outline-none focus:ring-2 focus:ring-ring'
            )}
        >
            {/* Sun icon — visible in dark mode, fades out in light mode */}
            <Sun
                className={cn(
                    'w-5 h-5 text-amber-400 absolute inset-0 m-auto',
                    'transition-all duration-300',
                    isDark
                        ? 'opacity-100 rotate-0 scale-100'
                        : 'opacity-0 -rotate-90 scale-0'
                )}
            />
            {/* Moon icon — visible in light mode, fades out in dark mode */}
            <Moon
                className={cn(
                    'w-5 h-5 text-slate-600 absolute inset-0 m-auto',
                    'transition-all duration-300',
                    isDark
                        ? 'opacity-0 rotate-90 scale-0'
                        : 'opacity-100 rotate-0 scale-100'
                )}
            />
            {/* Invisible spacer to maintain button size */}
            <span className="w-5 h-5 block opacity-0" aria-hidden="true" />
        </button>
    );
}

export default ThemeToggle;
