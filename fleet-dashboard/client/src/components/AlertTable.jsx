import RiskBadge from './RiskBadge';
import { formatTimestamp, getRiskColor } from '../utils/formatters';

function PaginationButton({ children, onClick, disabled, active = false }) {
    return (
        <button
            type="button"
            onClick={onClick}
            disabled={disabled}
            className={`flex h-8 w-8 items-center justify-center rounded-lg border text-[0.75rem] font-semibold transition ${active ? 'border-[rgba(59,130,246,0.3)] bg-[rgba(59,130,246,0.2)] text-[#60a5fa]' : 'border-white/8 bg-white/5 text-white/60 hover:bg-white/8 hover:text-white/80'} ${disabled ? 'cursor-not-allowed opacity-30' : ''}`}
        >
            {children}
        </button>
    );
}

function getPageItems(totalPages, currentPage) {
    if (totalPages <= 7) {
        return Array.from({ length: totalPages }, (_, index) => index + 1);
    }

    const items = [1];
    const start = Math.max(2, currentPage - 1);
    const end = Math.min(totalPages - 1, currentPage + 1);

    if (start > 2) {
        items.push('ellipsis-start');
    }

    for (let pageNumber = start; pageNumber <= end; pageNumber += 1) {
        items.push(pageNumber);
    }

    if (end < totalPages - 1) {
        items.push('ellipsis-end');
    }

    items.push(totalPages);
    return items;
}

export default function AlertTable({
    alerts = [],
    loading = false,
    error = null,
    page = 1,
    pageSize = 25,
    onPageChange,
    onRetry,
    onExport,
    emptyMessage = 'No alerts found for this driver in the selected range.'
}) {
    const totalPages = Math.max(1, Math.ceil(alerts.length / pageSize));
    const safePage = Math.min(Math.max(1, page), totalPages);
    const startIndex = (safePage - 1) * pageSize;
    const visibleRows = alerts.slice(startIndex, startIndex + pageSize);

    if (loading) {
        return (
            <div className="dashboard-card overflow-hidden p-5">
                <div className="space-y-3">
                    <div className="h-[14px] w-40 rounded-full bg-white/6" />
                    <div className="h-[42px] rounded-[10px] bg-white/6" />
                    <div className="h-[42px] rounded-[10px] bg-white/6" />
                    <div className="h-[42px] rounded-[10px] bg-white/6" />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="dashboard-card p-6">
                <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5 text-red-100">
                    <div className="text-sm font-semibold uppercase tracking-[0.2em]">Unable to load alerts</div>
                    <div className="mt-2 text-sm text-red-100/80">{error.message || 'Something went wrong while fetching alerts.'}</div>
                    <button type="button" onClick={onRetry} className="dashboard-button mt-4 border-red-400/30 bg-red-500/10 text-red-100">
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-card overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-white/6 bg-white/[0.03] p-5 md:flex-row md:items-center md:justify-between">
                <div>
                    <div className="text-[0.875rem] font-semibold text-white">Alert History</div>
                    <div className="mt-1 text-[0.75rem] text-white/40">{alerts.length} filtered alert{alerts.length === 1 ? '' : 's'}</div>
                </div>

                <button type="button" onClick={onExport} className="dashboard-button self-start md:self-auto">
                    Export CSV
                </button>
            </div>

            {alerts.length === 0 ? (
                <div className="p-10 text-center text-sm text-white/40">{emptyMessage}</div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="dashboard-table min-w-full text-left">
                        <thead className="text-xs uppercase tracking-[0.04em] text-white/40">
                            <tr>
                                <th className="px-4 py-3.5 font-medium">Timestamp</th>
                                <th className="px-4 py-3.5 font-medium">Risk Level</th>
                                <th className="px-4 py-3.5 font-medium">Risk Score</th>
                                <th className="px-4 py-3.5 font-medium">Triggered By</th>
                                <th className="px-4 py-3.5 font-medium">Duration</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/4">
                            {visibleRows.map((alert, index) => (
                                <tr
                                    key={alert.id}
                                    className="motion-row transition hover:bg-white/[0.025]"
                                    style={{ animationDelay: `${index * 30}ms` }}
                                >
                                    <td className="px-4 py-3.5 text-sm text-white/80">{formatTimestamp(alert.timestamp)}</td>
                                    <td className="px-4 py-3.5">
                                        <RiskBadge level={alert.riskLevel} />
                                    </td>
                                    <td className="px-4 py-3.5 font-display text-sm tabular-nums" style={{ color: getRiskColor(alert.riskLevel) }}>
                                        {Number(alert.riskScore || 0).toFixed(1)}
                                    </td>
                                    <td className="px-4 py-3.5 text-sm text-white/70">{alert.triggeredBy || 'Unknown'}</td>
                                    <td className="px-4 py-3.5 font-mono text-sm text-white/50">{Number(alert.duration || 0).toFixed(2)}s</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <div className="flex flex-col gap-3 border-t border-white/6 px-5 py-4 md:flex-row md:items-center md:justify-between">
                <div className="text-sm text-white/40">
                    Showing {alerts.length === 0 ? 0 : startIndex + 1}-{Math.min(startIndex + pageSize, alerts.length)} of {alerts.length}
                </div>

                <div className="flex items-center gap-2">
                    <PaginationButton disabled={safePage === 1} onClick={() => onPageChange(safePage - 1)}>
                        Previous
                    </PaginationButton>
                    <div className="flex items-center gap-1.5">
                        {getPageItems(totalPages, safePage).map((item) =>
                            typeof item === 'number' ? (
                                <PaginationButton key={item} active={item === safePage} onClick={() => onPageChange(item)}>
                                    {item}
                                </PaginationButton>
                            ) : (
                                <span key={item} className="flex h-8 w-8 items-center justify-center text-white/30">
                                    ·
                                </span>
                            )
                        )}
                    </div>
                    <PaginationButton disabled={safePage >= totalPages} onClick={() => onPageChange(safePage + 1)}>
                        Next
                    </PaginationButton>
                </div>
            </div>
        </div>
    );
}
