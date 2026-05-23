import { Home, Building2, Settings, Users, MessageSquareMore, CalendarDays, ClipboardList, LogOut, Sparkles, DollarSign, PhoneCall, KeyRound } from 'lucide-react';
import { cn } from '@/lib';
import { useAuth } from '../context/AuthContext';
import { useOnboarding } from '../context/OnboardingContext';
import Logo from './icon.svg';

function Sidebar({ currentView, onNavigate }) {
    const { user, signOut } = useAuth();
    const { isChecklistComplete } = useOnboarding();
    const navItems = [
        { id: 'dashboard', icon: Home, label: 'Dashboard' },
        { id: 'tenants', icon: Users, label: 'Tenants' },
        { id: 'properties', icon: Building2, label: 'Properties' },
        { id: 'rent', icon: DollarSign, label: 'Rent' },
        { id: 'calendar', icon: CalendarDays, label: 'Calendar' },
        { id: 'complaints', icon: ClipboardList, label: 'Complaints' },
        { id: 'voice-stats', icon: PhoneCall, label: 'Voice Stats' },
        { id: 'leasing', icon: KeyRound, label: 'Leasing' },
        { id: 'workflow', icon: MessageSquareMore, label: 'SMS Workflow' },
        { id: 'settings', icon: Settings, label: 'Settings' },
    ];

    return (
        <aside className="w-20 lg:w-64 bg-card border-r border-border flex flex-col">
            {/* Logo */}
            <div className="h-16 flex items-center justify-center lg:justify-start lg:px-6 border-b border-border gap-3">
                <img src={Logo} alt="LeadPipe Logo" className="w-10 h-10 flex-shrink-0" />
                <span className="hidden lg:inline text-xl font-bold text-foreground">LeadPipe</span>
            </div>

            {/* Nav */}
            <nav data-tour="sidebar-nav" className="flex-1 py-6 px-3 lg:px-4 overflow-y-auto">
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

            {/* Get Started — onboarding checklist */}
            {!isChecklistComplete && (
                <div className="px-3 lg:px-4 pb-2">
                    <button
                        onClick={() => onNavigate('onboarding')}
                        className={cn(
                            "w-full flex items-center gap-3 px-3 lg:px-4 py-3 rounded-lg transition-all duration-200",
                            currentView === 'onboarding'
                                ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                                : "text-amber-500 bg-amber-500/10 hover:bg-amber-500/20 animate-pulse"
                        )}
                    >
                        <Sparkles className="w-5 h-5 flex-shrink-0" />
                        <span className="hidden lg:inline font-medium">Get Started</span>
                    </button>
                </div>
            )}

            {/* User info + Logout */}
            <div className="border-t border-border p-3 lg:p-4">
                <div className="hidden lg:block text-xs text-muted-foreground truncate mb-2 px-1">
                    {user?.email}
                </div>
                <button
                    onClick={signOut}
                    className="w-full flex items-center gap-3 px-3 lg:px-4 py-3 rounded-lg text-muted-foreground hover:bg-red-500/10 hover:text-red-500 transition-all duration-200"
                >
                    <LogOut className="w-5 h-5 flex-shrink-0" />
                    <span className="hidden lg:inline font-medium">Logout</span>
                </button>
            </div>
        </aside>
    );
}

export default Sidebar;

