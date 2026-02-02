import { motion } from 'framer-motion';
import './PriorityQueue.css';
import PriorityBadge from './PriorityBadge';
import { formatDate } from '../services/apiService';

function PriorityQueue({ complaints, onComplaintClick }) {
    return (
        <motion.div
            className="priority-queue bento-tile"
            variants={{
                hidden: { opacity: 0, y: 20 },
                visible: { opacity: 1, y: 0 }
            }}
        >
            <div className="tile-header">
                <span className="tile-icon">⚠️</span>
                <h3 className="tile-title">High Priority</h3>
            </div>

            <div className="queue-list">
                {complaints.length === 0 ? (
                    <div className="empty-queue">No high priority complaints</div>
                ) : (
                    complaints.map(complaint => (
                        <div
                            key={complaint.id}
                            className="queue-item"
                            onClick={() => onComplaintClick(complaint)}
                        >
                            <div className="queue-item-header">
                                <span className="queue-flat">{complaint.flat_number}</span>
                                <PriorityBadge priority={complaint.priority} />
                            </div>
                            <div className="queue-category">{complaint.category}</div>
                            <div className="queue-time">{formatDate(complaint.created_at)}</div>
                        </div>
                    ))
                )}
            </div>

            {complaints.length >= 5 && (
                <div className="queue-footer">
                    <span className="see-all-link">See all high priority →</span>
                </div>
            )}
        </motion.div>
    );
}

export default PriorityQueue;
