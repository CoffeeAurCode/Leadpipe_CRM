import { useState, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Upload, Download, FileText, CheckCircle2, AlertTriangle, XCircle, Loader2, ArrowLeft, Sparkles } from 'lucide-react';
import { cn } from '@/lib';
import { analyzeImportFile, importPropertiesCsv, importTenantsCsv } from '../services/apiService';

// ── Constants ─────────────────────────────────────────────────────────────────

const TEMPLATES = {
    properties: {
        header: 'property_name,property_address,building_name,flat_number,floor_number,bedrooms,bathrooms',
        sample: [
            'Sunrise Towers,12 MG Road,Block A,A101,1,2,1',
            'Sunrise Towers,12 MG Road,Block A,A102,1,3,2',
            'Sunrise Towers,12 MG Road,Block B,B201,2,2,1',
        ],
        filename: 'properties_template.csv',
    },
    tenants: {
        header: 'name,phone,email,flat_number,lease_start_date,lease_end_date,rent_amount,rent_status,manager_notes',
        sample: [
            'Rahul Sharma,+919876543210,rahul@gmail.com,A101,2024-01-01,2025-01-01,15000,On-time,',
            'Priya Patel,+919988776655,priya@gmail.com,B201,2024-06-01,2025-06-01,18000,Upcoming,Pets allowed',
        ],
        filename: 'tenants_template.csv',
    },
};

const COLUMN_OPTIONS = {
    properties: [
        { value: 'property_name', label: 'property_name', required: true },
        { value: 'building_name', label: 'building_name', required: true },
        { value: 'flat_number', label: 'flat_number', required: true },
        { value: 'property_address', label: 'property_address' },
        { value: 'floor_number', label: 'floor_number' },
        { value: 'bedrooms', label: 'bedrooms' },
        { value: 'bathrooms', label: 'bathrooms' },
    ],
    tenants: [
        { value: 'name', label: 'name', required: true },
        { value: 'phone', label: 'phone', required: true },
        { value: 'flat_number', label: 'flat_number', required: true },
        { value: 'email', label: 'email' },
        { value: 'lease_start_date', label: 'lease_start_date' },
        { value: 'lease_end_date', label: 'lease_end_date' },
        { value: 'rent_amount', label: 'rent_amount' },
        { value: 'rent_status', label: 'rent_status' },
        { value: 'manager_notes', label: 'manager_notes' },
    ],
};

const REQUIRED_COLS = {
    properties: new Set(['property_name', 'building_name', 'flat_number']),
    tenants: new Set(['name', 'phone', 'flat_number']),
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function downloadTemplate(type) {
    const t = TEMPLATES[type];
    const content = [t.header, ...t.sample].join('\n');
    const blob = new Blob([content], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = t.filename;
    a.click();
    URL.revokeObjectURL(url);
}

function parseCsvPreview(text) {
    const lines = text.trim().split('\n');
    if (lines.length < 1) return { headers: [], rows: [] };
    const headers = lines[0].split(',').map(h => h.trim());
    const rows = lines.slice(1, 4).map(line => line.split(',').map(v => v.trim()));
    return { headers, rows };
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Tab({ active, onClick, children }) {
    return (
        <button
            onClick={onClick}
            className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                active
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
            )}
        >
            {children}
        </button>
    );
}

function DropZone({ onFile, file }) {
    const { t } = useTranslation();
    const inputRef = useRef(null);
    const [dragging, setDragging] = useState(false);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f && (f.name.endsWith('.csv') || f.name.endsWith('.xlsx'))) onFile(f);
    }, [onFile]);

    const handleChange = (e) => {
        const f = e.target.files[0];
        if (f) onFile(f);
        e.target.value = '';
    };

    return (
        <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={cn(
                'border-2 border-dashed rounded-xl p-8 cursor-pointer transition-colors text-center',
                dragging
                    ? 'border-primary bg-primary/5'
                    : file
                        ? 'border-emerald-500 bg-emerald-500/5'
                        : 'border-border hover:border-primary/50 hover:bg-secondary/50'
            )}
        >
            <input
                ref={inputRef}
                type="file"
                accept=".csv,.xlsx"
                className="hidden"
                onChange={handleChange}
            />
            {file ? (
                <div className="flex flex-col items-center gap-2">
                    <FileText className="w-8 h-8 text-emerald-500" />
                    <p className="text-sm font-medium text-foreground">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB — {t('import.clickToChange')}</p>
                </div>
            ) : (
                <div className="flex flex-col items-center gap-2">
                    <Upload className="w-8 h-8 text-muted-foreground" />
                    <p className="text-sm font-medium text-foreground">{t('import.dropHerePre')} <span className="text-primary">{t('import.browse')}</span></p>
                    <p className="text-xs text-muted-foreground">{t('import.maxSize')}</p>
                </div>
            )}
        </div>
    );
}

function PreviewTable({ headers, rows }) {
    if (!headers.length) return null;
    return (
        <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-xs">
                <thead className="bg-secondary">
                    <tr>
                        {headers.map((h, i) => (
                            <th key={i} className="px-3 py-2 text-left font-semibold text-foreground whitespace-nowrap">
                                {h}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row, ri) => (
                        <tr key={ri} className="border-t border-border">
                            {row.map((cell, ci) => (
                                <td key={ci} className="px-3 py-2 text-muted-foreground truncate max-w-[120px]">
                                    {cell || <span className="italic opacity-40">—</span>}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function ColumnMappingStep({ importType, mapping, onMappingChange, onConfirm, onBack, loading }) {
    const { t } = useTranslation();
    const columns = COLUMN_OPTIONS[importType];
    const required = REQUIRED_COLS[importType];
    const originalHeaders = Object.keys(mapping);

    const mappedTargets = new Set(Object.values(mapping).filter(Boolean));
    const stillUnmapped = [...required].filter(r => !mappedTargets.has(r));

    const handleChange = (header, newTarget) => {
        onMappingChange({ ...mapping, [header]: newTarget || null });
    };

    return (
        <div className="space-y-4">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <Sparkles className="w-4 h-4 flex-shrink-0 text-amber-500 mt-0.5" />
                <p className="text-sm text-amber-700 dark:text-amber-300">
                    {t('import.aiMappingWarning')}
                </p>
            </div>

            {stillUnmapped.length > 0 && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-500">
                    {t('import.requiredNotMapped', { columns: stillUnmapped.join(', ') })}
                </div>
            )}

            <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-sm">
                    <thead className="bg-secondary">
                        <tr>
                            <th className="px-3 py-2 text-left font-semibold text-foreground">{t('import.yourColumn')}</th>
                            <th className="px-3 py-2 text-left font-semibold text-foreground">{t('import.mapsTo')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {originalHeaders.map(header => {
                            const currentTarget = mapping[header];
                            return (
                                <tr key={header} className="border-t border-border">
                                    <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{header}</td>
                                    <td className="px-3 py-2">
                                        <select
                                            value={currentTarget || ''}
                                            onChange={e => handleChange(header, e.target.value)}
                                            className={cn(
                                                'w-full text-xs rounded-md border bg-background px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary',
                                                currentTarget
                                                    ? 'border-emerald-500/50 text-foreground'
                                                    : 'border-border text-muted-foreground'
                                            )}
                                        >
                                            <option value="">{t('import.ignoreColumn')}</option>
                                            {columns.map(col => (
                                                <option key={col.value} value={col.value}>
                                                    {col.label}{col.required ? ' *' : ''}
                                                </option>
                                            ))}
                                        </select>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            <p className="text-xs text-muted-foreground">{t('import.requiredField')}</p>

            <div className="flex items-center justify-between gap-3 pt-1">
                <button
                    onClick={onBack}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-secondary transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    {t('common.back')}
                </button>
                <button
                    onClick={() => onConfirm(mapping)}
                    disabled={stillUnmapped.length > 0 || loading}
                    className={cn(
                        'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors',
                        stillUnmapped.length === 0 && !loading
                            ? 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg shadow-primary/20'
                            : 'bg-secondary text-muted-foreground cursor-not-allowed'
                    )}
                >
                    {loading ? (
                        <><Loader2 className="w-4 h-4 animate-spin" />{t('import.importing')}</>
                    ) : (
                        <><Upload className="w-4 h-4" />{t('import.confirmAndImport')}</>
                    )}
                </button>
            </div>
        </div>
    );
}

function ResultPanel({ result, importType }) {
    const { t } = useTranslation();
    if (!result) return null;

    const isProperties = importType === 'properties';
    const { created, skipped, errors } = result;

    return (
        <div className="space-y-3">
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                {isProperties ? (
                    <div className="space-y-1">
                        {[
                            ['properties', created?.properties],
                            ['buildings', created?.buildings],
                            ['flats', created?.flats],
                        ].map(([label, count]) => (
                            <div key={label} className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                                <span>{count} {label} created</span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                        <span>{created} tenants created</span>
                    </div>
                )}
            </div>

            {skipped?.length > 0 && (
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                    <div className="flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-500 mt-0.5" />
                        <div>
                            <p className="text-sm font-medium text-amber-600 dark:text-amber-400">{t('import.rowsSkipped', { count: skipped.length })}</p>
                            <ul className="mt-1 space-y-0.5">
                                {skipped.map((s, i) => (
                                    <li key={i} className="text-xs text-muted-foreground">{s}</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            )}

            {errors?.length > 0 && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                    <div className="flex items-start gap-2">
                        <XCircle className="w-4 h-4 flex-shrink-0 text-red-500 mt-0.5" />
                        <div>
                            <p className="text-sm font-medium text-red-500">{t('import.errorsFound', { count: errors.length })}</p>
                            <ul className="mt-1 space-y-0.5">
                                {errors.map((e, i) => (
                                    <li key={i} className="text-xs text-muted-foreground">{e}</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function FlatNumberWarningStep({ affected, onConfirm, onBack, loading }) {
    return (
        <div className="space-y-4">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-500 mt-0.5" />
                <div className="text-sm text-amber-700 dark:text-amber-300">
                    <p className="font-semibold">Unit names with special characters detected</p>
                    <p className="mt-0.5">Unit names may only contain letters and numbers — no hyphens, spaces, or symbols. The units below will be renamed if you choose to strip them. Otherwise, cancel and fix your file.</p>
                </div>
            </div>

            <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-sm">
                    <thead className="bg-secondary">
                        <tr>
                            <th className="px-3 py-2 text-left font-semibold text-foreground">Original in file</th>
                            <th className="px-3 py-2 text-left font-semibold text-foreground">Will be stored as</th>
                        </tr>
                    </thead>
                    <tbody>
                        {affected.map((item, i) => (
                            <tr key={i} className="border-t border-border">
                                <td className="px-3 py-2 font-mono text-xs text-red-500">{item.original}</td>
                                <td className="px-3 py-2 font-mono text-xs text-emerald-500">{item.sanitized || <span className="italic text-muted-foreground">empty — row will be skipped</span>}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="flex items-center justify-between gap-3 pt-1">
                <button
                    onClick={onBack}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-secondary transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Cancel
                </button>
                <button
                    onClick={onConfirm}
                    disabled={loading}
                    className={cn(
                        'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors',
                        !loading
                            ? 'bg-amber-500 text-white hover:bg-amber-600 shadow-lg shadow-amber-500/20'
                            : 'bg-secondary text-muted-foreground cursor-not-allowed'
                    )}
                >
                    {loading ? (
                        <><Loader2 className="w-4 h-4 animate-spin" />Importing...</>
                    ) : (
                        'Strip & Import'
                    )}
                </button>
            </div>
        </div>
    );
}

// ── Main Modal ────────────────────────────────────────────────────────────────

export default function CsvImportModal({ isOpen, onClose, defaultTab = 'properties', onSuccess }) {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState(defaultTab);
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [rowCount, setRowCount] = useState(0);
    const [analyzing, setAnalyzing] = useState(false);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [apiError, setApiError] = useState(null);

    // Mapping step state
    const [mappingStep, setMappingStep] = useState(false);
    const [mapping, setMapping] = useState(null);

    // Flat number warning step state
    const [flatWarning, setFlatWarning] = useState(null);
    const [pendingMapping, setPendingMapping] = useState(null);

    const resetState = () => {
        setFile(null);
        setPreview(null);
        setRowCount(0);
        setResult(null);
        setApiError(null);
        setMappingStep(false);
        setMapping(null);
        setAnalyzing(false);
        setFlatWarning(null);
        setPendingMapping(null);
    };

    const handleTabChange = (tab) => {
        setActiveTab(tab);
        resetState();
    };

    const handleFile = (f) => {
        setFile(f);
        setResult(null);
        setApiError(null);
        setMappingStep(false);
        setMapping(null);
        setFlatWarning(null);
        setPendingMapping(null);

        if (f.name.toLowerCase().endsWith('.xlsx')) {
            setPreview(null);
            setRowCount(0);
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const lines = text.trim().split('\n');
            setRowCount(Math.max(0, lines.length - 1));
            setPreview(parseCsvPreview(text));
        };
        reader.readAsText(f);
    };

    const doImport = async (columnMapping, sanitize = false) => {
        setLoading(true);
        setResult(null);
        setApiError(null);
        try {
            const data = activeTab === 'properties'
                ? await importPropertiesCsv(file, columnMapping, sanitize)
                : await importTenantsCsv(file, columnMapping, sanitize);

            if (data.flat_number_warning) {
                setPendingMapping(columnMapping);
                setFlatWarning(data.affected);
                setMappingStep(false);
            } else {
                setResult(data);
                setMappingStep(false);
                setFlatWarning(null);
                setPendingMapping(null);
                onSuccess?.();
            }
        } catch (err) {
            setApiError(err.message || 'Import failed');
        } finally {
            setLoading(false);
        }
    };

    const handleAnalyzeAndImport = async () => {
        if (!file) return;
        setAnalyzing(true);
        setApiError(null);
        try {
            const analysis = await analyzeImportFile(file, activeTab);
            if (!analysis.needs_mapping) {
                setAnalyzing(false);
                await doImport(null);
            } else {
                setMapping(analysis.mapping);
                setMappingStep(true);
                setAnalyzing(false);
            }
        } catch (err) {
            setApiError(err.message || 'Analysis failed');
            setAnalyzing(false);
        }
    };

    const handleClose = () => {
        resetState();
        onClose();
    };

    if (!isOpen) return null;

    const isXlsx = file?.name?.toLowerCase().endsWith('.xlsx');
    const busy = analyzing || loading;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] flex flex-col">

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-border flex-shrink-0">
                    <h2 className="text-lg font-semibold text-foreground">{t('import.modalTitle')}</h2>
                    <button onClick={handleClose} className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

                    {/* Tabs — hidden during mapping or warning step */}
                    {!mappingStep && !flatWarning && (
                        <div className="flex gap-2">
                            <Tab active={activeTab === 'properties'} onClick={() => handleTabChange('properties')}>
                                {t('import.propertiesTab')}
                            </Tab>
                            <Tab active={activeTab === 'tenants'} onClick={() => handleTabChange('tenants')}>
                                {t('import.tenantsTab')}
                            </Tab>
                        </div>
                    )}

                    {flatWarning ? (
                        <FlatNumberWarningStep
                            affected={flatWarning}
                            onConfirm={() => doImport(pendingMapping, true)}
                            onBack={() => setFlatWarning(null)}
                            loading={loading}
                        />
                    ) : mappingStep ? (
                        <ColumnMappingStep
                            importType={activeTab}
                            mapping={mapping}
                            onMappingChange={setMapping}
                            onConfirm={doImport}
                            onBack={() => setMappingStep(false)}
                            loading={loading}
                        />
                    ) : (
                        <>
                            {/* Description */}
                            <p className="text-sm text-muted-foreground">
                                {activeTab === 'properties' ? t('import.propertiesDesc') : t('import.tenantsDesc')}
                            </p>

                            {/* Drop zone */}
                            <DropZone onFile={handleFile} file={file} />

                            {/* Excel notice */}
                            {isXlsx && (
                                <p className="text-xs text-muted-foreground text-center">
                                    {t('import.excelNotice')}
                                </p>
                            )}

                            {/* CSV Preview */}
                            {preview && preview.headers.length > 0 && (
                                <div className="space-y-2">
                                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                        {t('import.previewLabel', { count: rowCount })}
                                    </p>
                                    <PreviewTable headers={preview.headers} rows={preview.rows} />
                                </div>
                            )}

                            {/* Result */}
                            {result && <ResultPanel result={result} importType={activeTab} />}

                            {/* API Error */}
                            {apiError && (
                                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-500">
                                    {apiError}
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Footer — hidden during mapping/warning steps (they have their own actions) */}
                {!mappingStep && !flatWarning && (
                    <div className="flex items-center justify-between px-6 py-4 border-t border-border flex-shrink-0 gap-3">
                        <button
                            onClick={() => downloadTemplate(activeTab)}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                        >
                            <Download className="w-4 h-4" />
                            {t('import.downloadTemplate')}
                        </button>

                        <div className="flex items-center gap-2">
                            <button
                                onClick={handleClose}
                                className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:bg-secondary transition-colors"
                            >
                                {result ? t('import.close') : t('import.cancel')}
                            </button>
                            {!result && (
                                <button
                                    onClick={handleAnalyzeAndImport}
                                    disabled={!file || busy}
                                    className={cn(
                                        'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors',
                                        file && !busy
                                            ? 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg shadow-primary/20'
                                            : 'bg-secondary text-muted-foreground cursor-not-allowed'
                                    )}
                                >
                                    {analyzing ? (
                                        <><Loader2 className="w-4 h-4 animate-spin" />{t('import.analyzing')}</>
                                    ) : loading ? (
                                        <><Loader2 className="w-4 h-4 animate-spin" />{t('import.importing')}</>
                                    ) : rowCount > 0 ? (
                                        <><Upload className="w-4 h-4" />{t('import.importWithRows', { count: rowCount })}</>
                                    ) : (
                                        <><Upload className="w-4 h-4" />{t('import.confirm')}</>
                                    )}
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
