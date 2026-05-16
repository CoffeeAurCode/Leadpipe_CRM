/**
 * Section 5.6 — ComplaintModal.jsx
 * Note: ComplaintModal in this codebase is a Detail/View modal, not a create form.
 * Tests cover the detail view behaviour described in TEST_PLAN.md Section 5.6.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ComplaintModal from '../components/ComplaintModal';

const BASE_COMPLAINT = {
    id: 42,
    status: 'pending',
    priority: 'high',
    description: 'Ceiling fan is broken',
    flat_number: 'A-101',
    tenant_name: 'Ravi Kumar',
    created_at: '2026-01-15T10:00:00',
};

function renderModal(overrides = {}) {
    const onClose = vi.fn();
    const onUpdate = vi.fn();
    const complaint = { ...BASE_COMPLAINT, ...overrides };

    const result = render(
        <ComplaintModal complaint={complaint} onClose={onClose} onUpdate={onUpdate} />
    );
    return { ...result, onClose, onUpdate };
}

describe('ComplaintModal', () => {
    it('renders complaint ID', () => {
        renderModal();
        expect(screen.getByText(/#42/)).toBeInTheDocument();
    });

    it('renders complaint description', () => {
        renderModal();
        expect(screen.getByText('Ceiling fan is broken')).toBeInTheDocument();
    });

    it('renders tenant name', () => {
        renderModal();
        expect(screen.getByText('Ravi Kumar')).toBeInTheDocument();
    });

    it('renders flat number as location', () => {
        renderModal();
        expect(screen.getByText('A-101')).toBeInTheDocument();
    });

    it('renders formatted created_at date', () => {
        renderModal();
        // Should contain "Jan" and "2026" from the formatted date
        expect(screen.getByText(/Jan.*2026|2026.*Jan/i)).toBeInTheDocument();
    });

    it('calls onClose when Close button is clicked', () => {
        const { onClose } = renderModal();
        fireEvent.click(screen.getByRole('button', { name: /close/i }));
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when backdrop is clicked', () => {
        const { onClose } = renderModal();
        // The backdrop is the outermost div
        const backdrop = screen.getByText('Complaint Details').closest('.fixed');
        fireEvent.click(backdrop);
        expect(onClose).toHaveBeenCalled();
    });

    it('does not propagate click from inner modal to backdrop', () => {
        const { onClose } = renderModal();
        // Clicking the modal card itself should NOT close
        const card = screen.getByText('Complaint Details').closest('.bg-card');
        fireEvent.click(card);
        expect(onClose).not.toHaveBeenCalled();
    });

    it('does not render tenant section when tenant_name is absent', () => {
        renderModal({ tenant_name: null });
        expect(screen.queryByText('Tenant')).not.toBeInTheDocument();
    });

    it('shows summary when complaint.summary is present', () => {
        renderModal({ summary: 'Water leak summary' });
        expect(screen.getByText('Water leak summary')).toBeInTheDocument();
    });
});
