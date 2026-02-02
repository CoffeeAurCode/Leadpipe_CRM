import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib';
import CompactStatsGrid from './CompactStatsGrid';
import CompactCalendar from './CompactCalendar';
import RecentUpdates from './RecentUpdates';
import QuickFilters from './QuickFilters';
import CompactComplaintCard from './CompactComplaintCard';
import ComplaintModal from './ComplaintModal';
import DateComplaintsModal from './DateComplaintsModal';

function BentoDashboard({ complaints, onComplaintUpdate }) {
    const [filters, setFilters] = useState({ status: 'all', priority: 'all' });
    const [selectedComplaint, setSelectedComplaint] = useState(null);
    const [selectedDate, setSelectedDate] = useState(null);
    const [complaintsForDate, setComplaintsForDate] = useState([]);

    // Filter complaints based on active filters
    const filteredComplaints = useMemo(() => {
        return complaints.filter(complaint => {
            const matchesStatus = filters.status === 'all' || complaint.status === filters.status;
            const matchesPriority = filters.priority === 'all' || complaint.priority === filters.priority;
            return matchesStatus && matchesPriority;
        });
    }, [complaints, filters]);

    // High priority complaints for priority queue
    const highPriorityComplaints = useMemo(() => {
        return complaints
            .filter(c => c.priority === 'high')
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .slice(0, 5);
    }, [complaints]);

    // Recently updated complaints
    const recentlyUpdated = useMemo(() => {
        return [...complaints]
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .slice(0, 5);
    }, [complaints]);

    const openComplaintModal = (complaint) => setSelectedComplaint(complaint);
    const closeComplaintModal = () => setSelectedComplaint(null);

    const openDateModal = (date, complaintsOnDate) => {
        setSelectedDate(date);
        setComplaintsForDate(complaintsOnDate);
    };
    const closeDateModal = () => {
        setSelectedDate(null);
        setComplaintsForDate([]);
    };

    // Container animation
    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const tileVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
    };

    return (
        <div className="space-y-6">
            {/* Bento Grid - LeadPipe pattern: 12-column grid */}
            <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                className="grid grid-cols-1 lg:grid-cols-12 gap-3 lg:gap-4"
            >
                {/* Top left: Filters (5 columns) */}
                <div className="lg:col-span-5">
                    <QuickFilters
                        filters={filters}
                        onFilterChange={setFilters}
                    />
                </div>

                {/* Top right: Stats (7 columns) */}
                <div className="lg:col-span-7">
                    <CompactStatsGrid complaints={complaints} />
                </div>

                {/* Bottom left: Recently Added (5 columns) */}
                <div className="lg:col-span-5">
                    <RecentUpdates
                        complaints={recentlyUpdated}
                        onComplaintClick={openComplaintModal}
                    />
                </div>

                {/* Bottom right: Calendar (7 columns) */}
                <div className="lg:col-span-7">
                    <CompactCalendar
                        complaints={complaints}
                        onDateClick={openDateModal}
                    />
                </div>
            </motion.div>

            {/* Compact Complaint Grid */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="space-y-4"
            >
                <h3 className="text-2xl font-bold text-foreground">
                    All Complaints
                    {filters.status !== 'all' || filters.priority !== 'all' ? (
                        <span className="ml-2 text-sm font-normal text-muted-foreground">
                            ({filteredComplaints.length} filtered)
                        </span>
                    ) : (
                        <span className="ml-2 text-sm font-normal text-muted-foreground">
                            ({complaints.length} total)
                        </span>
                    )}
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredComplaints.map(complaint => (
                        <CompactComplaintCard
                            key={complaint.id}
                            complaint={complaint}
                            onClick={() => openComplaintModal(complaint)}
                            onUpdate={onComplaintUpdate}
                        />
                    ))}
                </div>

                {filteredComplaints.length === 0 && (
                    <div className="flex items-center justify-center h-32 rounded-lg border border-border bg-card">
                        <p className="text-muted-foreground">No complaints match the current filters</p>
                    </div>
                )}
            </motion.div>

            {/* Modals */}
            <AnimatePresence>
                {selectedComplaint && (
                    <ComplaintModal
                        complaint={selectedComplaint}
                        onClose={closeComplaintModal}
                        onUpdate={onComplaintUpdate}
                    />
                )}
            </AnimatePresence>

            <AnimatePresence>
                {selectedDate && (
                    <DateComplaintsModal
                        date={selectedDate}
                        complaints={complaintsForDate}
                        onClose={closeDateModal}
                        onComplaintClick={openComplaintModal}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

export default BentoDashboard;

