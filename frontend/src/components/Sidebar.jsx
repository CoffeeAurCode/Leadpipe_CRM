import { Home, Building2, Settings, Users, MessageSquareMore, CalendarDays } from 'lucide-react';
import { cn } from '@/lib';
import Logo from './icon.svg';

function Sidebar({ currentView, onNavigate }) {
    const navItems = [
        { id: 'dashboard', icon: Home, label: 'Dashboard' },
        { id: 'properties', icon: Building2, label: 'Properties' },
        { id: 'tenants', icon: Users, label: 'Tenants' },
        { id: 'settings', icon: Settings, label: 'Settings' },
        { id: 'workflow', icon: MessageSquareMore, label: 'SMS Workflow' },
        { id: 'calendar', icon: CalendarDays, label: 'Calendar' },
    ];

    return (
        <aside className="w-20 lg:w-64 bg-card border-r border-border flex flex-col">
            {/* Logo */}
            <div className="h-16 flex items-center justify-center lg:justify-start lg:px-6 border-b border-border gap-3">
                <img src={Logo} alt="LeadPipe Logo" className="w-10 h-10 flex-shrink-0" />
                <span className="hidden lg:inline text-xl font-bold text-foreground">LeadPipe</span>
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

