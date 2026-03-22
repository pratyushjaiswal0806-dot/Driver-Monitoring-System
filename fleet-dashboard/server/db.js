import { DatabaseSync } from 'node:sqlite';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const DEFAULT_DRIVER_ID = 'default-driver';
const DEFAULT_DRIVER_NAME = 'Default Driver';
const SAFE_MAX = 20;
const MILD_MAX = 40;
const WARNING_MAX = 60;
const HIGH_MAX = 80;

function resolveDatabasePath() {
    const serverDir = path.dirname(fileURLToPath(import.meta.url));
    const dashboardRoot = path.resolve(serverDir, '..');
    const repoRoot = path.resolve(dashboardRoot, '..');

    const candidates = [
        path.resolve(repoRoot, 'logs', 'alerts.db'),
        path.resolve(dashboardRoot, 'server', 'alerts.db'),
        path.resolve(process.cwd(), 'logs', 'alerts.db'),
        path.resolve(process.cwd(), 'server', 'alerts.db')
    ];

    const found = candidates.find((candidate) => fs.existsSync(candidate));
    if (found) {
        return found;
    }

    return candidates[0];
}

const dbPath = resolveDatabasePath();
if (!fs.existsSync(dbPath)) {
    throw new Error(
        `SQLite database not found at ${dbPath}. Copy alerts.db into fleet-dashboard/server/alerts.db before starting the API.`
    );
}

const database = new DatabaseSync(dbPath);
const schemaColumns = new Set(
    database.prepare("PRAGMA table_info(alerts)").all().map((column) => column.name)
);

const durationColumn = schemaColumns.has('duration_sec')
    ? 'duration_sec'
    : schemaColumns.has('duration')
        ? 'duration'
        : '0';

function isKnownDriverId(driverId) {
    return !driverId || driverId === DEFAULT_DRIVER_ID;
}

function normalizeBoundary(value, end = false) {
    if (!value) {
        return null;
    }

    const normalized = String(value).replace('T', ' ');
    if (normalized.length === 10) {
        return end ? `${normalized} 23:59:59.999` : `${normalized} 00:00:00.000`;
    }

    return normalized;
}

function buildWhereClause({ from, to } = {}) {
    const clauses = [];
    const params = [];

    const start = normalizeBoundary(from, false);
    const end = normalizeBoundary(to, true);

    if (start) {
        clauses.push('timestamp >= ?');
        params.push(start);
    }

    if (end) {
        clauses.push('timestamp <= ?');
        params.push(end);
    }

    const whereClause = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
    return { whereClause, params };
}

function fetchAlerts({ from, to, limit = 100, offset = 0 } = {}) {
    const { whereClause, params } = buildWhereClause({ from, to });
    const safeLimit = Math.max(1, Number(limit) || 100);
    const safeOffset = Math.max(0, Number(offset) || 0);

    const statement = database.prepare(`
    SELECT
      id,
      timestamp,
      risk_level,
      risk_score,
      triggered_by,
      ${durationColumn} AS duration
    FROM alerts
    ${whereClause}
    ORDER BY timestamp DESC, id DESC
    LIMIT ? OFFSET ?
  `);

    return statement.all(...params, safeLimit, safeOffset);
}

function fetchAllAlerts({ from, to } = {}) {
    const { whereClause, params } = buildWhereClause({ from, to });
    const statement = database.prepare(`
    SELECT
      id,
      timestamp,
      risk_level,
      risk_score,
      triggered_by,
      ${durationColumn} AS duration
    FROM alerts
    ${whereClause}
    ORDER BY timestamp DESC, id DESC
  `);

    return statement.all(...params);
}

function parseTimestampValue(timestamp) {
    const normalized = String(timestamp || '').replace(' ', 'T');
    const parsed = new Date(normalized);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDateKey(timestamp) {
    if (!timestamp) {
        return null;
    }

    return String(timestamp).slice(0, 10);
}

function getRiskLevelFromScore(score) {
    const value = Number(score) || 0;
    if (value < SAFE_MAX) {
        return 'safe';
    }
    if (value < MILD_MAX) {
        return 'mild';
    }
    if (value < WARNING_MAX) {
        return 'warning';
    }
    if (value < HIGH_MAX) {
        return 'high';
    }
    return 'critical';
}

function normalizeTriggerName(triggerName) {
    return String(triggerName || '')
        .trim()
        .replace(/[_-]+/g, ' ')
        .split(/\s+/)
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ');
}

function splitTriggers(triggeredBy) {
    return String(triggeredBy || '')
        .split(',')
        .map((item) => normalizeTriggerName(item))
        .filter(Boolean);
}

function countRiskDistribution(alerts) {
    const distribution = {
        safe: 0,
        mild: 0,
        warning: 0,
        high: 0,
        critical: 0
    };

    for (const alert of alerts) {
        const level = getRiskLevelFromScore(alert.risk_score);
        distribution[level] += 1;
    }

    return distribution;
}

function countTriggers(alerts) {
    const counts = new Map();

    for (const alert of alerts) {
        for (const trigger of splitTriggers(alert.triggered_by)) {
            counts.set(trigger, (counts.get(trigger) || 0) + 1);
        }
    }

    return [...counts.entries()]
        .sort((left, right) => right[1] - left[1])
        .map(([name, count]) => ({ name, count }));
}

function groupByDate(alerts) {
    const byDate = new Map();

    for (const alert of alerts) {
        const dateKey = formatDateKey(alert.timestamp);
        if (!dateKey) {
            continue;
        }

        if (!byDate.has(dateKey)) {
            byDate.set(dateKey, []);
        }

        byDate.get(dateKey).push(alert);
    }

    return byDate;
}

function addDays(dateKey, delta) {
    const date = new Date(`${dateKey}T00:00:00`);
    date.setDate(date.getDate() + delta);
    return date.toISOString().slice(0, 10);
}

function buildDateSeries(days) {
    const safeDays = Math.max(1, Number(days) || 7);
    const today = new Date().toISOString().slice(0, 10);
    const series = [];

    for (let index = safeDays - 1; index >= 0; index -= 1) {
        series.push(addDays(today, -index));
    }

    return series;
}

function calculateAverageRisk(alerts) {
    if (!alerts.length) {
        return 0;
    }

    const sum = alerts.reduce((total, alert) => total + Number(alert.risk_score || 0), 0);
    return sum / alerts.length;
}

function getLatestAlert(alerts) {
    return alerts.length ? alerts[0] : null;
}

function getDriverList() {
    const alerts = fetchAllAlerts();
    const latest = getLatestAlert(alerts);
    const latestTimestamp = latest ? latest.timestamp : null;
    const latestRiskLevel = latest ? getRiskLevelFromScore(latest.risk_score) : 'safe';

    return [
        {
            id: DEFAULT_DRIVER_ID,
            name: DEFAULT_DRIVER_NAME,
            lastSeen: latestTimestamp,
            totalAlerts: alerts.length,
            currentRiskLevel: latestRiskLevel
        }
    ];
}

function getDriverSummary(driverId = DEFAULT_DRIVER_ID) {
    if (!isKnownDriverId(driverId)) {
        return null;
    }

    const alerts = fetchAllAlerts();
    const latest = getLatestAlert(alerts);
    const riskDistribution = countRiskDistribution(alerts);
    const topTriggers = countTriggers(alerts).slice(0, 5);

    return {
        totalAlerts: alerts.length,
        averageRiskScore: Number(calculateAverageRisk(alerts).toFixed(2)),
        lastSessionDate: latest ? latest.timestamp : null,
        riskDistribution,
        topTriggers
    };
}

function getDriverAlerts(driverId = DEFAULT_DRIVER_ID, query = {}) {
    if (!isKnownDriverId(driverId)) {
        return null;
    }

    return fetchAlerts(query);
}

function getDriverHealth(driverId = DEFAULT_DRIVER_ID, days = 7) {
    if (!isKnownDriverId(driverId)) {
        return null;
    }

    const safeDays = Math.max(1, Number(days) || 7);
    const alerts = fetchAllAlerts({ from: addDays(new Date().toISOString().slice(0, 10), -(safeDays - 1)) });

    if (!alerts.length) {
        return {
            sleepApnea: { score: 0, severity: 'not_detected' },
            chronicFatigue: { score: 0, severity: 'not_detected' },
            suddenChange: { score: 0, severity: 'not_detected' },
            timePattern: { score: 0, severity: 'not_detected', peakHour: null }
        };
    }

    const severityForScore = (score) => {
        if (score <= 0) {
            return 'not_detected';
        }
        if (score < 0.4) {
            return 'low';
        }
        if (score < 0.6) {
            return 'medium';
        }
        return 'high';
    };

    const getTimestamp = (alert) => parseTimestampValue(alert.timestamp);
    const eyeCloseAlerts = alerts.filter((alert) => {
        const triggers = splitTriggers(alert.triggered_by).join(' ').toLowerCase();
        return triggers.includes('eyes closed') || triggers.includes('drowsiness');
    });

    let apneaScore = 0;
    if (eyeCloseAlerts.length >= 3) {
        let clusterWindows = 0;
        const totalWindows = Math.max(1, eyeCloseAlerts.length - 2);

        for (let index = 0; index < eyeCloseAlerts.length - 2; index += 1) {
            const first = getTimestamp(eyeCloseAlerts[index]);
            const third = getTimestamp(eyeCloseAlerts[index + 2]);
            if (first && third && (third - first) / 1000 < 300) {
                clusterWindows += 1;
            }
        }

        apneaScore = Math.min(clusterWindows / totalWindows, 1);
    }

    const drowsyAlerts = alerts.filter((alert) => {
        const triggerText = String(alert.triggered_by || '').toLowerCase();
        return triggerText.includes('drowsiness') || triggerText.includes('eyes_closed');
    });
    const drowsyRatio = drowsyAlerts.length / Math.max(alerts.length, 1);
    const drowsyDates = new Set(drowsyAlerts.map((alert) => formatDateKey(alert.timestamp)).filter(Boolean));
    const fatigueScore = Math.min((drowsyRatio * 0.6) + ((drowsyDates.size / 7) * 0.4), 1);

    const midpoint = Math.floor(alerts.length / 2);
    const firstHalf = alerts.slice(midpoint);
    const secondHalf = alerts.slice(0, midpoint);
    const firstSpanHours = Math.max(0.1, spanHours(firstHalf));
    const secondSpanHours = Math.max(0.1, spanHours(secondHalf));
    const firstRate = firstHalf.length / firstSpanHours;
    const secondRate = secondHalf.length / secondSpanHours;
    const changeRatio = firstRate > 0 ? secondRate / firstRate : 1;
    const suddenChangeScore = Math.min(Math.max((changeRatio - 1) / 2, 0), 1);

    const hourCounts = new Map();
    for (const alert of alerts) {
        const parsed = getTimestamp(alert);
        if (!parsed) {
            continue;
        }

        const hour = parsed.getHours();
        hourCounts.set(hour, (hourCounts.get(hour) || 0) + 1);
    }

    let peakHour = null;
    let maxHourCount = 0;
    for (const [hour, count] of hourCounts.entries()) {
        if (count > maxHourCount) {
            peakHour = hour;
            maxHourCount = count;
        }
    }

    const totalAlerts = alerts.length;
    const concentration = totalAlerts > 0 ? maxHourCount / totalAlerts : 0;
    const timePatternScore = concentration > 0.3 ? Math.min(Math.max((concentration - 0.3) / 0.7, 0), 1) : 0;

    return {
        sleepApnea: {
            score: Number(apneaScore.toFixed(3)),
            severity: severityForScore(apneaScore)
        },
        chronicFatigue: {
            score: Number(fatigueScore.toFixed(3)),
            severity: severityForScore(fatigueScore)
        },
        suddenChange: {
            score: Number(suddenChangeScore.toFixed(3)),
            severity: severityForScore(suddenChangeScore)
        },
        timePattern: {
            score: Number(timePatternScore.toFixed(3)),
            severity: severityForScore(timePatternScore),
            peakHour
        }
    };
}

function spanHours(alerts) {
    if (alerts.length < 2) {
        return 1;
    }

    const first = parseTimestampValue(alerts[0].timestamp);
    const last = parseTimestampValue(alerts[alerts.length - 1].timestamp);
    if (!first || !last) {
        return 1;
    }

    return Math.max((last - first) / 3600000, 0.1);
}

function getFleetOverview() {
    const today = new Date().toISOString().slice(0, 10);
    const todayStart = `${today} 00:00:00.000`;
    const todayEnd = `${today} 23:59:59.999`;

    const allAlerts = fetchAllAlerts();
    const todayAlerts = fetchAllAlerts({ from: todayStart, to: todayEnd });
    const latest = getLatestAlert(allAlerts);
    const latestRiskLevel = latest ? getRiskLevelFromScore(latest.risk_score) : 'safe';

    return {
        totalDrivers: 1,
        activeToday: todayAlerts.length > 0 ? 1 : 0,
        totalAlertsToday: todayAlerts.length,
        criticalAlertsToday: todayAlerts.filter((alert) => Number(alert.risk_score) >= HIGH_MAX).length,
        averageRiskScore: Number(calculateAverageRisk(todayAlerts).toFixed(2)),
        driverStatuses: [
            {
                driverId: DEFAULT_DRIVER_ID,
                name: DEFAULT_DRIVER_NAME,
                currentRiskLevel: latestRiskLevel,
                lastSeen: latest ? latest.timestamp : null,
                alertsToday: todayAlerts.length
            }
        ]
    };
}

function getAnalyticsTrends(days = 7) {
    const safeDays = Math.max(1, Number(days) || 7);
    const today = new Date().toISOString().slice(0, 10);
    const fromDate = addDays(today, -(safeDays - 1));
    const from = `${fromDate} 00:00:00.000`;
    const to = `${today} 23:59:59.999`;
    const alerts = fetchAllAlerts({ from, to });
    const byDate = groupByDate(alerts);
    const series = buildDateSeries(safeDays);

    return series.map((date) => {
        const alertsForDate = byDate.get(date) || [];
        const totalAlerts = alertsForDate.length;
        const averageRiskScore = Number(calculateAverageRisk(alertsForDate).toFixed(2));
        const criticalCount = alertsForDate.filter((alert) => Number(alert.risk_score) >= HIGH_MAX).length;

        return {
            date,
            totalAlerts,
            averageRiskScore,
            criticalCount
        };
    });
}

function getAlertsByRange({ from, to, limit, offset } = {}) {
    return fetchAlerts({ from, to, limit, offset });
}

function getTopTriggers(alerts, limit = 10) {
    return countTriggers(alerts).slice(0, limit);
}

export {
    DEFAULT_DRIVER_ID,
    DEFAULT_DRIVER_NAME,
    database,
    getAlertsByRange,
    getAnalyticsTrends,
    getDriverAlerts,
    getDriverHealth,
    getDriverList,
    getDriverSummary,
    getFleetOverview,
    getRiskLevelFromScore,
    getTopTriggers,
    isKnownDriverId,
    normalizeTriggerName,
    parseTimestampValue,
    splitTriggers
};
