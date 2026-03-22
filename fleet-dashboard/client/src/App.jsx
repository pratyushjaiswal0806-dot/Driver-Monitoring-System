import { useEffect, useMemo, useState } from 'react';
import {
    BrowserRouter,
    Outlet,
    Route,
    Routes,
    useLocation,
    useOutletContext
} from 'react-router-dom';

import { useApi } from './hooks/useApi';
import { usePolling } from './hooks/usePolling';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import FleetOverview from './pages/FleetOverview';
import DriverDetail from './pages/DriverDetail';
import Analytics from './pages/Analytics';
import NotFound from './pages/NotFound';
import { DEFAULT_DRIVER_ID } from './utils/formatters';

const APP_NAME = 'Driver Monitoring System';

function getPageTitle(pathname) {
    if (pathname === '/') {
        return 'Fleet Overview';
    }

    if (pathname.startsWith('/analytics')) {
        return 'Analytics';
    }

    if (pathname.startsWith('/drivers/')) {
        return 'Driver Detail';
    }

    return 'Not Found';
}

function DashboardShell() {
    const location = useLocation();
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [refreshKey, setRefreshKey] = useState(0);
    const [lastUpdated, setLastUpdated] = useState(new Date().toISOString());

    const pollingTick = usePolling(5000, true);
    const driversQuery = useApi('/api/drivers', { initialData: [] }, [refreshKey, pollingTick]);

    useEffect(() => {
        setSidebarOpen(false);
    }, [location.pathname]);

    useEffect(() => {
        setLastUpdated(new Date().toISOString());
    }, [refreshKey, pollingTick]);

    useEffect(() => {
        document.title = `${getPageTitle(location.pathname)} | ${APP_NAME}`;
    }, [location.pathname]);

    const refreshAll = () => {
        setRefreshKey((current) => current + 1);
        setLastUpdated(new Date().toISOString());
    };

    const outletContext = useMemo(() => ({
        refreshKey,
        pollingTick,
        manualRefresh: refreshAll,
        lastUpdated,
        drivers: driversQuery.data || [],
        driversLoading: driversQuery.loading,
        driversError: driversQuery.error,
        defaultDriverId: DEFAULT_DRIVER_ID
    }), [refreshKey, pollingTick, lastUpdated, driversQuery.data, driversQuery.loading, driversQuery.error]);

    return (
        <div className="flex min-h-screen bg-[var(--app-bg)] text-white/90">
            <Sidebar
                open={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
                drivers={driversQuery.data || []}
                loading={driversQuery.loading}
            />

            <div className="flex min-h-screen flex-1 flex-col md:pl-[240px]">
                <Navbar
                    title={getPageTitle(location.pathname)}
                    appName={APP_NAME}
                    lastUpdated={lastUpdated}
                    onRefresh={refreshAll}
                    onMenuToggle={() => setSidebarOpen((current) => !current)}
                />

                <main className="dashboard-content motion-page mx-auto flex-1 w-full max-w-[1280px] px-4 py-6 sm:px-6 lg:px-8">
                    <Outlet context={outletContext} />
                </main>
            </div>
        </div>
    );
}

export function useDashboardContext() {
    return useOutletContext();
}

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route element={<DashboardShell />}>
                    <Route path="/" element={<FleetOverview />} />
                    <Route path="/analytics" element={<Analytics />} />
                    <Route path="/drivers/:id" element={<DriverDetail />} />
                    <Route path="*" element={<NotFound />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}
