import { getRiskColor, formatRiskLabel } from '../utils/formatters';

export default function RiskBadge({ level, className = '' }) {
    const normalizedLevel = String(level || 'safe').toLowerCase();
    const color = getRiskColor(normalizedLevel);
    const isCritical = normalizedLevel === 'critical';
    const palette = {
        safe: { backgroundColor: 'rgba(34, 197, 94, 0.12)', color: '#86efac', borderColor: 'rgba(34, 197, 94, 0.18)' },
        mild: { backgroundColor: 'rgba(234, 179, 8, 0.12)', color: '#fde047', borderColor: 'rgba(234, 179, 8, 0.18)' },
        warning: { backgroundColor: 'rgba(249, 115, 22, 0.12)', color: '#fdba74', borderColor: 'rgba(249, 115, 22, 0.18)' },
        high: { backgroundColor: 'rgba(239, 68, 68, 0.12)', color: '#fca5a5', borderColor: 'rgba(239, 68, 68, 0.18)' },
        critical: { backgroundColor: 'rgba(220, 38, 38, 0.2)', color: '#fca5a5', borderColor: 'rgba(220, 38, 38, 0.25)' }
    };
    const styles = palette[normalizedLevel] || palette.safe;

    return (
        <span
            className={`inline-flex items-center gap-2 rounded-full border px-[0.625rem] py-[0.1875rem] font-body text-[0.72rem] font-semibold uppercase tracking-[0.05em] ${isCritical ? 'risk-critical-pulse' : ''} ${className}`}
            style={{ ...styles, boxShadow: isCritical ? '0 0 8px rgba(220,38,38,0.4)' : 'none' }}
        >
            <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: color }}
            />
            {formatRiskLabel(normalizedLevel)}
        </span>
    );
}
