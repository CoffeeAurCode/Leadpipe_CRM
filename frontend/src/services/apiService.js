// Use environment variable for API URL, fallback to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
import { format } from 'date-fns';

/**
 * API Service for Tenant Management Backend
 * Handles all HTTP requests to FastAPI backend
 */

// Fetch all flats
export async function fetchFlats() {
    try {
        const response = await fetch(`${API_BASE_URL}/flats`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching all flats:', error);
        throw error;
    }
}

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
 * Fetch feature settings for a property (optionally scoped to building/unit).
 * @param {string} propertyUuid
 * @param {Object} [scope] - Optional: { building_id, unit_id }
 */
export async function fetchPropertySettings(propertyUuid, scope = {}) {
    try {
        const params = new URLSearchParams();
        if (scope.building_id != null) params.set('building_id', scope.building_id);
        if (scope.unit_id != null) params.set('unit_id', scope.unit_id);
        const qs = params.toString() ? `?${params}` : '';
        const response = await fetch(`${API_BASE_URL}/properties/${propertyUuid}/settings${qs}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Error fetching property settings:', error);
        throw error;
    }
}

/**
 * Update feature settings at the given scope.
 * @param {string} propertyUuid
 * @param {Object} features  - { featureKey: bool, ... }
 * @param {Object} [scope]   - Optional: { building_id, unit_id, replace_overrides }
 */
export async function updatePropertySettings(propertyUuid, features, scope = {}) {
    try {
        const body = {
            features,
            building_id: scope.building_id ?? null,
            unit_id: scope.unit_id ?? null,
            replace_overrides: scope.replace_overrides ?? false,
        };
        const response = await fetch(`${API_BASE_URL}/properties/${propertyUuid}/settings`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Error updating property settings:', error);
        throw error;
    }
}

// ==================== TENANTS API ====================

/** Fetch all tenants with optional filtering and sorting. */
export async function fetchTenants(params = {}) {
    try {
        const query = new URLSearchParams();
        if (params.rent_status)  query.set('rent_status',  params.rent_status);
        if (params.lease_status) query.set('lease_status', params.lease_status);
        if (params.sort_by)      query.set('sort_by',      params.sort_by);
        if (params.sort_order)   query.set('sort_order',   params.sort_order);
        if (params.building_id != null) query.set('building_id', params.building_id);
        if (params.property_id != null) query.set('property_id', params.property_id);
        if (params.unit_uuid)    query.set('unit_uuid',    params.unit_uuid);
        const qs = query.toString() ? `?${query}` : '';
        const response = await fetch(`${API_BASE_URL}/tenants${qs}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Error fetching tenants:', error);
        throw error;
    }
}

/** Update a tenant's fields (PATCH). */
export async function updateTenant(tenantUuid, updates) {
    try {
        const response = await fetch(`${API_BASE_URL}/tenants/${tenantUuid}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error updating tenant ${tenantUuid}:`, error);
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

// ── Settings (Building & Unit scope) ─────────────────────────────────────────

/** Fetch aggregate settings for a building (majority-vote across its units). */
export async function fetchBuildingSettings(propertyUuid, buildingId) {
    const response = await fetch(`${API_BASE_URL}/properties/${propertyUuid}/settings/building/${buildingId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

/** Fetch settings for one specific unit. */
export async function fetchUnitSettings(unitId) {
    const response = await fetch(`${API_BASE_URL}/units/${unitId}/settings`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

/** Bulk-apply feature toggles to ALL units in a building. */
export async function updateBuildingSettings(propertyUuid, buildingId, features) {
    const response = await fetch(`${API_BASE_URL}/properties/${propertyUuid}/settings/building/${buildingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features }),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

// ==================== APPOINTMENTS API ====================

/** Fetch appointments within a date range (yyyy-MM-dd strings). */
export async function fetchAppointments(startDate, endDate) {
    const qs = new URLSearchParams();
    if (startDate) qs.set('start_date', startDate);
    if (endDate) qs.set('end_date', endDate);
    const response = await fetch(`${API_BASE_URL}/appointments?${qs}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

// ==================== WORKFLOW API ====================

/** Send an SMS to a list of tenants (identified by UUID). */
export async function sendWorkflowSms(tenantUuids, message) {
    const response = await fetch(`${API_BASE_URL}/workflow/send-sms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_ids: tenantUuids, message }),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

/** Update feature toggles for one specific unit. */
export async function updateUnitSettings(unitId, features) {
    const response = await fetch(`${API_BASE_URL}/units/${unitId}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features }),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
}
