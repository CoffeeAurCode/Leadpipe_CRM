import React from 'react';
import StatusDropdown from './StatusDropdown';
import './ComplaintTable.css';

const ComplaintTable = ({ complaints, callLogs, onStatusUpdate, updatingIds }) => {
    // Create a map of complaint_id -> phone_number from call logs
    const phoneMap = {};
    if (callLogs && callLogs.length > 0) {
        callLogs.forEach(log => {
            if (log.complaint_id && log.phone_number) {
                phoneMap[log.complaint_id] = log.phone_number;
            }
        });
    }

    const getPriorityClass = (priority) => {
        switch (priority?.toLowerCase()) {
            case 'high':
                return 'priority-high';
            case 'medium':
                return 'priority-medium';
            case 'low':
                return 'priority-low';
            default:
                return '';
        }
    };

    if (!complaints || complaints.length === 0) {
        return (
            <div className="table-container">
                <div className="empty-state">No complaints found</div>
            </div>
        );
    }

    return (
        <div className="table-container">
            <table className="complaint-table">
                <thead>
                    <tr>
                        <th>No.</th>
                        <th>Flat No.</th>
                        <th>Mobile No.</th>
                        <th>Description</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {complaints.map((complaint, index) => (
                        <tr key={complaint.id} className={getPriorityClass(complaint.priority)}>
                            <td className="cell-number">{index + 1}</td>
                            <td className="cell-flat">{complaint.flat_number || 'N/A'}</td>
                            <td className="cell-phone">{phoneMap[complaint.id] || 'N/A'}</td>
                            <td className="cell-description">{complaint.description}</td>
                            <td className="cell-status">
                                <StatusDropdown
                                    currentStatus={complaint.status}
                                    complaintId={complaint.id}
                                    onStatusChange={onStatusUpdate}
                                    isUpdating={updatingIds.includes(complaint.id)}
                                />
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default ComplaintTable;
