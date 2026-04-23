import { RefreshCw } from 'lucide-react';
import { cn } from '@/lib';
import ThemeToggle from './ThemeToggle';
import NotificationPanel from './NotificationPanel';

function TopBar({ onRefresh }) {
    return (
        <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6 transition-colors duration-200">
            <div>
                <h2 className="text-lg lg:text-xl font-semibold text-foreground">Welcome back!</h2>
                <p className="text-xs lg:text-sm text-muted-foreground">Manage your tenant complaints efficiently</p>
            </div>

            <div className="flex items-center gap-2">
                {/* Notification Bell */}
                <NotificationPanel />

                {/* Theme Toggle */}
                <ThemeToggle />

                {/* Refresh Button */}
                <button
                    onClick={onRefresh}
                    className={cn(
                        "flex items-center gap-2 px-4 py-2 rounded-lg",
                        "bg-primary text-primary-foreground",
                        "hover:bg-primary/90 transition-all duration-200",
                        "shadow-lg shadow-primary/20"
                    )}
                >
                    <RefreshCw className="w-4 h-4" />
                    <span className="hidden lg:inline font-medium">Refresh</span>
                </button>
            </div>
        </header>
    );
}

export default TopBar;

