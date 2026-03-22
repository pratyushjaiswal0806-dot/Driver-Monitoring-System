import { formatTimestamp } from '../utils/formatters';

function MenuIcon() {
    return (
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M4 6h16" />
            <path d="M4 12h16" />
            <path d="M4 18h16" />
        </svg>
    );
}

function RefreshIcon() {
    return (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 12a8 8 0 1 1-2.34-5.66" />
            <path d="M20 4v6h-6" />
        </svg>
    );
}

export default function Navbar({ appName = 'Driver Monitoring System', title, lastUpdated, onRefresh, onMenuToggle }) {
    const breadcrumbTitle = title === 'Fleet Overview' || title === 'Not Found' ? title : `Fleet Overview › ${title}`;

    return (
        <header className="sticky top-0 z-50 h-14 w-full border-b border-white/6 bg-[rgba(8,11,20,0.85)] shadow-[0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-[20px]">
            <div className="relative flex h-14 items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
                <div className="flex min-w-0 items-center gap-3 md:flex-1">
                    <button
                        type="button"
                        onClick={onMenuToggle}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/8 bg-white/5 text-white/70 md:hidden"
                        aria-label="Toggle navigation"
                    >
                        <MenuIcon />
                    </button>

                    <div className="min-w-0">
                        <div className="hidden md:block dashboard-kicker">{appName}</div>
                        <h1 className="hidden truncate font-display text-[1.125rem] font-semibold text-white md:block">{breadcrumbTitle}</h1>
                    </div>
                </div>

                <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 md:hidden">
                    <h1 className="truncate text-center font-display text-[1.125rem] font-semibold text-white">{title}</h1>
                </div>

                <div className="flex items-center gap-3">
                    <div className="hidden items-center gap-3 md:flex">
                        <div className="text-right">
                            <div className="dashboard-kicker">Last updated</div>
                            <div className="text-[0.75rem] text-white/60">{formatTimestamp(lastUpdated)}</div>
                        </div>

                        <div className="h-4 w-px bg-white/8" />
                    </div>

                    <button
                        type="button"
                        onClick={onRefresh}
                        className="navbar-refresh inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/8 bg-white/5 text-white/70 hover:border-white/15 hover:bg-white/8"
                        aria-label="Refresh data"
                    >
                        <RefreshIcon />
                    </button>
                </div>
            </div>
        </header>
    );
}
