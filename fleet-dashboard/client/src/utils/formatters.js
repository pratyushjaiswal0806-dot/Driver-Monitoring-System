export const DEFAULT_DRIVER_ID = 'default-driver';

export const RISK_LEVELS = ['safe', 'mild', 'warning', 'high', 'critical'];

export const RISK_COLORS = {
    safe: '#22c55e',
    mild: '#eab308',
    warning: '#f97316',
    high: '#ef4444',
    critical: '#7f1d1d'
};

export const SEVERITY_LABELS = {
    not_detected: 'NOT DETECTED',
    low: 'LOW',
    medium: 'MEDIUM',
    high: 'HIGH'
};

export const SEVERITY_COLORS = {
    not_detected: '#64748b',
    low: '#22c55e',
    medium: '#f97316',
    high: '#ef4444'
};

function safeDate(timestamp) {
    if (!timestamp) {
        return null;
    }

    const normalized = String(timestamp).replace(' ', 'T');
    const parsed = new Date(normalized);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatTimestamp(timestamp) {
    const parsed = safeDate(timestamp);
    if (!parsed) {
        return timestamp || 'Unknown';
    }

    return new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short'
    }).format(parsed);
}

export function formatDateOnly(timestamp) {
    const parsed = safeDate(timestamp);
    if (!parsed) {
        return timestamp ? String(timestamp).slice(0, 10) : '—';
    }

    return new Intl.DateTimeFormat('en-CA', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(parsed);
}

export function formatDriverLastSeen(timestamp) {
    if (!timestamp) {
        return 'No alerts yet';
    }

    return formatTimestamp(timestamp);
}

export function formatRiskLabel(level) {
    return String(level || 'unknown').replace(/_/g, ' ').toUpperCase();
}

export function getRiskColor(level) {
    return RISK_COLORS[String(level || 'safe').toLowerCase()] || '#64748b';
}

export function getRiskLevelFromScore(score) {
    const value = Number(score) || 0;

    if (value < 20) {
        return 'safe';
    }
    if (value < 40) {
        return 'mild';
    }
    if (value < 60) {
        return 'warning';
    }
    if (value < 80) {
        return 'high';
    }
    return 'critical';
}

export function formatTriggerName(value) {
    return String(value || '')
        .trim()
        .replace(/[_-]+/g, ' ')
        .replace(/\s+/g, ' ')
        .split(' ')
        .filter(Boolean)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

export function formatSeverity(severity) {
    return SEVERITY_LABELS[String(severity || 'not_detected').toLowerCase()] || 'NOT DETECTED';
}

export function getSeverityColor(severity) {
    return SEVERITY_COLORS[String(severity || 'not_detected').toLowerCase()] || '#64748b';
}

function escapeCsvValue(value) {
    const stringValue = value === null || value === undefined ? '' : String(value);
    if (/[",\n]/.test(stringValue)) {
        return `"${stringValue.replace(/"/g, '""')}"`;
    }
    return stringValue;
}

export function alertsToCsv(alerts) {
    const headers = ['Timestamp', 'Risk Level', 'Risk Score', 'Triggered By', 'Duration'];
    const rows = alerts.map((alert) => [
        alert.timestamp,
        formatRiskLabel(alert.riskLevel),
        Number(alert.riskScore || 0).toFixed(1),
        alert.triggeredBy,
        Number(alert.duration || 0).toFixed(2)
    ]);

    const lines = [headers, ...rows].map((row) => row.map(escapeCsvValue).join(','));
    return lines.join('\n');
}

export function downloadCsv(filename, csvText) {
    const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
}

export function groupAlertsByDay(alerts) {
    const grouped = new Map();

    for (const alert of alerts || []) {
        const dateKey = String(alert.timestamp || '').slice(0, 10);
        if (!dateKey) {
            continue;
        }

        grouped.set(dateKey, (grouped.get(dateKey) || 0) + 1);
    }

    return grouped;
}

export function groupAlertsByHour(alerts) {
    const grouped = new Array(24).fill(0);

    for (const alert of alerts || []) {
        const parsed = safeDate(alert.timestamp);
        if (!parsed) {
            continue;
        }

        grouped[parsed.getHours()] += 1;
    }

    return grouped;
}

export function groupTriggers(alerts) {
    const grouped = new Map();

    for (const alert of alerts || []) {
        const triggers = String(alert.triggeredBy || '')
            .split(',')
            .map((trigger) => formatTriggerName(trigger))
            .filter(Boolean);

        for (const trigger of triggers) {
            grouped.set(trigger, (grouped.get(trigger) || 0) + 1);
        }
    }

    return [...grouped.entries()]
        .map(([name, count]) => ({ name, count }))
        .sort((left, right) => right.count - left.count);
}

export function buildDateSeries(days) {
    const safeDays = Math.max(1, Number(days) || 7);
    const today = new Date();
    const series = [];

    for (let index = safeDays - 1; index >= 0; index -= 1) {
        const date = new Date(today);
        date.setDate(date.getDate() - index);
        series.push(date.toISOString().slice(0, 10));
    }

    return series;
}

export function formatRelativeRisk(score) {
    return `${Number(score || 0).toFixed(1)}%`;
}
