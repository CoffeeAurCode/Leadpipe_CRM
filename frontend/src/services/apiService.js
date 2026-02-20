// Use environment variable for API URL, fallback to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
import { format } from 'date-fns';

/**
 * API Service for Tenant Management Backend
 * Handles all HTTP requests to FastAPI backend
 */

// Fetch all complaints
export async function fetchComplaints() {
    try {
        const response = await fetch(`${API_BASE_URL}/complaints`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching complaints:', error);
        throw error;
    }
}

// Fetch single complaint by ID
export async function fetchComplaintById(id) {
    try {
        const response = await fetch(`${API_BASE_URL}/complaints/${id}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error fetching complaint ${id}:`, error);
        throw error;
    }
}

// Update complaint (PATCH)
export async function updateComplaint(id, updates) {
    try {
        const response = await fetch(`${API_BASE_URL}/complaints/${id}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updates),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error updating complaint ${id}:`, error);
        throw error;
    }
}

// Create new complaint
export async function createComplaint(complaintData) {
    try {
        const response = await fetch(`${API_BASE_URL}/complaints`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(complaintData),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error creating complaint:', error);
        throw error;
    }
}

// Helper: Map status to display text
import { STATUS, STATUS_CONFIG } from '../constants/status';

export function getStatusDisplay(status) {
    return STATUS_CONFIG[status]?.label || status;
}

// Helper: Map priority to display
export function getPriorityDisplay(priority) {
    const priorityMap = {
        'high': 'High',
        'medium': 'Medium',
        'low': 'Low'
    };
    return priorityMap[priority] || priority;
}

// Helper: Format date with manual IST conversion
export function formatDate(dateString) {
    console.log('formatDate called with:', dateString);
    if (!dateString) return 'N/A';

    try {
        // Ensure the string has 'Z' suffix to explicitly mark it as UTC
        const utcString = dateString.endsWith('Z') ? dateString : dateString + 'Z';

        // Parse as UTC
        const utcDate = new Date(utcString);

        // Manually add IST offset: +5 hours 30 minutes (330 minutes = 19800000 milliseconds)
        const istDate = new Date(utcDate.getTime() + (5.5 * 60 * 60 * 1000));

        // Format the IST time
        return format(istDate, 'MMM d, yyyy h:mm a');
    } catch (error) {
        console.error('Error formatting date:', error);
        return dateString;
    }
}

// Fetch all properties
export async function fetchProperties() {
    try {
        const response = await fetch(`${API_BASE_URL}/properties`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching properties:', error);
        throw error;
    }
}

// Fetch detailed flat information including tenant data
export async function fetchFlatDetails(flatUuid) {
    try {
        const response = await fetch(`${API_BASE_URL}/flats/${flatUuid}/details`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error fetching flat details for ${flatUuid}:`, error);
        throw error;
    }
}

// Update flat details and tenant (PATCH)
export async function updateFlat(flatUuid, updateData) {
    try {
        const response = await fetch(`${API_BASE_URL}/flats/${flatUuid}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updateData),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error updating flat ${flatUuid}:`, error);
        throw error;
    }
}

// Create a new property with optional image and tenant
export async function createProperty(formData) {
    try {
        // FormData is sent as-is (multipart/form-data)
        // Do NOT set Content-Type header - browser will set it with boundary
        const response = await fetch(`${API_BASE_URL}/flats`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error creating property:', error);
        throw error;
    }
}

// ==================== SETTINGS API ====================

/**
 * Fetch feature settings for a property
 * @param {string} propertyUuid - UUID of the property
 * @returns {Promise<Object>} - Feature settings object
 */
export async function fetchPropertySettings(propertyUuid) {
    try {
        const response = await fetch(`${API_BASE_URL}/properties/${propertyUuid}/settings`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching property settings:', error);
        throw error;
    }
}

/**
 * Update feature settings for a property
 * @param {string} propertyUuid - UUID of the property
 * @param {Object} features - Object mapping feature keys to boolean values
 * @returns {Promise<Object>} - Updated settings
 */
export async function updatePropertySettings(propertyUuid, features) {
    try {
        const response = await fetch(`${API_BASE_URL}/properties/${propertyUuid}/settings`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ features }),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error updating property settings:', error);
        throw error;
    }
}

// ==================== RENT API ====================

export async function fetchActiveRent(flatUuid) {
    try {
        const response = await fetch(`${API_BASE_URL}/rents/${flatUuid}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        return data.rent; // null if not set
    } catch (error) {
        console.error('Error fetching rent:', error);
        return null;
    }
}

export async function setRent(flatUuid, monthlyRent, effectiveFrom) {
    const response = await fetch(`${API_BASE_URL}/rents/set`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            flat_uuid: flatUuid,
            monthly_rent: monthlyRent,
            effective_from: effectiveFrom,
        }),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

// ── Property Types ────────────────────────────────────────────────────────────

export async function fetchPropertyTypes() {
    const response = await fetch(`${API_BASE_URL}/property-types`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

// ── Buildings ─────────────────────────────────────────────────────────────────

/** Fetch all buildings (with unit counts aggregated server-side). */
export async function fetchBuildings() {
    const response = await fetch(`${API_BASE_URL}/buildings`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

/** Fetch all units (flats) belonging to a specific building. */
export async function fetchBuildingUnits(buildingId) {
    const response = await fetch(`${API_BASE_URL}/buildings/${buildingId}/units`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

/** Create a new building. */
export async function createBuilding(payload) {
    const response = await fetch(`${API_BASE_URL}/buildings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

/** Update a building's details. */
export async function updateBuilding(buildingId, payload) {
    const response = await fetch(`${API_BASE_URL}/buildings/${buildingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

// ── Property Groups ───────────────────────────────────────────────────────────

/** Fetch all top-level property groups. */
export async function fetchPropertyGroups() {
    const response = await fetch(`${API_BASE_URL}/property-groups`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

/** Create a new property group. */
export async function createPropertyGroup(payload) {
    const response = await fetch(`${API_BASE_URL}/property-groups`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

/** Fetch all buildings belonging to a specific property group. */
export async function fetchPropertyBuildings(propertyId) {
    const response = await fetch(`${API_BASE_URL}/property-groups/${propertyId}/buildings`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}
