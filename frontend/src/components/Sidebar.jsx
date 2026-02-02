import { Home, Calendar, Settings } from 'lucide-react';
import { cn } from '@/lib';

function Sidebar({ currentView, onNavigate }) {
    const navItems = [
        { id: 'dashboard', icon: Home, label: 'Dashboard' },
        { id: 'calendar', icon: Calendar, label: 'Calendar' },
        { id: 'settings', icon: Settings, label: 'Settings' },
    ];

    return (
        <aside className="w-20 lg:w-64 bg-card border-r border-border flex flex-col">
            {/* Logo */}
            <div className="h-16 flex items-center justify-center lg:justify-start lg:px-6 border-b border-border">
                <h1 className="text-xl lg:text-2xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                    <span className="hidden lg:inline">Dashboard</span>
                    <span className="lg:hidden">D</span>
                </h1>
            </div>

            {/* Nav */}
            <nav className="flex-1 py-6 px-3 lg:px-4">
                <ul className="space-y-2">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = currentView === item.id;

                        return (
                            <li key={item.id}>
                                <button
                                    onClick={() => onNavigate(item.id)}
                                    className={cn(
                                        "w-full flex items-center gap-3 px-3 lg:px-4 py-3 rounded-lg transition-all duration-200",
                                        isActive
                                            ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                                            : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                                    )}
                                >
                                    <Icon className="w-5 h-5 flex-shrink-0" />
                                    <span className="hidden lg:inline font-medium">{item.label}</span>
                                </button>
                            </li>
                        );
                    })}
                </ul>
            </nav>
        </aside>
    );
}

export default Sidebar;

