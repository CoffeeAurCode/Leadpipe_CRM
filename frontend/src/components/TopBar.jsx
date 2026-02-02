import { RefreshCw, Bell } from 'lucide-react';
import { cn } from '@/lib';

function TopBar({ onRefresh }) {
    return (
        <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6">
            <div>
                <h2 className="text-lg lg:text-xl font-semibold text-foreground">Welcome back!</h2>
                <p className="text-xs lg:text-sm text-muted-foreground">Manage your tenant complaints efficiently</p>
            </div>

            <div className="flex items-center gap-3">
                {/* Notification Button */}
                <button className="relative p-2 rounded-lg hover:bg-secondary transition-colors">
                    <Bell className="w-5 h-5 text-muted-foreground" />
                    <span className="absolute top- right-1 w-2 h-2 bg-primary rounded-full"></span>
                </button>

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

