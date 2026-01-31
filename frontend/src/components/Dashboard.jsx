import React, { useState, useEffect } from 'react';
import ComplaintTable from './ComplaintTable';
import { api } from '../services/api';
import './Dashboard.css';

const Dashboard = () => {
    const [complaints, setComplaints] = useState([]);
    const [callLogs, setCallLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [updatingIds, setUpdatingIds] = useState([]);

    // Fetch complaints and call logs
    const fetchData = async () => {
        try {
            const [complaintsData, callLogsData] = await Promise.all([
                api.fetchComplaints(),
                api.fetchCallLogs()
            ]);
            setComplaints(complaintsData);
            setCallLogs(callLogsData);
            setError(null);
        } catch (err) {
            console.error('Error fetching data:', err);
            setError('Failed to load complaints. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // Initial fetch on mount
    useEffect(() => {
        fetchData();
    }, []);

    // Polling: Fetch data every 5 seconds
    useEffect(() => {
        const interval = setInterval(() => {
            fetchData();
        }, 5000);

        return () => clearInterval(interval);
    }, []);

    // Handle status update
    const handleStatusUpdate = async (complaintId, newStatus) => {
        setUpdatingIds(prev => [...prev, complaintId]);
        try {
            const updatedComplaint = await api.updateComplaintStatus(complaintId, newStatus);

            // Update local state immediately
            setComplaints(prev =>
                prev.map(complaint =>
                    complaint.id === complaintId
                        ? { ...complaint, status: updatedComplaint.status }
                        : complaint
                )
            );
        } catch (err) {
            console.error('Error updating status:', err);
            alert('Failed to update status. Please try again.');
        } finally {
            setUpdatingIds(prev => prev.filter(id => id !== complaintId));
        }
    };

    if (loading && complaints.length === 0) {
        return (
            <div className="dashboard">
                <div className="dashboard-header">
                    <h1 className="dashboard-title">Dashboard</h1>
                </div>
                <div className="loading-state">Loading complaints...</div>
            </div>
        );
    }

    if (error && complaints.length === 0) {
        return (
            <div className="dashboard">
                <div className="dashboard-header">
                    <h1 className="dashboard-title">Dashboard</h1>
                </div>
                <div className="error-state">{error}</div>
            </div>
        );
    }

    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <h1 className="dashboard-title">Dashboard</h1>
                <div className="auto-refresh-indicator">
                    <span className="pulse-dot"></span>
                    Auto-refreshing every 5s
                </div>
            </div>

            <ComplaintTable
                complaints={complaints}
                callLogs={callLogs}
                onStatusUpdate={handleStatusUpdate}
                updatingIds={updatingIds}
            />
        </div>
    );
};

export default Dashboard;
