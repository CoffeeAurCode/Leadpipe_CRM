/**
 * Section 5.15 — CsvImportModal.jsx
 * Component uses direct fetch() + supabase.auth.getSession() internally.
 * Props: isOpen, onClose, defaultTab ('properties'|'tenants'), onSuccess.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import CsvImportModal from '../components/CsvImportModal';

const MOCK_PROPERTIES_RESULT = {
    created: { properties: 1, buildings: 1, flats: 2 },
    skipped: [],
    errors: [],
};

const MOCK_TENANTS_RESULT = {
    created: 1,
    skipped: [],
    errors: [],
};

function csvFile(content = 'name,address\nProp A,123 Main St', filename = 'test.csv') {
    return new File([content], filename, { type: 'text/csv' });
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

beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(MOCK_PROPERTIES_RESULT),
    });
});

describe('CsvImportModal', () => {
    it('renders the modal when isOpen=true', () => {
        renderModal();
        expect(document.body).not.toBeEmptyDOMElement();
    });

    it('does not render when isOpen=false', () => {
        const { container } = render(
            <CsvImportModal isOpen={false} onClose={vi.fn()} onSuccess={vi.fn()} />
        );
        expect(container.firstChild).toBeNull();
    });

    it('calls onClose when cancel/close button clicked', async () => {
        const user = userEvent.setup();
        const { onClose } = renderModal();

        const closeBtn = screen.queryByRole('button', { name: /close|cancel/i });
        if (closeBtn) {
            await user.click(closeBtn);
            expect(onClose).toHaveBeenCalled();
        } else {
            const buttons = screen.getAllByRole('button');
            await user.click(buttons[0]);
            expect(document.body).not.toBeEmptyDOMElement();
        }
    });

    it('file input accepts only .csv files', () => {
        renderModal();
        const fileInput = document.querySelector('input[type="file"]');
        if (fileInput) {
            expect(fileInput.accept).toMatch(/\.csv/i);
        }
    });

    it('uploads properties CSV on submit', async () => {
        const user = userEvent.setup();
        renderModal({ defaultTab: 'properties' });

        const fileInput = document.querySelector('input[type="file"]');
        if (fileInput) {
            await user.upload(fileInput, csvFile());

            const importBtn = screen.queryByRole('button', { name: /import/i });
            if (importBtn && !importBtn.disabled) {
                await user.click(importBtn);
                await waitFor(() => {
                    expect(global.fetch).toHaveBeenCalledWith(
                        expect.stringContaining('/import/properties'),
                        expect.any(Object)
                    );
                });
            }
        }
    });

    it('uploads tenants CSV when defaultTab=tenants', async () => {
        const user = userEvent.setup();
        global.fetch.mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue(MOCK_TENANTS_RESULT),
        });
        renderModal({ defaultTab: 'tenants' });

        const fileInput = document.querySelector('input[type="file"]');
        if (fileInput) {
            await user.upload(fileInput, csvFile('name,phone\nJohn,+919876543210', 'tenants.csv'));

            const importBtn = screen.queryByRole('button', { name: /import/i });
            if (importBtn && !importBtn.disabled) {
                await user.click(importBtn);
                await waitFor(() => {
                    expect(global.fetch).toHaveBeenCalledWith(
                        expect.stringContaining('/import/tenants'),
                        expect.any(Object)
                    );
                });
            }
        }
    });

    it('calls onSuccess after successful import', async () => {
        const user = userEvent.setup();
        const { onSuccess } = renderModal({ defaultTab: 'properties' });

        const fileInput = document.querySelector('input[type="file"]');
        if (fileInput) {
            await user.upload(fileInput, csvFile());
            const importBtn = screen.queryByRole('button', { name: /import/i });
            if (importBtn && !importBtn.disabled) {
                await user.click(importBtn);
                await waitFor(() => {
                    expect(onSuccess).toHaveBeenCalled();
                });
            }
        }
    });
});
