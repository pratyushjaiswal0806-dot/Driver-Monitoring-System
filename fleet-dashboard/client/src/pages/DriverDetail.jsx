import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useOutletContext } from 'react-router-dom';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    LabelList,
    Line,
    LineChart,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
    Legend
} from 'recharts';

import { useApi } from '../hooks/useApi';
import RiskGauge from '../components/RiskGauge';
import StatCard from '../components/StatCard';
import SkeletonCard from '../components/SkeletonCard';
import AlertTable from '../components/AlertTable';
import HealthCard from '../components/HealthCard';
import RiskBadge from '../components/RiskBadge';
import {
    DEFAULT_DRIVER_ID,
    alertsToCsv,
    buildDateSeries,
    downloadCsv,
    formatTimestamp,
    formatTriggerName,
    getRiskLevelFromScore,
    groupAlertsByDay,
    groupTriggers,
    RISK_COLORS,
    RISK_LEVELS
} from '../utils/formatters';

function toDateInputValue(offsetDays = 0) {
    const date = new Date();
    date.setDate(date.getDate() - offsetDays);
    return date.toISOString().slice(0, 10);
}

function ChartPanel({ title, children, subtitle = '' }) {
    return (
        <div className="dashboard-panel">
            <div className="dashboard-panel-header">
                <div>
                    <div className="dashboard-kicker">Driver insights</div>
                    <div className="mt-1 font-display text-[1.125rem] font-semibold text-white">{title}</div>
                    {subtitle ? <div className="mt-1 text-[0.75rem] text-white/40">{subtitle}</div> : null}
                </div>
                <div className="dashboard-badge border-white/8 bg-white/5 text-white/55">Live</div>
            </div>
            {children}
        </div>
    );
}

function TabButton({ active, children, onClick }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`-mb-px border-b-2 px-1 pb-3 pt-2 text-[0.85rem] font-medium transition ${active ? 'border-current text-white' : 'border-transparent text-white/40 hover:text-white/70'}`}
        >
            {children}
        </button>
    );
}

function BackArrowIcon() {
    return (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
        </svg>
    );
}

function EmptyState({ message }) {
    return <div className="flex h-72 items-center justify-center text-sm text-white/40">{message}</div>;
}

export default function DriverDetail() {
    const { id } = useParams();
    const { refreshKey, pollingTick, drivers } = useOutletContext();
    const driverName = drivers.find((driver) => driver.id === id)?.name || 'Default Driver';
    const driverId = id || DEFAULT_DRIVER_ID;

    const [activeTab, setActiveTab] = useState('overview');
    const [page, setPage] = useState(1);
    const [riskFilter, setRiskFilter] = useState('all');
    const [fromDate, setFromDate] = useState(toDateInputValue(29));
    const [toDate, setToDate] = useState(toDateInputValue(0));

    const summaryQuery = useApi(`/api/drivers/${driverId}/summary`, { initialData: null }, [refreshKey, pollingTick, driverId]);
    const allAlertsQuery = useApi(`/api/drivers/${driverId}/alerts?limit=10000`, { initialData: [] }, [refreshKey, pollingTick, driverId]);
    const historyQuery = useApi(
        `/api/drivers/${driverId}/alerts?from=${encodeURIComponent(fromDate)}&to=${encodeURIComponent(toDate)}&limit=10000`,
        { initialData: [] },
        [refreshKey, pollingTick, driverId, fromDate, toDate]
    );
    const healthQuery = useApi(`/api/drivers/${driverId}/health?days=7`, { initialData: null }, [refreshKey, pollingTick, driverId]);

    const alerts = allAlertsQuery.data || [];
    const historyAlerts = historyQuery.data || [];

    useEffect(() => {
        setPage(1);
    }, [fromDate, toDate, riskFilter, activeTab]);

    const latestAlert = alerts[0] || null;
    const latestScore = latestAlert ? Number(latestAlert.riskScore || 0) : 0;
    const sessionCount = useMemo(() => {
        const dates = new Set(alerts.map((alert) => String(alert.timestamp || '').slice(0, 10)).filter(Boolean));
        return dates.size;
    }, [alerts]);

    const overviewTrend = useMemo(() => {
        const grouped = groupAlertsByDay(alerts);
        const range = buildDateSeries(30);

        return range.map((date) => ({
            date,
            totalAlerts: grouped.get(date) || 0
        }));
    }, [alerts]);

    const riskDistributionData = useMemo(() => {
        const distribution = summaryQuery.data?.riskDistribution || {
            safe: 0,
            mild: 0,
            warning: 0,
            high: 0,
            critical: 0
        };

        return RISK_LEVELS.map((level) => ({
            level: level.toUpperCase(),
            count: distribution[level] || 0,
            fill: RISK_COLORS[level]
        }));
    }, [summaryQuery.data]);

    const topTrigger = summaryQuery.data?.topTriggers?.[0]?.name || 'No alerts yet';
    const peakHour = useMemo(() => {
        const hourly = new Array(24).fill(0);
        for (const alert of alerts) {
            const parsed = new Date(String(alert.timestamp || '').replace(' ', 'T'));
            if (!Number.isNaN(parsed.getTime())) {
                hourly[parsed.getHours()] += 1;
            }
        }

        const peakValue = Math.max(...hourly);
        const peakIndex = hourly.indexOf(peakValue);
        return peakValue > 0 ? peakIndex : null;
    }, [alerts]);

    const filteredHistory = useMemo(() => {
        if (riskFilter === 'all') {
            return historyAlerts;
        }

        return historyAlerts.filter((alert) => getRiskLevelFromScore(alert.riskScore) === riskFilter);
    }, [historyAlerts, riskFilter]);

    const paginatedHistory = useMemo(() => {
        const pageSize = 25;
        const start = (page - 1) * pageSize;
        return filteredHistory.slice(start, start + pageSize);
    }, [filteredHistory, page]);

    const riskDistributionTotal = riskDistributionData.reduce((total, item) => total + item.count, 0);
    const currentOverviewStatus = latestAlert ? getRiskLevelFromScore(latestScore) : 'safe';
    const historyPageCount = Math.max(1, Math.ceil(filteredHistory.length / 25));
    const tabAccent = RISK_COLORS[currentOverviewStatus] || RISK_COLORS.safe;
    const riskDistributionShare = riskDistributionData.reduce((total, item) => total + item.count, 0);

    const miniStats = [
        {
            label: 'Average Risk Score',
            value: summaryQuery.data ? summaryQuery.data.averageRiskScore.toFixed(1) : '—'
        },
        {
            label: 'Total Alerts',
            value: summaryQuery.data ? summaryQuery.data.totalAlerts : '—'
        },
        {
            label: 'Most Common Trigger',
            value: summaryQuery.data?.topTriggers?.[0]?.name || '—'
        },
        {
            label: 'Peak Alert Hour',
            value: peakHour === null ? '—' : `${String(peakHour).padStart(2, '0')}:00`
        }
    ];

    const exportCsv = () => {
        const csv = alertsToCsv(filteredHistory);
        const safeName = driverName.replace(/\s+/g, '_').toLowerCase();
        downloadCsv(`${safeName}_alerts.csv`, csv);
    };

    return (
        <div className="space-y-4">
            <div
                className="dashboard-hero flex min-h-[96px] items-center rounded-[20px] p-5 md:p-6"
                style={{
                    background:
                        currentOverviewStatus === 'critical'
                            ? 'linear-gradient(135deg, rgba(220,38,38,0.08) 0%, rgba(15,32,64,0.4) 48%, rgba(8,11,20,0.2) 100%)'
                            : currentOverviewStatus === 'high' || currentOverviewStatus === 'warning'
                                ? 'linear-gradient(135deg, rgba(249,115,22,0.08) 0%, rgba(15,32,64,0.4) 48%, rgba(8,11,20,0.2) 100%)'
                                : 'linear-gradient(135deg, rgba(30,58,95,0.6) 0%, rgba(15,32,64,0.4) 48%, rgba(8,11,20,0.2) 100%)'
                }}
            >
                <div className="flex w-full items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <Link to="/" className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/8 bg-white/5 text-white/70 hover:bg-white/8">
                            <BackArrowIcon />
                        </Link>
                        <div>
                            <div className="dashboard-kicker">Driver detail</div>
                            <h2 className="mt-1 font-display text-[2.25rem] font-bold text-white">{driverName}</h2>
                            <div className="mt-1 text-[0.75rem] text-white/40">
                                Last seen: <span className="text-white/70">{formatTimestamp(summaryQuery.data?.lastSessionDate || latestAlert?.timestamp)}</span>
                                <span className="mx-2 text-white/20">•</span>
                                Sessions: <span className="text-white/70">{sessionCount}</span>
                            </div>
                        </div>
                    </div>

                    <div className="motion-stagger flex items-center gap-3">
                        <div className="scale-[1.2] origin-right">
                            <RiskBadge level={currentOverviewStatus} />
                        </div>
                    </div>
                </div>
            </div>

            <div className="flex flex-wrap gap-6 border-b border-white/7">
                <TabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')}>
                    Overview
                </TabButton>
                <TabButton active={activeTab === 'history'} onClick={() => setActiveTab('history')}>
                    Alert History
                </TabButton>
                <TabButton active={activeTab === 'health'} onClick={() => setActiveTab('health')}>
                    Health Report
                </TabButton>
            </div>

            {summaryQuery.loading ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <SkeletonCard />
                    <SkeletonCard />
                    <SkeletonCard />
                    <SkeletonCard />
                </div>
            ) : summaryQuery.error ? (
                <div className="dashboard-card p-6">
                    <div className="dashboard-kicker text-red-300">Unable to load driver summary</div>
                    <div className="mt-2 text-[0.9rem] text-white/70">{summaryQuery.error.message}</div>
                    <button type="button" onClick={summaryQuery.refetch} className="dashboard-button mt-4">
                        Retry
                    </button>
                </div>
            ) : null}

            {activeTab === 'overview' ? (
                <div className="space-y-6">
                    <div className="motion-stagger grid gap-6 xl:grid-cols-[2fr_3fr]">
                        <RiskGauge score={latestScore} subtitle={latestAlert ? 'Latest alert score' : 'No recent alert data'} />

                        <div className="motion-stagger grid gap-4 md:grid-cols-2">
                            {miniStats.map((stat) => (
                                <StatCard key={stat.label} {...stat} className="h-full" />
                            ))}
                        </div>
                    </div>

                    <ChartPanel title="Risk Level Distribution" subtitle="SAFE, MILD, WARNING, HIGH, CRITICAL">
                        {riskDistributionTotal === 0 ? (
                            <EmptyState message="No alerts available to build the distribution chart." />
                        ) : (
                            <div className="p-5">
                                <div className="flex h-11 overflow-hidden rounded-xl border border-white/6 bg-white/[0.03]">
                                    {riskDistributionData.map((entry) => {
                                        const percent = riskDistributionShare > 0 ? (entry.count / riskDistributionShare) * 100 : 0;
                                        return (
                                            <div
                                                key={entry.level}
                                                className="flex h-full items-center justify-center text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-white"
                                                style={{ width: `${percent}%`, backgroundColor: entry.fill }}
                                            >
                                                {percent >= 12 ? `${entry.level} ${Math.round(percent)}%` : null}
                                            </div>
                                        );
                                    })}
                                </div>

                                <div className="mt-4 flex flex-wrap gap-2">
                                    {riskDistributionData.map((entry) => {
                                        const percent = riskDistributionShare > 0 ? (entry.count / riskDistributionShare) * 100 : 0;
                                        return (
                                            <div key={entry.level} className="inline-flex items-center gap-2 rounded-full border border-white/6 bg-white/[0.03] px-3 py-1 text-[0.72rem] text-white/55">
                                                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.fill }} />
                                                <span>{entry.level}</span>
                                                <span className="text-white/35">{Math.round(percent)}%</span>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </ChartPanel>

                    <ChartPanel title="Daily Alert Trend" subtitle="Last 30 days for this driver">
                        {overviewTrend.every((item) => item.totalAlerts === 0) ? (
                            <EmptyState message="No daily trend data available yet." />
                        ) : (
                            <div className="h-80">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={overviewTrend} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                                        <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                                        <XAxis dataKey="date" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                        <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} allowDecimals={false} />
                                        <Tooltip
                                            contentStyle={{
                                                background: '#11141d',
                                                border: '1px solid rgba(255,255,255,0.08)',
                                                borderRadius: 12,
                                                color: '#fff'
                                            }}
                                        />
                                        <Line type="monotone" dataKey="totalAlerts" stroke="#f97316" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        )}
                    </ChartPanel>
                </div>
            ) : null}

            {activeTab === 'history' ? (
                <div className="space-y-4">
                    <div className="dashboard-card p-5">
                        <div className="grid gap-4 lg:grid-cols-[repeat(2,minmax(0,1fr))_220px_auto] lg:items-end">
                            <label className="space-y-2 text-sm text-white/70">
                                <span className="text-xs uppercase tracking-[0.04em] text-white/40">From</span>
                                <input
                                    type="date"
                                    className="dashboard-input"
                                    value={fromDate}
                                    onChange={(event) => setFromDate(event.target.value)}
                                />
                            </label>

                            <label className="space-y-2 text-sm text-white/70">
                                <span className="text-xs uppercase tracking-[0.04em] text-white/40">To</span>
                                <input
                                    type="date"
                                    className="dashboard-input"
                                    value={toDate}
                                    onChange={(event) => setToDate(event.target.value)}
                                />
                            </label>

                            <label className="space-y-2 text-sm text-white/70">
                                <span className="text-xs uppercase tracking-[0.04em] text-white/40">Risk Level</span>
                                <select
                                    className="dashboard-input"
                                    value={riskFilter}
                                    onChange={(event) => setRiskFilter(event.target.value)}
                                >
                                    <option value="all">All</option>
                                    <option value="mild">MILD</option>
                                    <option value="warning">WARNING</option>
                                    <option value="high">HIGH</option>
                                    <option value="critical">CRITICAL</option>
                                </select>
                            </label>

                            <button type="button" onClick={exportCsv} className="dashboard-button">
                                Export CSV
                            </button>
                        </div>
                    </div>

                    <AlertTable
                        alerts={filteredHistory}
                        loading={historyQuery.loading}
                        error={historyQuery.error}
                        page={page}
                        onPageChange={setPage}
                        onRetry={historyQuery.refetch}
                        onExport={exportCsv}
                        emptyMessage="No alerts found for this driver in the selected range."
                    />
                </div>
            ) : null}

            {activeTab === 'health' ? (
                <div className="space-y-4">
                    <div className="rounded-2xl border border-white/8 bg-white/[0.04] px-5 py-4 text-[0.9rem] text-slate-300">
                        This analysis is for informational purposes only and does not constitute a medical diagnosis. Consult a qualified professional for any health concerns.
                    </div>

                    {healthQuery.loading ? (
                        <div className="motion-stagger grid gap-4 md:grid-cols-2">
                            <SkeletonCard />
                            <SkeletonCard />
                            <SkeletonCard />
                            <SkeletonCard />
                        </div>
                    ) : healthQuery.error ? (
                        <div className="dashboard-card p-6">
                            <div className="text-sm font-semibold uppercase tracking-[0.2em] text-red-300">Unable to load health report</div>
                            <div className="mt-2 text-sm text-white/70">{healthQuery.error.message}</div>
                            <button type="button" onClick={healthQuery.refetch} className="dashboard-button mt-4">
                                Retry
                            </button>
                        </div>
                    ) : (
                        <div className="grid gap-4 md:grid-cols-2">
                            <HealthCard
                                label="Sleep Apnea Risk"
                                icon="SA"
                                score={healthQuery.data?.sleepApnea?.score || 0}
                                severity={healthQuery.data?.sleepApnea?.severity || 'not_detected'}
                                description="Clusters of eye closure alerts over short windows."
                            />
                            <HealthCard
                                label="Chronic Fatigue"
                                icon="CF"
                                score={healthQuery.data?.chronicFatigue?.score || 0}
                                severity={healthQuery.data?.chronicFatigue?.severity || 'not_detected'}
                                description="Persistent drowsiness patterns across multiple days."
                            />
                            <HealthCard
                                label="Sudden Behavioral Change"
                                icon="SC"
                                score={healthQuery.data?.suddenChange?.score || 0}
                                severity={healthQuery.data?.suddenChange?.severity || 'not_detected'}
                                description="Alert frequency increased in the later half of the dataset."
                            />
                            <HealthCard
                                label="Time-Based Pattern"
                                icon="TB"
                                score={healthQuery.data?.timePattern?.score || 0}
                                severity={healthQuery.data?.timePattern?.severity || 'not_detected'}
                                description={healthQuery.data?.timePattern?.peakHour === null ? 'No hourly concentration detected yet.' : `Peak hour: ${String(healthQuery.data.timePattern.peakHour).padStart(2, '0')}:00`}
                            />
                        </div>
                    )}
                </div>
            ) : null}
        </div>
    );
}
