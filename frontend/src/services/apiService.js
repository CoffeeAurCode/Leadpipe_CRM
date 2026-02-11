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
