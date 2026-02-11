// Use environment variable for API URL, fallback to localhost for development
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
    async fetchComplaints() {
        try {
            const response = await fetch(`${BASE_URL}/complaints`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching complaints:', error);
            throw error;
        }
    },

    async updateComplaintStatus(complaintId, status) {
        try {
            const response = await fetch(`${BASE_URL}/complaints/${complaintId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error updating complaint status:', error);
            throw error;
        }
    },

    async fetchCallLogs() {
        try {
            const response = await fetch(`${BASE_URL}/call_logs`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching call logs:', error);
            throw error;
        }
    },

    // ========== FLATS ENDPOINTS ==========

    async verifyFlat(flatNumber) {
        try {
            const response = await fetch(`${BASE_URL}/flats/verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ flat_number: flatNumber }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error verifying flat:', error);
            throw error;
        }
    },

    async fetchFlats() {
        try {
            const response = await fetch(`${BASE_URL}/flats`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching flats:', error);
            throw error;
        }
    },

    // ========== APPOINTMENTS ENDPOINTS ==========

    async fetchAppointments(filters = {}) {
        try {
            const params = new URLSearchParams();
            if (filters.start_date) params.append('start_date', filters.start_date);
            if (filters.end_date) params.append('end_date', filters.end_date);
            if (filters.flat_number) params.append('flat_number', filters.flat_number);

            const url = `${BASE_URL}/appointments${params.toString() ? '?' + params.toString() : ''}`;
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching appointments:', error);
            throw error;
        }
    },

    async createAppointment(appointmentData) {
        try {
            const response = await fetch(`${BASE_URL}/appointments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(appointmentData),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error creating appointment:', error);
            throw error;
        }
    },

    async updateAppointment(appointmentId, updateData) {
        try {
            const response = await fetch(`${BASE_URL}/appointments/${appointmentId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updateData),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error updating appointment:', error);
            throw error;
        }
    },

    async cancelAppointment(appointmentId) {
        try {
            const response = await fetch(`${BASE_URL}/appointments/${appointmentId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return true;
        } catch (error) {
            console.error('Error cancelling appointment:', error);
            throw error;
        }
    },

    // ========== TENANTS ENDPOINTS ==========

    async fetchTenants() {
        try {
            const response = await fetch(`${BASE_URL}/tenants`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching tenants:', error);
            throw error;
        }
    },

    async getTenantByUuid(tenantUuid) {
        try {
            const response = await fetch(`${BASE_URL}/tenants/${tenantUuid}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching tenant:', error);
            throw error;
        }
    },

    async getTenantByPhone(phone) {
        try {
            const response = await fetch(`${BASE_URL}/tenants/by-phone/${phone}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching tenant by phone:', error);
            throw error;
        }
    },

    async createTenant(tenantData) {
        try {
            const response = await fetch(`${BASE_URL}/tenants`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(tenantData),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error creating tenant:', error);
            throw error;
        }
    },

    async updateTenant(tenantUuid, updateData) {
        try {
            const response = await fetch(`${BASE_URL}/tenants/${tenantUuid}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updateData),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error updating tenant:', error);
            throw error;
        }
    },

    async deleteTenant(tenantUuid) {
        try {
            const response = await fetch(`${BASE_URL}/tenants/${tenantUuid}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return true;
        } catch (error) {
            console.error('Error deleting tenant:', error);
            throw error;
        }
    }
};
