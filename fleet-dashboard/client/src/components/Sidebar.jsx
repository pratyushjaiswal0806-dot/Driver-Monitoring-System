import { Link, NavLink } from 'react-router-dom';

import { formatDriverLastSeen, getRiskColor } from '../utils/formatters';
import SkeletonCard from './SkeletonCard';

function ShieldIcon() {
    return (
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3l7 4v5c0 5-3 8-7 9-4-1-7-4-7-9V7l7-4z" />
            <path d="M9 12l2 2 4-5" />
        </svg>
    );
}

function HomeIcon() {
    return (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 11l9-8 9 8" />
            <path d="M5 10v10h14V10" />
        </svg>
    );
}

function ChartIcon() {
    return (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 19V5" />
            <path d="M8 19v-7" />
            <path d="M12 19v-3" />
            <path d="M16 19v-11" />
            <path d="M20 19v-8" />
        </svg>
    );
}

function DriverDot({ level }) {
    const color = getRiskColor(level || 'safe');
    return <span className="mt-1 h-2.5 w-2.5 rounded-full shadow-[0_0_14px_rgba(255,255,255,0.18)]" style={{ backgroundColor: color }} />;
}

export default function Sidebar({ open, onClose, drivers = [], loading = false }) {
    return (
        <>
            <div
                className={`fixed inset-0 z-30 bg-black/60 transition-opacity duration-300 md:hidden ${open ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
                onClick={onClose}
                aria-hidden="true"
            />

            <aside
                className={`fixed left-0 top-0 z-40 h-full w-full border-r border-white/6 bg-[rgba(8,11,20,0.95)] text-white/90 shadow-2xl shadow-black/50 backdrop-blur-[24px] transition-transform duration-300 md:w-[240px] md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}
            >
                <div className="flex h-full flex-col font-display tracking-tight">
                    <div className="border-b border-white/6 px-4 py-5">
                        <div className="flex items-center gap-3 rounded-2xl border border-white/7 bg-white/[0.03] px-3 py-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-[linear-gradient(135deg,#1e3a5f_0%,#0f2040_100%)] text-white/90 shadow-[0_0_16px_rgba(59,130,246,0.2)]">
                                <ShieldIcon />
                            </div>
                            <div className="min-w-0 flex-1">
                                <div className="text-[0.9rem] font-bold text-white">Sentinel Lens</div>
                                <div className="mt-0.5 text-[0.65rem] uppercase tracking-[0.06em] text-white/35">Driver Monitoring System</div>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="h-1.5 w-1.5 rounded-full bg-[#22c55e] shadow-[0_0_6px_rgba(34,197,94,0.6)] animate-pulseGlow" />
                                <span className="text-[0.64rem] uppercase tracking-[0.12em] text-white/30">Live sync</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto px-3 py-4 scrollbar-thin md:px-3">
                        <nav>
                            <div className="px-1 pb-1 pt-3 text-xs uppercase tracking-[0.04em] text-white/40">Navigation</div>
                            <NavLink
                                to="/"
                                end
                                className={({ isActive }) => `sidebar-nav-link flex h-9 items-center gap-2.5 rounded-[10px] border-l-2 px-3 text-[0.8rem] font-medium ${isActive ? 'border-l-[#3b82f6] bg-[rgba(59,130,246,0.12)] text-[#60a5fa]' : 'border-l-transparent text-white/45 hover:bg-white/5 hover:text-white/75'}`}
                            >
                                <HomeIcon />
                                Fleet Overview
                            </NavLink>

                            <NavLink
                                to="/analytics"
                                className={({ isActive }) => `sidebar-nav-link mt-1 flex h-9 items-center gap-2.5 rounded-[10px] border-l-2 px-3 text-[0.8rem] font-medium ${isActive ? 'border-l-[#3b82f6] bg-[rgba(59,130,246,0.12)] text-[#60a5fa]' : 'border-l-transparent text-white/45 hover:bg-white/5 hover:text-white/75'}`}
                            >
                                <ChartIcon />
                                Analytics
                            </NavLink>
                        </nav>

                        <div className="mt-6">
                            <div className="px-1 pb-1 pt-3 text-xs uppercase tracking-[0.04em] text-white/40">Drivers</div>

                            <div className="space-y-2">
                                {loading ? (
                                    <div className="space-y-3">
                                        <SkeletonCard />
                                        <SkeletonCard />
                                    </div>
                                ) : null}

                                {!loading && drivers.length === 0 ? (
                                    <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4 text-sm text-[#c6c6cd]">
                                        No drivers found yet.
                                    </div>
                                ) : null}

                                {drivers.map((driver) => (
                                    <NavLink
                                        key={driver.id}
                                        to={`/drivers/${driver.id}`}
                                        className={({ isActive }) => `driver-row block rounded-[10px] border-l-2 px-3 py-3 ${isActive ? 'bg-white/6 text-white' : 'border-l-transparent bg-transparent hover:bg-white/4'}`}
                                    >
                                        <div className="flex items-start gap-3">
                                            <DriverDot level={driver.currentRiskLevel} />
                                            <div className="min-w-0 flex-1">
                                                <div className="truncate text-[0.8rem] font-medium text-white">{driver.name}</div>
                                                <div className="mt-0.5 text-[0.68rem] text-white/35">{formatDriverLastSeen(driver.lastSeen)}</div>
                                                <div className="mt-2 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-white/7 px-2 text-[0.68rem] font-semibold uppercase tracking-[0.05em] text-white/75">
                                                    {driver.totalAlerts || 0}
                                                </div>
                                            </div>
                                        </div>
                                    </NavLink>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="mt-auto border-t border-white/6 px-4 py-3">
                        <div className="flex items-center gap-2 text-[0.68rem] italic text-white/20">
                            <ShieldIcon />
                            <span>No live video feed</span>
                        </div>
                    </div>
                </div>
            </aside>
        </>
    );
}
