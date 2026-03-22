import { formatSeverity, getSeverityColor } from '../utils/formatters';

export default function HealthCard({ label, icon, score = 0, severity = 'not_detected', description = '' }) {
    const color = getSeverityColor(severity);
    const percent = Math.round(Math.max(0, Math.min(1, Number(score) || 0)) * 100);

    return (
        <div className="dashboard-card p-5">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <div className="flex items-center gap-3">
                        <div
                            className="flex h-11 w-11 items-center justify-center rounded-2xl text-sm font-bold transition-transform duration-300 hover:scale-105"
                            style={{ backgroundColor: `${color}22`, color }}
                        >
                            {icon}
                        </div>
                        <div>
                            <div className="text-base font-semibold text-white">{label}</div>
                            <div className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">{formatSeverity(severity)}</div>
                        </div>
                    </div>
                </div>

                <div className="text-right text-sm font-semibold text-slate-300">{percent}%</div>
            </div>

            <div className="mt-5 h-[6px] rounded-full bg-white/7">
                <div
                    className="health-progress-fill h-[6px] rounded-full"
                    style={{ width: `${percent}%`, background: `linear-gradient(90deg, ${color}aa 0%, ${color} 100%)`, boxShadow: `0 0 18px ${color}66` }}
                />
            </div>

            {description ? <div className="mt-4 text-sm text-slate-400">{description}</div> : null}
        </div>
    );
}
