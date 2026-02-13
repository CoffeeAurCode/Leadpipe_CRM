/**
 * Canonical complaint status values.
 * 
 * These match the database CHECK constraint and backend validation.
 * DO NOT use raw strings in components - always import STATUS from this file.
 * 
 * Allowed statuses:
 * - STATUS.PENDING: "pending"
 * - STATUS.IN_PROGRESS: "in-progress"
 * - STATUS.RESOLVED: "resolved"
 */
export const STATUS = {
    PENDING: 'pending',
    IN_PROGRESS: 'in-progress',
    RESOLVED: 'resolved'
};

/**
 * Status display configuration for UI components.
 * Maps status values to their visual styling.
 */
export const STATUS_CONFIG = {
    [STATUS.PENDING]: {
        label: 'Pending',
        bg: 'bg-yellow-500/10',
        text: 'text-yellow-400',
        border: 'border-yellow-500/30'
    },
    [STATUS.IN_PROGRESS]: {
        label: 'In Progress',
        bg: 'bg-blue-500/10',
        text: 'text-blue-400',
        border: 'border-blue-500/30'
    },
    [STATUS.RESOLVED]: {
        label: 'Resolved',
        bg: 'bg-green-500/10',
        text: 'text-green-400',
        border: 'border-green-500/30'
    }
};

/**
 * Get all status values as an array.
 * Useful for dropdowns and filters.
 */
export const getAllStatuses = () => Object.values(STATUS);

/**
 * Get status label for display.
 * @param {string} status - Status value
 * @returns {string} Display label
 */
export const getStatusLabel = (status) => {
    return STATUS_CONFIG[status]?.label || status;
};
