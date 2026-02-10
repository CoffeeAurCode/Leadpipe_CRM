import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import ComplaintCard from './ComplaintCard';
import ComplaintDetailModal from './ComplaintDetailModal';
import './ComplaintsOverview.css';

export default function ComplaintsOverview({ complaints, loading, onComplaintUpdate }) {
    const [selectedStatus, setSelectedStatus] = useState('all');
    const [selectedPriority, setSelectedPriority] = useState('all');
    const [selectedComplaint, setSelectedComplaint] = useState(null);

    // Calculate statistics
    const stats = useMemo(() => {
        return {
            total: complaints.length,
            pending: complaints.filter(c => c.status === 'pending').length,
            inProgress: complaints.filter(c => c.status === 'in-progress').length,
            resolved: complaints.filter(c => c.status === 'resolved').length,
        };
    }, [complaints]);

    // Filter complaints
    const filteredComplaints = useMemo(() => {
        return complaints.filter(complaint => {
            const statusMatch = selectedStatus === 'all' || complaint.status === selectedStatus;
            const priorityMatch = selectedPriority === 'all' || complaint.priority === selectedPriority;
            return statusMatch && priorityMatch;
        });
    }, [complaints, selectedStatus, selectedPriority]);

    // Animation variants for staggered children
    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.05
            }
        }
    };

    return (
        <div className="complaints-overview">
            {/* Stats Overview */}
            <motion.div
                className="stats-grid"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
            >
                <div className="stat-card">
                    <div className="stat-value">{stats.total}</div>
                    <div className="stat-label">Total Complaints</div>
                </div>
                <div className="stat-card accent">
                    <div className="stat-value">{stats.pending}</div>
                    <div className="stat-label">Pending</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{stats.inProgress}</div>
                    <div className="stat-label">In Progress</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{stats.resolved}</div>
                    <div className="stat-label">Resolved</div>
                </div>
            </motion.div>

            {/* Filters */}
            <motion.div
                className="filters"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2, duration: 0.3 }}
            >
                <div className="filter-group">
                    <label>Status:</label>
                    <select
                        className="filter-select"
                        value={selectedStatus}
                        onChange={(e) => setSelectedStatus(e.target.value)}
                    >
                        <option value="all">All</option>
                        <option value="pending">Pending</option>
                        <option value="in-progress">In Progress</option>
                        <option value="resolved">Resolved</option>
                        <option value="closed">Closed</option>
                    </select>
                </div>

                <div className="filter-group">
                    <label>Priority:</label>
                    <select
                        className="filter-select"
                        value={selectedPriority}
                        onChange={(e) => setSelectedPriority(e.target.value)}
                    >
                        <option value="all">All</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>

                <div className="results-count">
                    Showing {filteredComplaints.length} of {complaints.length} complaints
                </div>
            </motion.div>

            {/* Complaints Grid */}
            {loading ? (
                <div className="loading-state">
                    <div className="loader"></div>
                    <p>Loading complaints...</p>
                </div>
            ) : filteredComplaints.length === 0 ? (
                <div className="empty-state">
                    <p>No complaints found</p>
                </div>
            ) : (
                <motion.div
                    className="complaints-grid"
                    variants={containerVariants}
                    initial="hidden"
                    animate="visible"
                >
                    {filteredComplaints.map(complaint => (
                        <ComplaintCard
                            key={complaint.id}
                            complaint={complaint}
                            onUpdate={onComplaintUpdate}
                            onViewDetails={setSelectedComplaint}
                        />
                    ))}
                </motion.div>
            )}

            {/* Detail Modal */}
            <ComplaintDetailModal
                complaint={selectedComplaint}
                isOpen={selectedComplaint !== null}
                onClose={() => setSelectedComplaint(null)}
            />
        </div>
    );
}
