import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import BentoDashboard from './components/BentoDashboard';
import CalendarView from './components/CalendarView';
import PropertiesPage from './components/PropertiesPage';
import SettingsPage from './components/SettingsPage';
import TenantManagement from './components/TenantManagement';
import SmsWorkflow from './components/SmsWorkflow';
import Chatbot from './components/Chatbot';
import { fetchComplaints, updateComplaint, fetchAppointments } from './services/apiService';
import { format, subDays, addDays } from 'date-fns';

function App() {
    const [complaints, setComplaints] = useState([]);
    const [appointments, setAppointments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentView, setCurrentView] = useState('dashboard');

    // Fetch complaints on mount
    useEffect(() => {
        loadComplaints();
        loadAppointments();
    }, []);

    // Listen for custom silent refresh events from modals
    useEffect(() => {
        window.addEventListener('refresh-data', loadComplaints);
        return () => window.removeEventListener('refresh-data', loadComplaints);
    }, []);

    // Refresh appointments when chatbot performs a write action
    useEffect(() => {
        window.addEventListener('refresh-appointments', loadAppointments);
        return () => window.removeEventListener('refresh-appointments', loadAppointments);
    }, []);

    async function loadAppointments() {
        try {
            const start = format(subDays(new Date(), 90), 'yyyy-MM-dd');
            const end = format(addDays(new Date(), 30), 'yyyy-MM-dd');
            const data = await fetchAppointments(start, end);
            setAppointments(data);
        } catch (err) {
            console.error('Failed to load appointments:', err);
        }
    }

    async function loadComplaints() {
        try {
            setLoading(true);
            const data = await fetchComplaints();
            setComplaints(data);
            setError(null);
        } catch (err) {
            setError('Failed to load complaints. Please check if the backend is running.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    // Handle complaint update from child components
    const handleComplaintUpdate = async (updatedComplaint) => {
        try {
            // Extract only the fields that have changed
            // For status updates, we only need to send the status field
            const updates = {};

            // Find the original complaint to compare
            const original = complaints.find(c => c.id === updatedComplaint.id);

            if (!original) {
                console.error('Original complaint not found');
                return;
            }

            // Determine which fields changed
            if (updatedComplaint.status !== original.status) {
                updates.status = updatedComplaint.status;
            }

            // If no changes, skip API call
            if (Object.keys(updates).length === 0) {
                return;
            }

            // Call the backend API to persist changes
            const serverUpdatedComplaint = await updateComplaint(updatedComplaint.id, updates);

            // Only update local state after successful API response
            setComplaints(prev =>
                prev.map(c => c.id === serverUpdatedComplaint.id ? serverUpdatedComplaint : c)
            );
        } catch (error) {
            console.error('Failed to update complaint:', error);
            // Optionally show user-friendly error message
            alert('Failed to update complaint. Please try again.');
        }
    };

    // Handle navigation
    const handleNavigate = (view) => {
        setCurrentView(view);
    };

    return (
        <>
        <div className="flex h-screen bg-background overflow-hidden">
            <Sidebar currentView={currentView} onNavigate={handleNavigate} />

            <div className="flex-1 flex flex-col overflow-hidden">
                <TopBar onRefresh={loadComplaints} />

                <motion.div
                    key={currentView}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className="flex-1 overflow-y-auto p-6"
                >
                    {currentView === 'workflow' ? (
                        <SmsWorkflow />
                    ) : (
                        <>
                            {error && (
                                <div className="mb-4 p-4 rounded-lg bg-red-500/10 border border-red-500 text-red-500">
                                    <p>{error}</p>
                                </div>
                            )}

                            {loading && complaints.length === 0 ? (
                                <div className="flex items-center justify-center h-full">
                                    <p className="text-muted-foreground">Loading complaints...</p>
                                </div>
                            ) : (
                                <>
                                    {currentView === 'dashboard' && (
                                        <BentoDashboard
                                            complaints={complaints}
                                            appointments={appointments}
                                            onComplaintUpdate={handleComplaintUpdate}
                                        />
                                    )}
                                    {currentView === 'calendar' && (
                                        <CalendarView complaints={complaints} appointments={appointments} />
                                    )}
                                    {currentView === 'properties' && (
                                        <PropertiesPage />
                                    )}
                                    {currentView === 'tenants' && (
                                        <TenantManagement />
                                    )}
                                    {currentView === 'settings' && (
                                        <SettingsPage />
                                    )}
                                </>
                            )}
                        </>
                    )}
                </motion.div>
            </div>
        </div>
        <Chatbot />
        </>
    );
}

export default App;


