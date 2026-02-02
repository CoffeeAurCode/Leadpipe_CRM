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
    }
};
