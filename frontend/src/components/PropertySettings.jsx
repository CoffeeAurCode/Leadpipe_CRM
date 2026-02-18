import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Settings, Save, X } from 'lucide-react';
import { fetchPropertySettings, updatePropertySettings } from '../services/apiService';
import { cn } from '@/lib';

/**
 * PropertySettings Component
 * 
 * Displays and manages feature toggles for a property.
 * Features are grouped by category for better organization.
 */
export function PropertySettings({ propertyUuid, onClose }) {
    const [settings, setSettings] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [hasChanges, setHasChanges] = useState(false);
    const [pendingChanges, setPendingChanges] = useState({});

    useEffect(() => {
        loadSettings();
    }, [propertyUuid]);

    async function loadSettings() {
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
            await updatePropertySettings(propertyUuid, pendingChanges);
            await loadSettings(); // Reload to get fresh state
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

    if (loading) {
        return (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
                    <div className="flex items-center justify-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
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

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden"
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b">
                    <div className="flex items-center gap-3">
                        <Settings className="w-6 h-6 text-blue-600" />
                        <h2 className="text-2xl font-bold">Property Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Error Display */}
                {error && (
                    <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800">
                        {error}
                    </div>
                )}

                {/* Content */}
                <div className="overflow-y-auto max-h-[calc(90vh-180px)] p-6">
                    <div className="space-y-6">
                        {Object.entries(categories).map(([category, features]) => (
                            <div key={category} className="border rounded-lg p-4 bg-gray-50">
                                <h3 className="text-lg font-semibold mb-4 text-gray-800">
                                    {category}
                                </h3>
                                <div className="space-y-3">
                                    {features.map(feature => {
                                        const currentValue = pendingChanges.hasOwnProperty(feature.key)
                                            ? pendingChanges[feature.key]
                                            : feature.enabled;

                                        return (
                                            <label
                                                key={feature.key}
                                                className={cn(
                                                    "flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors",
                                                    "hover:bg-white",
                                                    currentValue && "bg-blue-50"
                                                )}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={currentValue}
                                                    onChange={() => handleToggle(feature.key, currentValue)}
                                                    className="mt-1 w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                                                />
                                                <div className="flex-1">
                                                    <div className="font-medium text-gray-900">
                                                        {feature.display_name}
                                                    </div>
                                                    <div className="text-sm text-gray-600 mt-1">
                                                        {feature.description}
                                                    </div>
                                                </div>
                                            </label>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6 border-t bg-gray-50">
                    <button
                        onClick={handleCancel}
                        disabled={!hasChanges || saving}
                        className={cn(
                            "px-4 py-2 rounded-lg transition-colors",
                            hasChanges
                                ? "text-gray-700 hover:bg-gray-200"
                                : "text-gray-400 cursor-not-allowed"
                        )}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={!hasChanges || saving}
                        className={cn(
                            "flex items-center gap-2 px-6 py-2 rounded-lg transition-colors",
                            hasChanges
                                ? "bg-blue-600 text-white hover:bg-blue-700"
                                : "bg-gray-300 text-gray-500 cursor-not-allowed"
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
                </div>
            </motion.div>
        </div>
    );
}
