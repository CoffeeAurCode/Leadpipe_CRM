import { useState, useEffect, lazy, Suspense } from 'react';
import { motion } from 'framer-motion';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import BentoDashboard from './components/BentoDashboard';
import Chatbot from './components/Chatbot';
import OutboundCallButton from './components/OutboundCallButton';

// Lazy-loaded routes — only downloaded when the user first navigates to them
const CalendarView     = lazy(() => import('./components/CalendarView'));
const PropertiesPage   = lazy(() => import('./components/PropertiesPage'));
const SettingsPage     = lazy(() => import('./components/SettingsPage'));
const TenantManagement = lazy(() => import('./components/TenantManagement'));
const SmsWorkflow      = lazy(() => import('./components/SmsWorkflow'));
const ComplaintsPage   = lazy(() => import('./components/ComplaintsPage'));

const PageFallback = () => (
    <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground text-sm">Loading...</p>
    </div>
);
import { fetchComplaints, updateComplaint, fetchAppointments, updateAppointment, deleteAppointment, getCallStatus } from './services/apiService';
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

    // Poll for call-end events every 10s — refreshes dashboard after any Vapi call finishes
    useEffect(() => {
        let lastSeen = null;
        const poll = async () => {
            try {
                const { last_call_ended_at } = await getCallStatus();
                if (last_call_ended_at && last_call_ended_at !== lastSeen) {
                    lastSeen = last_call_ended_at;
                    loadComplaints();
                    loadAppointments();
                }
            } catch {
                // silently ignore — backend may not be running
            }
        };
        const id = setInterval(poll, 10000);
        return () => clearInterval(id);
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
            const updates = {};
            const original = complaints.find(c => c.id === updatedComplaint.id);
            if (!original) { console.error('Original complaint not found'); return; }
            if (updatedComplaint.status !== original.status) updates.status = updatedComplaint.status;
            if (Object.keys(updates).length === 0) return;
            const serverUpdatedComplaint = await updateComplaint(updatedComplaint.id, updates);
            setComplaints(prev =>
                prev.map(c => c.id === serverUpdatedComplaint.id ? serverUpdatedComplaint : c)
            );
        } catch (error) {
            console.error('Failed to update complaint:', error);
            alert('Failed to update complaint. Please try again.');
        }
    };

    // Handle appointment update (status, date, notes)
    const handleAppointmentUpdate = async (id, updates) => {
        await updateAppointment(id, updates);
        await loadAppointments();
    };

    // Handle appointment delete
    const handleAppointmentDelete = async (id) => {
        await deleteAppointment(id);
        await loadAppointments();
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
                        <Suspense fallback={<PageFallback />}><SmsWorkflow /></Suspense>
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
                                <Suspense fallback={<PageFallback />}>
                                    {currentView === 'dashboard' && (
                                        <BentoDashboard
                                            complaints={complaints}
                                            appointments={appointments}
                                            onComplaintUpdate={handleComplaintUpdate}
                                            onAppointmentUpdate={handleAppointmentUpdate}
                                            onAppointmentDelete={handleAppointmentDelete}
                                        />
                                    )}
                                    {currentView === 'complaints' && (
                                        <ComplaintsPage
                                            complaints={complaints}
                                            onComplaintUpdate={handleComplaintUpdate}
                                        />
                                    )}
                                    {currentView === 'calendar' && (
                                        <CalendarView
                                            complaints={complaints}
                                            appointments={appointments}
                                            onComplaintUpdate={handleComplaintUpdate}
                                            onAppointmentUpdate={handleAppointmentUpdate}
                                            onAppointmentDelete={handleAppointmentDelete}
                                        />
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
                                </Suspense>
                            )}
                        </>
                    )}
                </motion.div>
            </div>
        </div>
        {/* Floating action buttons — phone + chatbot, bottom-right corner */}
        <div className="fixed bottom-4 right-4 z-50 flex items-end gap-3">
            <OutboundCallButton />
            <Chatbot />
        </div>
        </>
    );
}

export default App;
