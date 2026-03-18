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

// ============================================================
// APPOINTMENT-SPECIFIC STATUS CONSTANTS
// ============================================================

/**
 * Canonical appointment status values.
 * These match the appointments table in Supabase.
 */
export const APPOINTMENT_STATUS = {
    SCHEDULED: 'scheduled',
    CANCELLED: 'cancelled',
    ATTENDED: 'attended',
    DONE: 'completed',   // DB stores 'completed'; UI displays 'Done'
};

/**
 * Appointment status display configuration.
 */
export const APPOINTMENT_STATUS_CONFIG = {
    [APPOINTMENT_STATUS.SCHEDULED]: {
        label: 'Scheduled',
        bg: 'bg-blue-500/10',
        text: 'text-blue-400',
        border: 'border-blue-500/30',
    },
    [APPOINTMENT_STATUS.CANCELLED]: {
        label: 'Cancelled',
        bg: 'bg-red-500/10',
        text: 'text-red-400',
        border: 'border-red-500/30',
    },
    [APPOINTMENT_STATUS.ATTENDED]: {
        label: 'Attended',
        bg: 'bg-purple-500/10',
        text: 'text-purple-400',
        border: 'border-purple-500/30',
    },
    [APPOINTMENT_STATUS.DONE]: {
        label: 'Done',
        bg: 'bg-green-500/10',
        text: 'text-green-400',
        border: 'border-green-500/30',
    },
};

/**
 * Returns appointment status config with graceful fallback.
 * Handles legacy 'completed' value from VAPI.
 */
export const getAppointmentStatusConfig = (status) => {
    return APPOINTMENT_STATUS_CONFIG[status] || {
        label: status ? (status.charAt(0).toUpperCase() + status.slice(1)) : 'Unknown',
        bg: 'bg-gray-500/10',
        text: 'text-gray-400',
        border: 'border-gray-500/30',
    };
};

