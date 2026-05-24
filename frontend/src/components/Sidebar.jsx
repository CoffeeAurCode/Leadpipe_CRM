import { Home, Building2, Settings, Users, MessageSquareMore, CalendarDays, ClipboardList, LogOut, Sparkles, DollarSign, PhoneCall, KeyRound } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib';
import { useAuth } from '../context/AuthContext';
import { useOnboarding } from '../context/OnboardingContext';
import Logo from './icon.svg';

function Sidebar({ currentView, onNavigate }) {
    const { user, signOut } = useAuth();
    const { isChecklistComplete } = useOnboarding();
    const { t } = useTranslation();

    const navItems = [
        { id: 'dashboard',   icon: Home,               label: t('nav.dashboard') },
        { id: 'tenants',     icon: Users,              label: t('nav.tenants') },
        { id: 'properties',  icon: Building2,          label: t('nav.properties') },
        { id: 'rent',        icon: DollarSign,         label: t('nav.rent') },
        { id: 'calendar',    icon: CalendarDays,       label: t('nav.calendar') },
        { id: 'complaints',  icon: ClipboardList,      label: t('nav.complaints') },
        { id: 'voice-stats', icon: PhoneCall,          label: t('nav.voiceStats') },
        { id: 'leasing',     icon: KeyRound,           label: t('nav.leasing') },
        { id: 'workflow',    icon: MessageSquareMore,  label: t('nav.smsWorkflow') },
        { id: 'settings',    icon: Settings,           label: t('nav.settings') },
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
                        <span className="hidden lg:inline font-medium">{t('nav.getStarted')}</span>
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
                    <span className="hidden lg:inline font-medium">{t('nav.logout')}</span>
                </button>
            </div>
        </aside>
    );
}

export default Sidebar;
