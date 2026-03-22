import { getRiskColor, getRiskLevelFromScore, formatRiskLabel } from '../utils/formatters';

function polarToCartesian(cx, cy, radius, angleDegrees) {
    const angleInRadians = ((angleDegrees - 90) * Math.PI) / 180.0;
    return {
        x: cx + radius * Math.cos(angleInRadians),
        y: cy + radius * Math.sin(angleInRadians)
    };
}

function describeArc(cx, cy, radius, startAngle, endAngle) {
    const start = polarToCartesian(cx, cy, radius, endAngle);
    const end = polarToCartesian(cx, cy, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';

    return [
        'M', start.x, start.y,
        'A', radius, radius, 0, largeArcFlag, 0, end.x, end.y
    ].join(' ');
}

export default function RiskGauge({ score = 0, label = 'Risk Score', subtitle = 'Last known' }) {
    const normalizedScore = Math.max(0, Math.min(100, Number(score) || 0));
    const riskLevel = getRiskLevelFromScore(normalizedScore);
    const strokeColor = getRiskColor(riskLevel);
    const strokeEnd = 180 - (normalizedScore / 100) * 180;

    const trackPath = describeArc(110, 110, 78, 180, 0);
    const valuePath = describeArc(110, 110, 78, 180, strokeEnd);

    return (
        <div
            className={`dashboard-card flex h-full flex-col items-center p-6 text-center ${riskLevel === 'critical' ? 'risk-critical-pulse' : ''}`}
            style={riskLevel === 'critical' ? { boxShadow: '0 0 30px rgba(220,38,38,0.3), 0 4px 24px rgba(0,0,0,0.3)' } : undefined}
        >
            <div className="dashboard-kicker">{label}</div>

            <div className="relative mt-4 w-full max-w-[280px] rounded-[20px] bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.06),transparent_62%)] px-3 pb-1 pt-1">
                <svg viewBox="0 0 220 140" className="h-auto w-full overflow-visible">
                    <path d={trackPath} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="16" strokeLinecap="round" />
                    <path d={valuePath} fill="none" stroke={strokeColor} strokeWidth="16" strokeLinecap="round" />
                </svg>

                <div className="absolute inset-0 flex flex-col items-center justify-center pt-9 text-center">
                    <div className="flex h-24 w-24 items-center justify-center rounded-full border border-white/8 bg-[rgba(8,11,20,0.9)] shadow-[0_0_40px_rgba(0,0,0,0.28)]">
                        <div className="font-display text-[3rem] font-extrabold leading-none text-white tabular-nums">{Math.round(normalizedScore)}</div>
                    </div>
                </div>
            </div>

            <div className="mt-4 text-[0.78rem] uppercase tracking-[0.06em]" style={{ color: strokeColor }}>
                {formatRiskLabel(riskLevel)}
            </div>
            <div className="mt-1 text-[0.75rem] text-white/40">{subtitle}</div>
        </div>
    );
}
