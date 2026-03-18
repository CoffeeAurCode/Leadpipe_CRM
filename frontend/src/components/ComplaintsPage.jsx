import { useState, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import QuickFilters from './QuickFilters';
import CompactComplaintCard from './CompactComplaintCard';
import ComplaintModal from './ComplaintModal';

export default function ComplaintsPage({ complaints = [], onComplaintUpdate }) {
    const [filters, setFilters] = useState({ status: 'all', priority: 'all' });
    const [selectedComplaint, setSelectedComplaint] = useState(null);

    const filteredComplaints = useMemo(() => {
        return complaints.filter(complaint => {
            const matchesStatus = filters.status === 'all' || complaint.status === filters.status;
            const matchesPriority = filters.priority === 'all' || complaint.priority === filters.priority;
            return matchesStatus && matchesPriority;
        });
    }, [complaints, filters]);

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
            >
                <h1 className="text-2xl font-bold text-foreground">Complaints</h1>
                <p className="text-sm text-muted-foreground mt-0.5">
                    {filters.status !== 'all' || filters.priority !== 'all'
                        ? `${filteredComplaints.length} filtered`
                        : `${complaints.length} total`} complaint{complaints.length !== 1 ? 's' : ''}
                </p>
            </motion.div>

            {/* Filters */}
            <QuickFilters filters={filters} onFilterChange={setFilters} />

            {/* Card grid */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            >
                {filteredComplaints.map(complaint => (
                    <CompactComplaintCard
                        key={complaint.id}
                        complaint={complaint}
                        onClick={() => setSelectedComplaint(complaint)}
                        onUpdate={onComplaintUpdate}
                    />
                ))}
                {filteredComplaints.length === 0 && (
                    <div className="col-span-3 flex items-center justify-center h-32 rounded-lg border border-border bg-card">
                        <p className="text-muted-foreground text-sm">No complaints match the current filters</p>
                    </div>
                )}
            </motion.div>

            {/* Detail modal */}
            <AnimatePresence>
                {selectedComplaint && (
                    <ComplaintModal
                        complaint={selectedComplaint}
                        onClose={() => setSelectedComplaint(null)}
                        onUpdate={onComplaintUpdate}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}
