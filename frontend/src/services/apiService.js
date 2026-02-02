const API_BASE_URL = 'http://localhost:8000';

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
export function getStatusDisplay(status) {
    const statusMap = {
        'pending': 'Pending',
        'in-progress': 'In Progress',
        'resolved': 'Resolved',
        'closed': 'Closed'
    };
    return statusMap[status] || status;
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

// Helper: Format date
export function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}
