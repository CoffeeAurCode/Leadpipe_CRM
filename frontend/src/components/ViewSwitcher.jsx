import { cn } from '@/lib';

/**
 * ViewSwitcher — Segmented control for the 3 property page views.
 * Props:
 *  - activeView: 'properties' | 'buildings' | 'units'
 *  - onChange: (view) => void
 */
const VIEWS = [
    { id: 'properties', label: 'Properties' },
    { id: 'buildings', label: 'Buildings' },
    { id: 'units', label: 'Units' },
];

function ViewSwitcher({ activeView, onChange }) {
    return (
        <div
            className="inline-flex items-center gap-1 p-1 rounded-xl bg-secondary border border-border"
            role="tablist"
            aria-label="Property view switcher"
        >
            {VIEWS.map(view => (
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
