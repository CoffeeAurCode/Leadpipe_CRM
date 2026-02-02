import { motion } from 'framer-motion';
import PriorityBadge from './PriorityBadge';
import StatusDropdown from './StatusDropdown';
import { formatDate } from '../services/apiService';
import './ComplaintCard.css';

export default function ComplaintCard({ complaint, onUpdate }) {
    const truncateText = (text, maxLength = 120) => {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    };

    return (
        <motion.div
            className="complaint-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.02 }}
            transition={{ duration: 0.3 }}
        >
            {/* Header */}
            <div className="card-header">
                <div className="card-id">#{complaint.id}</div>
                <PriorityBadge priority={complaint.priority} />
            </div>

            {/* Body */}
            <div className="card-body">
                <div className="card-meta">
                    <span className="flat-number">
                        {complaint.flat_number || 'N/A'}
                    </span>
                    <span className="separator">•</span>
                    <span className="category">{complaint.category}</span>
                </div>

                <p className="description">
                    {truncateText(complaint.description)}
                </p>
            </div>

            {/* Footer */}
            <div className="card-footer">
                <div className="footer-left">
                    <StatusDropdown
                        complaintId={complaint.id}
                        currentStatus={complaint.status}
                        onUpdate={onUpdate}
                    />
                </div>
                <div className="footer-right">
                    <span className="timestamp">{formatDate(complaint.created_at)}</span>
                </div>
            </div>
        </motion.div>
    );
}
