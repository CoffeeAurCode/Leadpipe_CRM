import { useState, useEffect, useRef, useCallback } from 'react';
import { Bell, CheckCheck, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib';
import { fetchNotifications, markNotificationRead, markAllNotificationsRead } from '../services/apiService';

const TYPE_COLORS = {
    appointment: 'bg-blue-500/15 text-blue-400',
    complaint:   'bg-red-500/15 text-red-500',
    rent:        'bg-emerald-500/15 text-emerald-500',
    lead:        'bg-violet-500/15 text-violet-500',
    system:      'bg-secondary text-muted-foreground',
};

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    const days = Math.floor(diff / 86400);
    return days === 1 ? 'Yesterday' : `${days}d ago`;
}

export default function NotificationPanel() {
    const { t } = useTranslation();
    const [open, setOpen] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(false);
    const panelRef = useRef(null);

    const unreadCount = notifications.filter(n => !n.is_read).length;

    const load = useCallback(async () => {
        try {
            const data = await fetchNotifications();
            setNotifications(data);
        } catch {
            // silently fail — table may not exist yet
        }
    }, []);

    // Poll every 30 seconds when tab is visible
    useEffect(() => {
        load();
        const id = setInterval(() => {
            if (!document.hidden) load();
        }, 30000);
        const onVisible = () => { if (!document.hidden) load(); };
        document.addEventListener('visibilitychange', onVisible);
        return () => { clearInterval(id); document.removeEventListener('visibilitychange', onVisible); };
    }, [load]);

    // Close on outside click
    useEffect(() => {
        if (!open) return;
        const handle = (e) => {
            if (panelRef.current && !panelRef.current.contains(e.target)) setOpen(false);
        };
        document.addEventListener('mousedown', handle);
        return () => document.removeEventListener('mousedown', handle);
    }, [open]);

    const handleMarkRead = async (id) => {
        try {
            await markNotificationRead(id);
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
        } catch {/* ignore */}
    };

    const handleMarkAllRead = async () => {
        try {
            await markAllNotificationsRead();
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        } catch {/* ignore */}
    };

    return (
        <div className="relative" ref={panelRef}>
            {/* Bell button */}
            <button
                onClick={() => { setOpen(o => !o); if (!open) load(); }}
                className={cn(
                    'relative p-2 rounded-lg transition-all duration-200',
                    open
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                )}
                aria-label="Notifications"
            >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[16px] h-4 px-1 bg-red-500 text-white text-[10px] font-bold rounded-full leading-none">
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {/* Panel */}
            {open && (
                <div className="absolute right-0 top-full mt-2 w-80 bg-card border border-border rounded-xl shadow-2xl z-50 overflow-hidden">
                    {/* Panel header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                        <div className="flex items-center gap-2">
                            <Bell className="w-4 h-4 text-primary" />
                            <span className="text-sm font-semibold text-foreground">{t('notifications.title')}</span>
                            {unreadCount > 0 && (
                                <span className="px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-500 text-xs font-medium">
                                    {unreadCount} new
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-1">
                            {unreadCount > 0 && (
                                <button
                                    onClick={handleMarkAllRead}
                                    className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                                    title={t('notifications.markAllRead')}
                                >
                                    <CheckCheck className="w-4 h-4" />
                                </button>
                            )}
                            <button
                                onClick={() => setOpen(false)}
                                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    {/* List */}
                    <ul className="max-h-96 overflow-y-auto divide-y divide-border">
                        {notifications.length === 0 ? (
                            <li className="px-4 py-8 text-center text-muted-foreground text-sm">
                                {t('notifications.empty')}
                            </li>
                        ) : notifications.map(n => (
                            <li
                                key={n.id}
                                onClick={() => !n.is_read && handleMarkRead(n.id)}
                                className={cn(
                                    'px-4 py-3 cursor-pointer transition-colors hover:bg-secondary/50',
                                    !n.is_read && 'bg-primary/5'
                                )}
                            >
                                <div className="flex items-start gap-2">
                                    {!n.is_read && (
                                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                                    )}
                                    {n.is_read && <span className="w-1.5 h-1.5 flex-shrink-0" />}
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-foreground leading-tight">{n.title}</p>
                                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.body}</p>
                                        <div className="flex items-center gap-2 mt-1.5">
                                            <span className={cn('px-1.5 py-0.5 rounded-full text-[10px] font-medium', TYPE_COLORS[n.type] || TYPE_COLORS.system)}>
                                                {n.type}
                                            </span>
                                            <span className="text-[10px] text-muted-foreground">{timeAgo(n.created_at)}</span>
                                        </div>
                                    </div>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
