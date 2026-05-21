/**
 * Tests for CsvImportModal — smart CSV/XLSX import with AI column mapping.
 *
 * All HTTP calls go through apiService.js (mocked here). The modal has two
 * main flows:
 *   1. analyzeImportFile → needs_mapping:false → direct import
 *   2. analyzeImportFile → needs_mapping:true  → ColumnMappingStep shown
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import CsvImportModal from '../components/CsvImportModal';

// ── Mock apiService ────────────────────────────────────────────────────────────

vi.mock('../services/apiService', () => ({
    analyzeImportFile: vi.fn(),
    importPropertiesCsv: vi.fn(),
    importTenantsCsv: vi.fn(),
}));

import { analyzeImportFile, importPropertiesCsv, importTenantsCsv } from '../services/apiService';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PROPERTIES_RESULT = {
    created: { properties: 1, buildings: 1, flats: 2 },
    skipped: [],
    errors: [],
};

const TENANTS_RESULT = {
    created: 2,
    skipped: [],
    errors: [],
};

const ANALYZE_NO_MAPPING = { needs_mapping: false, row_count: 2 };

const ANALYZE_WITH_MAPPING = {
    needs_mapping: true,
    mapping: {
        'tenant name': 'name',
        mobile: 'phone',
        'unit no': 'flat_number',
        notes: null,
    },
    unmapped_required: [],
    row_count: 3,
};

function csvFile(content = 'property_name,building_name,flat_number\nSunrise,Block A,A-101', name = 'test.csv') {
    return new File([content], name, { type: 'text/csv' });
}

function xlsxFile(name = 'data.xlsx') {
    return new File(['binary'], name, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}

function renderModal(props = {}) {
    const onClose = vi.fn();
    const onSuccess = vi.fn();
    const result = render(
        <CsvImportModal
            isOpen={true}
            onClose={onClose}
            onSuccess={onSuccess}
            defaultTab="properties"
            {...props}
        />
    );
    return { ...result, onClose, onSuccess };
}

async function uploadFile(file) {
    const input = document.querySelector('input[type="file"]');
    await userEvent.upload(input, file);
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
    vi.clearAllMocks();
    analyzeImportFile.mockResolvedValue(ANALYZE_NO_MAPPING);
    importPropertiesCsv.mockResolvedValue(PROPERTIES_RESULT);
    importTenantsCsv.mockResolvedValue(TENANTS_RESULT);
});

// ── Basic rendering ───────────────────────────────────────────────────────────

describe('CsvImportModal — rendering', () => {
    it('renders when isOpen=true', () => {
        renderModal();
        expect(screen.getByText(/import from csv or excel/i)).toBeInTheDocument();
    });

    it('does not render when isOpen=false', () => {
        const { container } = render(
            <CsvImportModal isOpen={false} onClose={vi.fn()} onSuccess={vi.fn()} />
        );
        expect(container.firstChild).toBeNull();
    });

    it('shows Properties and Tenants tabs', () => {
        renderModal();
        expect(screen.getByRole('button', { name: /^properties$/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /^tenants$/i })).toBeInTheDocument();
    });

    it('calls onClose when X button clicked', async () => {
        const user = userEvent.setup();
        const { onClose } = renderModal();
        // X button is the close icon button in the header
        const buttons = screen.getAllByRole('button');
        const closeBtn = buttons.find(b => b.querySelector('svg'));
        if (closeBtn) await user.click(closeBtn);
        // fallback: Cancel button
        else {
            const cancelBtn = screen.getByRole('button', { name: /cancel/i });
            await user.click(cancelBtn);
        }
        expect(onClose).toHaveBeenCalled();
    });

    it('calls onClose when Cancel button clicked', async () => {
        const user = userEvent.setup();
        const { onClose } = renderModal();
        await user.click(screen.getByRole('button', { name: /cancel/i }));
        expect(onClose).toHaveBeenCalled();
    });
});

// ── File input ────────────────────────────────────────────────────────────────

describe('CsvImportModal — file input', () => {
    it('file input accepts .csv and .xlsx', () => {
        renderModal();
        const input = document.querySelector('input[type="file"]');
        expect(input).not.toBeNull();
        expect(input.accept).toMatch(/\.csv/);
        expect(input.accept).toMatch(/\.xlsx/);
    });

    it('shows file name after CSV upload', async () => {
        renderModal();
        await uploadFile(csvFile());
        expect(screen.getByText('test.csv')).toBeInTheDocument();
    });

    it('shows Excel notice and no preview for .xlsx files', async () => {
        renderModal();
        await uploadFile(xlsxFile());
        expect(screen.getByText(/excel file detected/i)).toBeInTheDocument();
        expect(screen.queryByText(/preview — first 3 rows/i)).toBeNull();
    });

    it('shows CSV preview after CSV upload', async () => {
        renderModal();
        await uploadFile(csvFile());
        await waitFor(() => {
            expect(screen.getByText(/preview — first 3 rows/i)).toBeInTheDocument();
        });
    });
});

// ── Flow A: needs_mapping = false → direct import ─────────────────────────────

describe('CsvImportModal — direct import flow (no mapping needed)', () => {
    it('calls analyzeImportFile on import click', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'properties' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => expect(analyzeImportFile).toHaveBeenCalledWith(
            expect.any(File), 'properties'
        ));
    });

    it('calls importPropertiesCsv without mapping when columns match', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'properties' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => expect(importPropertiesCsv).toHaveBeenCalledWith(
            expect.any(File), null
        ));
    });

    it('calls importTenantsCsv for tenants tab', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'tenants' });
        await uploadFile(csvFile('name,phone,flat_number\nRahul,+91987,A-101', 'tenants.csv'));
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => expect(importTenantsCsv).toHaveBeenCalledWith(
            expect.any(File), null
        ));
    });

    it('shows result panel after successful import', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'properties' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => {
            expect(screen.getByText(/1 properties created/i)).toBeInTheDocument();
        });
    });

    it('calls onSuccess after successful import', async () => {
        const user = userEvent.setup();
        const { onSuccess } = renderModal({ defaultTab: 'properties' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    });

    it('shows error panel when importPropertiesCsv rejects', async () => {
        importPropertiesCsv.mockRejectedValue(new Error('Server error 500'));
        const user = userEvent.setup();
        renderModal({ defaultTab: 'properties' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => {
            expect(screen.getByText(/server error 500/i)).toBeInTheDocument();
        });
    });

    it('shows error panel when analyzeImportFile rejects', async () => {
        analyzeImportFile.mockRejectedValue(new Error('Cannot parse file'));
        const user = userEvent.setup();
        renderModal();
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => {
            expect(screen.getByText(/cannot parse file/i)).toBeInTheDocument();
        });
    });
});

// ── Flow B: needs_mapping = true → mapping step ───────────────────────────────

describe('CsvImportModal — AI mapping flow', () => {
    beforeEach(() => {
        analyzeImportFile.mockResolvedValue(ANALYZE_WITH_MAPPING);
    });

    it('shows ColumnMappingStep when needs_mapping is true', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'tenants' });
        await uploadFile(csvFile('tenant name,mobile,unit no\nRahul,+91987,A-101', 'custom.csv'));
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => {
            expect(screen.getByText(/ai has suggested a mapping/i)).toBeInTheDocument();
        });
    });

    it('mapping table shows original column headers', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'tenants' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => {
            expect(screen.getByText('tenant name')).toBeInTheDocument();
            expect(screen.getByText('mobile')).toBeInTheDocument();
            expect(screen.getByText('unit no')).toBeInTheDocument();
        });
    });

    it('AI-suggested mappings are pre-selected in dropdowns', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'tenants' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => {
            const selects = screen.getAllByRole('combobox');
            const values = selects.map(s => s.value);
            expect(values).toContain('name');
            expect(values).toContain('phone');
            expect(values).toContain('flat_number');
        });
    });

    it('Confirm & Import button calls importTenantsCsv with column_mapping', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'tenants' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => screen.getByText(/ai has suggested a mapping/i));
        await user.click(screen.getByRole('button', { name: /confirm & import/i }));
        await waitFor(() => {
            expect(importTenantsCsv).toHaveBeenCalledWith(
                expect.any(File),
                expect.objectContaining({ 'tenant name': 'name', mobile: 'phone', 'unit no': 'flat_number' })
            );
        });
    });

    it('Back button returns to upload screen', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'tenants' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => screen.getByText(/ai has suggested a mapping/i));
        await user.click(screen.getByRole('button', { name: /back/i }));
        await waitFor(() => {
            expect(screen.queryByText(/ai has suggested a mapping/i)).toBeNull();
            expect(screen.getByText(/properties/i)).toBeInTheDocument();
        });
    });

    it('unmapped required columns block Confirm & Import', async () => {
        analyzeImportFile.mockResolvedValue({
            needs_mapping: true,
            mapping: { somecol: null, anothercol: null },
            unmapped_required: ['name', 'phone', 'flat_number'],
            row_count: 1,
        });
        const user = userEvent.setup();
        renderModal({ defaultTab: 'tenants' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => screen.getByText(/required columns not yet mapped/i));
        const confirmBtn = screen.getByRole('button', { name: /confirm & import/i });
        expect(confirmBtn).toBeDisabled();
    });

    it('shows result panel after successful mapped import', async () => {
        importTenantsCsv.mockResolvedValue(TENANTS_RESULT);
        const user = userEvent.setup();
        renderModal({ defaultTab: 'tenants' });
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => screen.getByText(/ai has suggested a mapping/i));
        await user.click(screen.getByRole('button', { name: /confirm & import/i }));
        await waitFor(() => {
            expect(screen.getByText(/2 tenants created/i)).toBeInTheDocument();
        });
    });
});

// ── Result panel ──────────────────────────────────────────────────────────────

describe('CsvImportModal — result panel', () => {
    it('shows skipped rows in amber panel', async () => {
        importPropertiesCsv.mockResolvedValue({
            created: { properties: 0, buildings: 0, flats: 0 },
            skipped: ['Row 2: flat A-101 already exists'],
            errors: [],
        });
        const user = userEvent.setup();
        renderModal();
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => {
            expect(screen.getByText(/1 row skipped/i)).toBeInTheDocument();
            expect(screen.getByText(/A-101 already exists/i)).toBeInTheDocument();
        });
    });

    it('shows error rows in red panel', async () => {
        importPropertiesCsv.mockResolvedValue({
            created: { properties: 0, buildings: 0, flats: 0 },
            skipped: [],
            errors: ['Row 3: missing required value'],
        });
        const user = userEvent.setup();
        renderModal();
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => {
            expect(screen.getByText(/1 error/i)).toBeInTheDocument();
            expect(screen.getByText(/missing required value/i)).toBeInTheDocument();
        });
    });
});

// ── Tab switching ─────────────────────────────────────────────────────────────

describe('CsvImportModal — tab switching', () => {
    it('switching tabs resets file and result state', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'properties' });

        // Upload a file and run import
        await uploadFile(csvFile());
        await user.click(screen.getByRole('button', { name: /import/i }));
        await waitFor(() => screen.getByText(/1 properties created/i));

        // Switch tab — result should clear
        await user.click(screen.getByRole('button', { name: /^tenants$/i }));
        expect(screen.queryByText(/properties created/i)).toBeNull();
        expect(screen.queryByText('test.csv')).toBeNull();
    });
});
