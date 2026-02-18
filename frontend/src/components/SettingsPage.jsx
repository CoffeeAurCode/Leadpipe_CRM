import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Settings as SettingsIcon, Save, RefreshCw } from 'lucide-react';
import { fetchProperties, fetchPropertySettings, updatePropertySettings } from '../services/apiService';
import { cn } from '@/lib';

/**
 * SettingsPage Component
 * 
 * Full-page settings view matching the design pattern of PropertiesPage.
 * Allows managing feature toggles for all properties.
 */
function SettingsPage() {
    const [properties, setProperties] = useState([]);
    const [selectedPropertyUuid, setSelectedPropertyUuid] = useState(null);
    const [settings, setSettings] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [hasChanges, setHasChanges] = useState(false);
    const [pendingChanges, setPendingChanges] = useState({});

    useEffect(() => {
        loadProperties();
    }, []);

    useEffect(() => {
        if (selectedPropertyUuid) {
            loadSettings(selectedPropertyUuid);
        }
    }, [selectedPropertyUuid]);

    async function loadProperties() {
        try {
            setLoading(true);
            const data = await fetchProperties();
            setProperties(data);
            if (data.length > 0) {
                setSelectedPropertyUuid(data[0].uuid);
            }
            setError(null);
        } catch (err) {
            console.error('Error loading properties:', err);
            setError('Failed to load properties');
        } finally {
            setLoading(false);
        }
    }

    async function loadSettings(propertyUuid) {
        try {
            setLoading(true);
            const data = await fetchPropertySettings(propertyUuid);
            setSettings(data.features);
            setPendingChanges({});
            setHasChanges(false);
            setError(null);
        } catch (err) {
            console.error('Error loading settings:', err);
            setError('Failed to load settings');
        } finally {
            setLoading(false);
        }
    }

    function handleToggle(featureKey, currentValue) {
        const newValue = !currentValue;
        setPendingChanges(prev => ({
            ...prev,
            [featureKey]: newValue
        }));
        setHasChanges(true);
    }

    async function handleSave() {
        try {
            setSaving(true);
            await updatePropertySettings(selectedPropertyUuid, pendingChanges);
            await loadSettings(selectedPropertyUuid);
            setError(null);
        } catch (err) {
            console.error('Error saving settings:', err);
            setError('Failed to save settings');
        } finally {
            setSaving(false);
        }
    }

    function handleCancel() {
        setPendingChanges({});
        setHasChanges(false);
    }

    if (loading && !settings) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
                        <p className="text-muted-foreground mt-1">Loading...</p>
                    </div>
                </div>
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                </div>
            </div>
        );
    }

    if (error && !settings) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
                        <p className="text-muted-foreground mt-1">Error loading data</p>
                    </div>
                </div>
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500">
                    <p className="text-red-500">{error}</p>
                </div>
            </div>
        );
    }

    if (!settings) return null;

    // Group features by category
    const categories = {};
    Object.entries(settings).forEach(([key, meta]) => {
        const cat = meta.category;
        if (!categories[cat]) categories[cat] = [];
        categories[cat].push({ key, ...meta });
    });

    const selectedProperty = properties.find(p => p.uuid === selectedPropertyUuid);

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between"
            >
                <div>
                    <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
                        <SettingsIcon className="w-8 h-8 text-primary" />
                        Settings
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Manage feature settings for your properties
                    </p>
                </div>
            </motion.div>

            {/* Property Selector */}
            {properties.length > 1 && (
                <div className="flex items-center gap-3">
                    <label className="text-sm font-medium text-foreground">Property:</label>
                    <select
                        value={selectedPropertyUuid || ''}
                        onChange={(e) => setSelectedPropertyUuid(e.target.value)}
                        className="px-4 py-2 rounded-lg border border-border bg-card text-foreground"
                    >
                        {properties.map(prop => (
                            <option key={prop.uuid} value={prop.uuid}>
                                {prop.name || `${prop.address} - Unit ${prop.flat_number}`}
                            </option>
                        ))}
                    </select>
                </div>
            )}

            {/* Current Property Info */}
            {selectedProperty && (
                <div className="p-4 rounded-lg bg-card border border-border">
                    <p className="text-sm text-muted-foreground">
                        Configuring: <span className="font-medium text-foreground">
                            {selectedProperty.name || `${selectedProperty.address} - Unit ${selectedProperty.flat_number}`}
                        </span>
                    </p>
                </div>
            )}

            {/* Error Display */}
            {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800">
                    {error}
                </div>
            )}

            {/* Feature Categories */}
            <div className="space-y-6">
                {Object.entries(categories).map(([category, features]) => (
                    <motion.div
                        key={category}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="rounded-lg border border-border bg-card overflow-hidden"
                    >
                        <div className="px-6 py-4 border-b border-border bg-secondary/50">
                            <h3 className="text-lg font-semibold text-foreground">
                                {category}
                            </h3>
                        </div>
                        <div className="p-6 space-y-4">
                            {features.map(feature => {
                                const currentValue = pendingChanges.hasOwnProperty(feature.key)
                                    ? pendingChanges[feature.key]
                                    : feature.enabled;

                                return (
                                    <label
                                        key={feature.key}
                                        className={cn(
                                            "flex items-start gap-4 p-4 rounded-lg cursor-pointer transition-colors border",
                                            currentValue
                                                ? "bg-primary/5 border-primary/20"
                                                : "bg-background border-border hover:bg-secondary/50"
                                        )}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={currentValue}
                                            onChange={() => handleToggle(feature.key, currentValue)}
                                            className="mt-1 w-5 h-5 text-primary rounded focus:ring-primary"
                                        />
                                        <div className="flex-1">
                                            <div className="font-medium text-foreground">
                                                {feature.display_name}
                                            </div>
                                            <div className="text-sm text-muted-foreground mt-1">
                                                {feature.description}
                                            </div>
                                        </div>
                                    </label>
                                );
                            })}
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Action Buttons */}
            {hasChanges && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="sticky bottom-6 flex items-center justify-end gap-3 p-4 rounded-lg bg-card border border-border shadow-xl"
                >
                    <button
                        onClick={handleCancel}
                        disabled={saving}
                        className="px-6 py-2 rounded-lg text-muted-foreground hover:bg-secondary transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className={cn(
                            "flex items-center gap-2 px-6 py-2 rounded-lg transition-colors",
                            "bg-primary text-primary-foreground hover:bg-primary/90"
                        )}
                    >
                        {saving ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                Saving...
                            </>
                        ) : (
                            <>
                                <Save className="w-4 h-4" />
                                Save Changes
                            </>
                        )}
                    </button>
                </motion.div>
            )}
        </div>
    );
}

export default SettingsPage;
