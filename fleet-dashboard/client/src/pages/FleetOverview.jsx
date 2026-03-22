import { useMemo } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';

import { useApi } from '../hooks/useApi';
import StatCard from '../components/StatCard';
import SkeletonCard from '../components/SkeletonCard';
import RiskBadge from '../components/RiskBadge';
import { formatTimestamp, formatRiskLabel } from '../utils/formatters';

function RadarIcon() {
    return (
        <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 12a9 9 0 1 0 18 0" />
            <path d="M12 3a9 9 0 0 1 9 9" />
            <path d="M12 12l5-5" />
            <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
        </svg>
    );
}

function ChartPanel({ title, children, subtitle = '' }) {
    return (
        <div className="dashboard-panel">
            <div className="dashboard-panel-header">
                <div>
                    <div className="dashboard-kicker">Insight Panel</div>
                    <div className="mt-1 font-display text-[1.125rem] font-semibold text-white">{title}</div>
                    {subtitle ? <div className="mt-1 text-[0.75rem] text-white/40">{subtitle}</div> : null}
                </div>
                <div className="dashboard-badge border-white/8 bg-white/5 text-white/55">Live</div>
            </div>
            {children}
        </div>
    );
}

function EmptyChart({ message }) {
    return <div className="flex h-72 items-center justify-center text-sm text-white/40">{message}</div>;
}

export default function FleetOverview() {
    const { refreshKey, pollingTick } = useOutletContext();
    const overviewQuery = useApi('/api/fleet/overview', { initialData: null }, [refreshKey, pollingTick]);
    const trendQuery = useApi('/api/analytics/trends?days=7', { initialData: [] }, [refreshKey, pollingTick]);

    const overview = overviewQuery.data;
    const trendData = trendQuery.data || [];

    const stats = useMemo(() => ([
        {
            label: 'Total Active Drivers Today',
            value: overview ? overview.activeToday : '—',
            subtext: overview ? `${overview.totalDrivers} registered driver${overview.totalDrivers === 1 ? '' : 's'}` : '',
            tone: 'blue'
        },
        {
            label: 'Total Alerts Today',
            value: overview ? overview.totalAlertsToday : '—',
            subtext: 'Alerts logged from the fleet',
            tone: 'orange'
        },
        {
            label: 'Critical Alerts Today',
            value: overview ? overview.criticalAlertsToday : '—',
            subtext: overview && overview.criticalAlertsToday > 0 ? 'Immediate review recommended' : 'No critical alerts yet',
            tone: overview && overview.criticalAlertsToday > 0 ? 'red' : 'neutral'
        },
        {
            label: 'Fleet Average Risk Score',
            value: overview ? overview.averageRiskScore.toFixed(1) : '—',
            subtext: 'Average from today\'s alerts',
            tone: 'purple'
        }
    ]), [overview]);

    const driverStatuses = overview?.driverStatuses || [];
    const autoRefreshStatus = 'ON';

    return (
        <div className="space-y-4">
            <div className="dashboard-hero flex h-[88px] items-center rounded-[20px] px-5">
                <div className="flex w-full items-center justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/8 bg-[rgba(96,165,250,0.1)] text-[#60a5fa] shadow-[0_0_18px_rgba(96,165,250,0.12)]">
                                <RadarIcon />
                            </div>
                            <div>
                                <div className="dashboard-kicker">Fleet overview</div>
                                <h2 className="mt-1 font-display text-[1.5rem] font-semibold text-white">Operational pulse at a glance</h2>
                            </div>
                        </div>
                    </div>

                    <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-[0.68rem] uppercase tracking-[0.06em] text-emerald-200">
                        <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(34,197,94,0.6)]" />
                        Auto-refresh {autoRefreshStatus}
                    </div>
                </div>
            </div>

            {overviewQuery.loading ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <SkeletonCard />
                    <SkeletonCard />
                    <SkeletonCard />
                    <SkeletonCard />
                </div>
            ) : overviewQuery.error ? (
                <div className="dashboard-card p-6">
                    <div className="text-sm font-semibold uppercase tracking-[0.2em] text-red-300">Unable to load fleet overview</div>
                    <div className="mt-2 text-sm text-slate-300">{overviewQuery.error.message}</div>
                    <button type="button" onClick={overviewQuery.refetch} className="dashboard-button mt-4">
                        Retry
                    </button>
                </div>
            ) : (
                <div className="motion-stagger grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {stats.map((stat) => (
                        <StatCard key={stat.label} {...stat} />
                    ))}
                </div>
            )}

            <div className="dashboard-panel overflow-hidden">
                <div className="dashboard-panel-header">
                    <div>
                        <div className="dashboard-kicker">Status board</div>
                        <div className="mt-1 font-display text-[1.125rem] font-semibold text-white">Driver Status</div>
                        <div className="mt-1 text-[0.75rem] text-white/40">Real-time status for every known driver</div>
                    </div>
                </div>

                {driverStatuses.length === 0 ? (
                    <div className="px-5 py-10 text-center text-sm text-white/40">No driver statuses available yet.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="dashboard-table min-w-full text-left">
                            <thead className="text-[0.68rem] uppercase tracking-[0.04em] text-white/40">
                                <tr>
                                    <th className="px-4 py-3.5 font-medium">Driver Name</th>
                                    <th className="px-4 py-3.5 font-medium">Last Seen</th>
                                    <th className="px-4 py-3.5 font-medium">Current Risk Level</th>
                                    <th className="px-4 py-3.5 font-medium">Alerts Today</th>
                                    <th className="px-4 py-3.5 font-medium">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/4">
                                {driverStatuses.map((driver) => (
                                    <tr key={driver.driverId} className="transition hover:bg-white/[0.03]">
                                        <td className="px-4 py-3.5 text-[0.9rem] font-medium text-white">{driver.name}</td>
                                        <td className="px-4 py-3.5 text-[0.85rem] text-white/70">{formatTimestamp(driver.lastSeen)}</td>
                                        <td className="px-4 py-3.5">
                                            <RiskBadge level={driver.currentRiskLevel} />
                                        </td>
                                        <td className="px-4 py-3.5 text-[0.85rem] text-white/80">{driver.alertsToday || 0}</td>
                                        <td className="px-4 py-3.5">
                                            <Link to={`/drivers/${driver.driverId}`} className="text-[0.78rem] font-medium text-blue-400 hover:text-blue-300 hover:underline">
                                                View Details
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <ChartPanel
                title="Fleet Trend"
                subtitle="Daily alerts across the last 7 days"
            >
                {trendQuery.loading ? (
                    <div className="h-72 animate-pulse rounded-2xl bg-white/5" />
                ) : trendQuery.error ? (
                    <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-6 text-red-100">
                        <div className="text-sm font-semibold uppercase tracking-[0.2em]">Trend chart unavailable</div>
                        <div className="mt-2 text-sm">{trendQuery.error.message}</div>
                        <button type="button" onClick={trendQuery.refetch} className="dashboard-button mt-4 border-red-400/30 bg-red-500/10 text-red-100">
                            Retry
                        </button>
                    </div>
                ) : trendData.length === 0 ? (
                    <EmptyChart message="No trend data available yet." />
                ) : (
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={trendData} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                                <CartesianGrid stroke="rgba(255,255,255,0.05)" strokeDasharray="4 4" />
                                <XAxis dataKey="date" stroke="rgba(255,255,255,0.35)" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }} />
                                <YAxis stroke="rgba(255,255,255,0.35)" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }} allowDecimals={false} />
                                <Tooltip
                                    contentStyle={{
                                        background: '#1a1d2e',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: 8,
                                        padding: '10px 14px',
                                        color: '#fff'
                                    }}
                                    labelStyle={{ color: '#fff' }}
                                />
                                <Line type="monotone" dataKey="totalAlerts" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: '#3b82f6' }} activeDot={{ r: 5, fill: '#3b82f6' }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </ChartPanel>
        </div>
    );
}
