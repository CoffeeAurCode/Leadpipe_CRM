import { useState, useRef, useEffect } from 'react';
import { RefreshCw, LogOut, Settings, User } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib';
import ThemeToggle from './ThemeToggle';
import NotificationPanel from './NotificationPanel';
import { useAuth } from '../context/AuthContext';

function LanguageToggle() {
    const { i18n, t } = useTranslation();
    const toggle = () => {
        const next = i18n.language === 'en' ? 'fr-CA' : 'en';
        i18n.changeLanguage(next);
        localStorage.setItem('lang', next);
    };
    return (
        <button
            onClick={toggle}
            className="px-3 py-1.5 rounded-lg border border-border text-sm font-semibold hover:bg-secondary transition-colors text-foreground"
            aria-label="Toggle language"
        >
            {t('lang.toggle')}
        </button>
    );
}

function ProfileMenu({ onNavigate }) {
    const { user, signOut } = useAuth();
    const { t } = useTranslation();
    const [open, setOpen] = useState(false);
    const menuRef = useRef(null);

    useEffect(() => {
        if (!open) return;
        const handler = (e) => {
            if (!menuRef.current?.contains(e.target)) setOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [open]);

    const initials = (() => {
        const name = user?.user_metadata?.full_name || user?.email || '';
        if (!name) return 'U';
        const parts = name.split(/\s+/);
        return parts.length >= 2
            ? (parts[0][0] + parts[1][0]).toUpperCase()
            : name.slice(0, 2).toUpperCase();
    })();

    const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Account';

    return (
        <div className="relative" ref={menuRef}>
            <button
                onClick={() => setOpen(o => !o)}
                className={cn(
                    'flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors',
                    'hover:bg-secondary',
                    open && 'bg-secondary'
                )}
                aria-label="Profile menu"
            >
                <div className="w-8 h-8 rounded-full bg-primary/15 text-primary flex items-center justify-center text-xs font-bold flex-shrink-0 select-none">
                    {initials}
                </div>
                <span className="hidden lg:block text-sm font-medium text-foreground max-w-[120px] truncate">
                    {displayName}
                </span>
            </button>

            {open && (
                <div className="absolute right-0 top-full mt-2 w-64 bg-card border border-border rounded-xl shadow-xl z-50 py-2 overflow-hidden">
                    <div className="px-4 py-3 border-b border-border">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-primary/15 text-primary flex items-center justify-center text-sm font-bold flex-shrink-0">
                                {initials}
                            </div>
                            <div className="min-w-0">
                                <p className="text-sm font-semibold text-foreground truncate">{displayName}</p>
                                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                            </div>
                        </div>
                    </div>

                    <div className="py-1">
                        <button
                            onClick={() => { setOpen(false); onNavigate?.('settings'); }}
                            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:bg-secondary transition-colors"
                        >
                            <Settings className="w-4 h-4 text-muted-foreground" />
                            {t('topbar.settings')}
                        </button>
                        <button
                            onClick={() => { setOpen(false); signOut(); }}
                            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-500 hover:bg-red-500/10 transition-colors"
                        >
                            <LogOut className="w-4 h-4" />
                            {t('topbar.signOut')}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

function TopBar({ onRefresh, isRefreshing, onNavigate }) {
    const { t } = useTranslation();
    return (
        <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6 transition-colors duration-200">
            <div>
                <h2 className="text-lg lg:text-xl font-semibold text-foreground">{t('topbar.welcome')}</h2>
                <p className="text-xs lg:text-sm text-muted-foreground">{t('topbar.subtitle')}</p>
            </div>

            <div className="flex items-center gap-2">
                <NotificationPanel />
                <ThemeToggle />
                <LanguageToggle />
                <button
                    onClick={onRefresh}
                    disabled={isRefreshing}
                    className={cn(
                        "flex items-center gap-2 px-4 py-2 rounded-lg",
                        "bg-primary text-primary-foreground",
                        "hover:bg-primary/90 transition-all duration-200",
                        "shadow-lg shadow-primary/20",
                        "disabled:opacity-70 disabled:cursor-not-allowed"
                    )}
                >
                    <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
                    <span className="hidden lg:inline font-medium">{t('topbar.refresh')}</span>
                </button>
                <ProfileMenu onNavigate={onNavigate} />
            </div>
        </header>
    );
}

export default TopBar;
