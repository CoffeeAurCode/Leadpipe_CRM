import { motion } from 'framer-motion';
import { CalendarIcon } from '@heroicons/react/24/outline';
import PriorityBadge from './PriorityBadge';
import StatusDropdown from './StatusDropdown';
import { formatDate } from '../services/apiService';
import { format, parseISO } from 'date-fns';
import './ComplaintCard.css';

export default function ComplaintCard({ complaint, onUpdate, onViewDetails }) {
    return (
        <motion.div
            className="complaint-card clickable"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.02 }}
            transition={{ duration: 0.3 }}
            onClick={() => onViewDetails && onViewDetails(complaint)}
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
                    {complaint.description || 'No description provided.'}
                </p>

                {/* Appointment Badge */}
                {complaint.appointment_date && (
                    <div className="appointment-badge">
                        <CalendarIcon className="appointment-icon" />
                        <span>{format(parseISO(complaint.appointment_date), 'MMM d, h:mm a')}</span>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="card-footer">
                <div className="footer-left">
                    <span className="timestamp">{formatDate(complaint.created_at)}</span>
                </div>
                <div className="footer-right">
                    <StatusDropdown
                        complaintId={complaint.id}
                        currentStatus={complaint.status}
                        onUpdate={onUpdate}
                    />
                </div>
            </div>
        </motion.div>
    );
}
