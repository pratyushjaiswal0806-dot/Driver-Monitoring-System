import { useMemo, useState } from 'react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    LabelList,
    Legend,
    Line,
    LineChart,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';
import { useOutletContext } from 'react-router-dom';

import { useApi } from '../hooks/useApi';
import SkeletonCard from '../components/SkeletonCard';
import {
    buildDateSeries,
    formatTriggerName,
    groupAlertsByHour,
    groupTriggers,
    RISK_COLORS,
    RISK_LEVELS
} from '../utils/formatters';

function ChartPanel({ title, children, subtitle = '' }) {
    return (
        <div className="dashboard-panel">
            <div className="dashboard-panel-header">
                <div>
                    <div className="dashboard-kicker">Analytics view</div>
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

function RangeButton({ active, children, onClick }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`rounded-[10px] border px-5 py-2 text-[0.82rem] font-medium transition ${active ? 'border-[rgba(59,130,246,0.3)] bg-[rgba(59,130,246,0.15)] text-[#93c5fd]' : 'border-white/8 bg-white/4 text-white/50 hover:bg-white/8 hover:text-white/80'}`}
        >
            {children}
        </button>
    );
}

export default function Analytics() {
    const { refreshKey, pollingTick } = useOutletContext();
    const [days, setDays] = useState(7);

    const trendQuery = useApi(`/api/analytics/trends?days=${days}`, { initialData: [] }, [refreshKey, pollingTick, days]);

    const range = useMemo(() => {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - (days - 1));
        return {
            from: start.toISOString().slice(0, 10),
            to: end.toISOString().slice(0, 10)
        };
    }, [days]);

    const alertsQuery = useApi(
        `/api/drivers/default-driver/alerts?from=${encodeURIComponent(range.from)}&to=${encodeURIComponent(range.to)}&limit=10000`,
        { initialData: [] },
        [refreshKey, pollingTick, range.from, range.to]
    );

    const trends = trendQuery.data || [];
    const alerts = alertsQuery.data || [];

    const pieData = useMemo(() => {
        const counts = {
            safe: 0,
            mild: 0,
            warning: 0,
            high: 0,
            critical: 0
        };

        for (const alert of alerts) {
            const raw = Number(alert.riskScore || 0);
            const key = raw < 20 ? 'safe' : raw < 40 ? 'mild' : raw < 60 ? 'warning' : raw < 80 ? 'high' : 'critical';
            counts[key] += 1;
        }

        return RISK_LEVELS.map((level) => ({
            name: level.toUpperCase(),
            value: counts[level],
            fill: RISK_COLORS[level]
        }));
    }, [alerts]);

    const hourlyData = useMemo(() => {
        const counts = groupAlertsByHour(alerts);
        return counts.map((count, hour) => ({
            hour: `${String(hour).padStart(2, '0')}:00`,
            count
        }));
    }, [alerts]);

    const triggerData = useMemo(() => {
        const grouped = groupTriggers(alerts);
        return grouped.slice(0, 10);
    }, [alerts]);

    const alertsByDay = useMemo(() => {
        const grouped = new Map();
        for (const item of trends) {
            grouped.set(item.date, item);
        }
        return buildDateSeries(days).map((date) => grouped.get(date) || {
            date,
            totalAlerts: 0,
            averageRiskScore: 0,
            criticalCount: 0
        });
    }, [trends, days]);

    return (
        <div className="space-y-4">
            <div className="dashboard-hero rounded-[20px] p-5 md:p-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <div className="dashboard-badge border-white/10 bg-white/5 text-white/55">Analytics</div>
                        <h2 className="mt-3 font-display text-[2.25rem] font-bold text-white md:text-[2.25rem]">Fleet-wide trends and patterns</h2>
                        <div className="mt-2 max-w-2xl text-[0.875rem] leading-6 text-white/45">Explore alert patterns across the selected time range and compare where risk is rising or stabilizing.</div>
                    </div>

                    <div className="motion-stagger flex flex-wrap gap-2">
                        <RangeButton active={days === 7} onClick={() => setDays(7)}>
                            Last 7 Days
                        </RangeButton>
                        <RangeButton active={days === 30} onClick={() => setDays(30)}>
                            Last 30 Days
                        </RangeButton>
                        <RangeButton active={days === 90} onClick={() => setDays(90)}>
                            Last 90 Days
                        </RangeButton>
                    </div>
                </div>
            </div>

            {(trendQuery.loading || alertsQuery.loading) ? (
                <div className="motion-stagger grid gap-4 xl:grid-cols-2">
                    <SkeletonCard className="h-72" />
                    <SkeletonCard className="h-72" />
                </div>
            ) : null}

            {(trendQuery.error || alertsQuery.error) ? (
                <div className="dashboard-card p-6">
                    <div className="dashboard-kicker text-red-300">Unable to load analytics</div>
                    <div className="mt-2 text-[0.9rem] text-slate-300">
                        {trendQuery.error?.message || alertsQuery.error?.message || 'An API request failed.'}
                    </div>
                    <button type="button" onClick={() => {
                        trendQuery.refetch();
                        alertsQuery.refetch();
                    }} className="dashboard-button mt-4">
                        Retry
                    </button>
                </div>
            ) : null}

            <div className="motion-stagger grid gap-4 xl:grid-cols-2">
                <ChartPanel title="Daily Total Alerts" subtitle="Count of alerts over the selected period">
                    {alertsByDay.every((item) => item.totalAlerts === 0) ? (
                        <EmptyChart message="No alerts available for the selected period." />
                    ) : (
                        <div className="h-80">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={alertsByDay} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
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
                                    />
                                    <Line type="monotone" dataKey="totalAlerts" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: '#3b82f6' }} activeDot={{ r: 5, fill: '#3b82f6' }} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </ChartPanel>

                <ChartPanel title="Daily Average Risk Score" subtitle="Mean risk score per day">
                    {alertsByDay.every((item) => item.averageRiskScore === 0) ? (
                        <EmptyChart message="No risk score data available for the selected period." />
                    ) : (
                        <div className="h-80">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={alertsByDay} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                                    <CartesianGrid stroke="rgba(255,255,255,0.05)" strokeDasharray="4 4" />
                                    <XAxis dataKey="date" stroke="rgba(255,255,255,0.35)" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }} />
                                    <YAxis stroke="rgba(255,255,255,0.35)" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }} domain={[0, 100]} />
                                    <Tooltip
                                        contentStyle={{
                                            background: '#1a1d2e',
                                            border: '1px solid rgba(255,255,255,0.1)',
                                            borderRadius: 8,
                                            padding: '10px 14px',
                                            color: '#fff'
                                        }}
                                    />
                                    <Line type="monotone" dataKey="averageRiskScore" stroke="#f97316" strokeWidth={2} dot={{ r: 3, fill: '#f97316' }} activeDot={{ r: 5, fill: '#f97316' }} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </ChartPanel>
            </div>

            <div className="grid gap-4 xl:grid-cols-2">
                <ChartPanel title="Fleet Risk Distribution" subtitle="All alerts in the selected period">
                    {alerts.length === 0 ? (
                        <EmptyChart message="No distribution data available yet." />
                    ) : (
                        <div className="p-5">
                            <div className="mx-auto flex h-10 w-full overflow-hidden rounded-xl border border-white/6 bg-white/[0.03]">
                                {pieData.map((entry) => {
                                    const percent = alerts.length > 0 ? (entry.value / alerts.length) * 100 : 0;
                                    const shouldLabelInside = percent >= 12;
                                    return (
                                        <div
                                            key={entry.name}
                                            className="relative flex h-full items-center justify-center text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-white"
                                            style={{ width: `${percent}%`, backgroundColor: entry.fill }}
                                        >
                                            {shouldLabelInside ? `${entry.name} ${Math.round(percent)}%` : null}
                                        </div>
                                    );
                                })}
                            </div>

                            <div className="mt-4 flex flex-wrap gap-2">
                                {pieData.map((entry) => {
                                    const percent = alerts.length > 0 ? (entry.value / alerts.length) * 100 : 0;
                                    return (
                                        <div key={entry.name} className="inline-flex items-center gap-2 rounded-full border border-white/6 bg-white/[0.03] px-3 py-1 text-[0.72rem] text-white/55">
                                            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.fill }} />
                                            <span>{entry.name}</span>
                                            <span className="text-white/35">{Math.round(percent)}%</span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </ChartPanel>

                <ChartPanel title="Hourly Alert Distribution" subtitle="Alert counts by hour of day">
                    {alerts.length === 0 ? (
                        <EmptyChart message="No hourly activity available yet." />
                    ) : (
                        <div className="h-80">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={hourlyData} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                                    <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                                    <XAxis dataKey="hour" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} interval={2} />
                                    <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} allowDecimals={false} />
                                    <Tooltip
                                        contentStyle={{
                                            background: '#11141d',
                                            border: '1px solid rgba(255,255,255,0.08)',
                                            borderRadius: 12,
                                            color: '#fff'
                                        }}
                                    />
                                    <Bar dataKey="count" radius={[10, 10, 0, 0]} fill="#8b5cf6">
                                        <LabelList dataKey="count" position="top" fill="#e5e7eb" />
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </ChartPanel>
            </div>

            <ChartPanel title="Top Alert Triggers" subtitle="Most common triggers across the fleet">
                {triggerData.length === 0 ? (
                    <EmptyChart message="No trigger data available yet." />
                ) : (
                    <div className="h-96">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={triggerData} margin={{ top: 10, right: 20, bottom: 40, left: 0 }}>
                                <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                                <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} angle={-20} textAnchor="end" interval={0} height={50} />
                                <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} allowDecimals={false} />
                                <Tooltip
                                    contentStyle={{
                                        background: '#11141d',
                                        border: '1px solid rgba(255,255,255,0.08)',
                                        borderRadius: 12,
                                        color: '#fff'
                                    }}
                                />
                                <Bar dataKey="count" radius={[10, 10, 0, 0]} fill="#8b5cf6">
                                    <LabelList dataKey="count" position="top" fill="#e5e7eb" />
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </ChartPanel>
        </div>
    );
}
