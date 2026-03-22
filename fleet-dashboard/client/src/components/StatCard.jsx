export default function StatCard({ label, value, subtext, tone = 'neutral', className = '' }) {
    const toneStyles = {
        neutral: { strip: 'bg-white/10', glow: 'bg-white/40' },
        blue: { strip: 'bg-blue-500', glow: 'bg-blue-400' },
        orange: { strip: 'bg-orange-500', glow: 'bg-orange-400' },
        red: { strip: 'bg-red-500', glow: 'bg-red-400' },
        purple: { strip: 'bg-violet-500', glow: 'bg-violet-400' }
    };

    const colors = toneStyles[tone] || toneStyles.neutral;

    return (
        <div className={`dashboard-card metric-rise group relative overflow-hidden p-5 ${className} ${tone === 'red' && Number(value) > 0 ? 'border-red-500/20 bg-[rgba(239,68,68,0.06)]' : ''}`}>
            <div className={`absolute inset-x-0 top-0 h-[3px] rounded-t-[16px] ${colors.strip}`} />
            <div className="relative z-10 flex h-full flex-col justify-between gap-4">
                <div className="flex items-center justify-between gap-3">
                    <div className="text-[0.75rem] font-medium uppercase tracking-[0.04em] text-white/40">{label}</div>
                    <span className={`h-2.5 w-2.5 rounded-full ${colors.glow} shadow-[0_0_18px_rgba(255,255,255,0.25)]`} />
                </div>
                <div className="font-display text-[1.875rem] font-bold leading-none text-white tabular-nums md:text-[2rem]">{value}</div>
                {subtext ? <div className="text-[0.75rem] text-white/40">{subtext}</div> : null}
            </div>
        </div>
    );
}
