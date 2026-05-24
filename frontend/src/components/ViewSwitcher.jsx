import { useTranslation } from 'react-i18next';
import { cn } from '@/lib';

function ViewSwitcher({ activeView, onChange }) {
    const { t } = useTranslation();
    const views = [
        { id: 'properties', label: t('properties.viewSwitcher.properties') },
        { id: 'buildings', label: t('properties.viewSwitcher.buildings') },
        { id: 'units', label: t('properties.viewSwitcher.units') },
    ];

    return (
        <div
            className="inline-flex items-center gap-1 p-1 rounded-xl bg-secondary border border-border"
            role="tablist"
            aria-label="Property view switcher"
        >
            {views.map(view => (
                <button
                    key={view.id}
                    role="tab"
                    id={`view-tab-${view.id}`}
                    aria-selected={activeView === view.id}
                    onClick={() => onChange(view.id)}
                    className={cn(
                        'px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
                        activeView === view.id
                            ? 'bg-card text-foreground shadow-sm border border-border'
                            : 'text-muted-foreground hover:text-foreground'
                    )}
                >
                    {view.label}
                </button>
            ))}
        </div>
    );
}

export default ViewSwitcher;
