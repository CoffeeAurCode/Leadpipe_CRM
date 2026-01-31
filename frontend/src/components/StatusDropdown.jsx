import React from 'react';
import './StatusDropdown.css';

const StatusDropdown = ({ currentStatus, complaintId, onStatusChange, isUpdating }) => {
    const statuses = ['pending', 'in-progress', 'resolved', 'closed'];

    const handleChange = async (e) => {
        const newStatus = e.target.value;
        if (newStatus !== currentStatus) {
            await onStatusChange(complaintId, newStatus);
        }
    };

    const getStatusIcon = (status) => {
        if (status === 'resolved' || status === 'closed') {
            return '✓';
        }
        return '';
    };

    return (
        <div className="status-dropdown-container">
            {isUpdating ? (
                <div className="status-loading">Updating...</div>
            ) : (
                <>
                    <select
                        className="status-dropdown"
                        value={currentStatus}
                        onChange={handleChange}
                        disabled={isUpdating}
                    >
                        {statuses.map(status => (
                            <option key={status} value={status}>
                                {status}
                            </option>
                        ))}
                    </select>
                    {getStatusIcon(currentStatus) && (
                        <span className="status-icon">{getStatusIcon(currentStatus)}</span>
                    )}
                </>
            )}
        </div>
    );
};

export default StatusDropdown;
