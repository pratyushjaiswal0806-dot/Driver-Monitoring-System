"""
Health Analyzer Module
Detects health issues from historical alert patterns.
Analyzes sleep apnea, chronic fatigue, sudden changes, and time-based patterns.
"""

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any


class HealthAnalyzer:
    """
    Analyzes driver alert history to detect potential health issues.
    Queries alerts.db and returns severity scores for 4 conditions.
    """

    def __init__(self, db_path: str):
        """
        Initialize health analyzer with database path.

        Args:
            db_path: Path to logs/alerts.db file
        """
        self.db_path = db_path
        self.severity_thresholds = {
            'low': 0.4,
            'medium': 0.6,
            'high': 0.8
        }

    def analyze_patterns(self, days: int = 7, severity_threshold: float = 0.6) -> Dict[str, Any]:
        """
        Analyze alert patterns over specified days.

        Args:
            days: Number of days to analyze (default 7)
            severity_threshold: Minimum score to report issue (default 0.6 = medium concern)

        Returns:
            Dict with 'issues' list containing detected health concerns
            Each issue has: condition, severity, score, description, recommendation
        """
        try:
            alerts = self._get_alerts_by_date(days)
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to query alerts: {str(e)}',
                'issues': []
            }

        if not alerts:
            return {
                'status': 'no_data',
                'message': f'No alerts in last {days} days',
                'issues': []
            }

        # Run all detection algorithms
        issues = []

        apnea_score = self._detect_apnea(alerts)
        if apnea_score >= severity_threshold:
            issues.append({
                'condition': 'Sleep Apnea',
                'score': apnea_score,
                'severity': self._get_severity_level(apnea_score),
                'description': 'Rapid clusters of eye-closing detected. May indicate respiratory events during driving.',
                'recommendation': 'Consider sleep study and consult with sleep specialist. High risk condition.'
            })

        fatigue_score = self._detect_chronic_fatigue(alerts)
        if fatigue_score >= severity_threshold:
            issues.append({
                'condition': 'Chronic Fatigue',
                'score': fatigue_score,
                'severity': self._get_severity_level(fatigue_score),
                'description': 'Persistent drowsiness detected across multiple days. May indicate sleep debt or medical condition.',
                'recommendation': 'Improve sleep hygiene, maintain 7-9 hours nightly, and consult physician if persists.'
            })

        change_score = self._detect_sudden_change(alerts)
        if change_score >= severity_threshold:
            issues.append({
                'condition': 'Sudden Health Change',
                'score': change_score,
                'severity': self._get_severity_level(change_score),
                'description': 'Alert frequency increased significantly. May indicate developing medical condition or medication effects.',
                'recommendation': 'Monitor closely and seek medical evaluation if multiple conditions present.'
            })

        time_pattern_score = self._detect_time_pattern(alerts)
        if time_pattern_score >= severity_threshold:
            most_common_hour = self._get_most_common_hour(alerts)
            issues.append({
                'condition': 'Time-Based Pattern',
                'score': time_pattern_score,
                'severity': self._get_severity_level(time_pattern_score),
                'description': f'Drowsiness concentrated around {most_common_hour}:00. May indicate circadian rhythm issue or medication timing.',
                'recommendation': 'Avoid driving during peak drowsiness hours. Track activity timing and medications.'
            })

        return {
            'status': 'success',
            'days_analyzed': days,
            'alert_count': len(alerts),
            'issues': issues
        }

    def get_health_report(self, days: int = 7) -> str:
        """
        Generate human-readable health report.

        Args:
            days: Number of days to analyze

        Returns:
            Formatted string report suitable for console display
        """
        result = self.analyze_patterns(days)

        lines = []
        lines.append("=" * 60)
        lines.append("HEALTH ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append(
            "⚠️  DISCLAIMER: This is NOT medical advice or diagnosis.")
        lines.append(
            "Results should be discussed with a healthcare professional.")
        lines.append("")

        if result['status'] == 'no_data':
            lines.append(f"Status: {result['message']}")
            lines.append(
                "(Recommendation: Drive and generate alert data for analysis)")
            lines.append("")
        elif result['status'] == 'error':
            lines.append(f"Error: {result['message']}")
            lines.append("")
        else:
            lines.append(
                f"Analysis Period: Last {result['days_analyzed']} days")
            lines.append(f"Alerts Analyzed: {result['alert_count']}")
            lines.append("")

            if not result['issues']:
                lines.append(
                    "✅ No significant health concerns detected based on alert patterns.")
            else:
                lines.append(
                    f"⚠️  {len(result['issues'])} potential health issue(s) detected:\n")

                for i, issue in enumerate(result['issues'], 1):
                    lines.append(
                        f"{i}. {issue['condition']} [{issue['severity'].upper()}]")
                    lines.append(f"   Score: {issue['score']:.1%}")
                    lines.append(f"   Description: {issue['description']}")
                    lines.append(
                        f"   Recommendation: {issue['recommendation']}")
                    lines.append("")

        lines.append("=" * 60)
        lines.append("For more info, press [E] to export alerts as CSV")
        lines.append("=" * 60)

        return '\n'.join(lines)

    def _get_alerts_by_date(self, days: int) -> List[Dict]:
        """Retrieve alerts from database for specified days."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days)

        cursor.execute("""
            SELECT timestamp, risk_level, triggered_by, risk_score
            FROM alerts
            WHERE datetime(timestamp) >= ?
            ORDER BY timestamp
        """, (cutoff_date.isoformat(),))

        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return alerts

    def _detect_apnea(self, alerts: List[Dict]) -> float:
        """
        Detect sleep apnea pattern (rapid eye-closing clusters).
        Returns score 0.0-1.0 based on clustering intensity.
        """
        eye_close_alerts = [
            a for a in alerts if a['triggered_by'] == 'eyes_closed']

        if len(eye_close_alerts) < 3:
            return 0.0

        # Find 5-minute windows with clusters
        cluster_windows = 0
        total_windows = max(1, len(eye_close_alerts) - 2)

        for i in range(len(eye_close_alerts) - 2):
            ts1 = datetime.fromisoformat(eye_close_alerts[i]['timestamp'])
            ts2 = datetime.fromisoformat(eye_close_alerts[i + 1]['timestamp'])
            ts3 = datetime.fromisoformat(eye_close_alerts[i + 2]['timestamp'])

            # Check if 3 events within 5 minutes
            if (ts3 - ts1).total_seconds() < 300:
                cluster_windows += 1

        clustering_ratio = cluster_windows / total_windows if total_windows > 0 else 0.0

        # Score based on clustering intensity
        score = min(clustering_ratio, 1.0)
        return score

    def _detect_chronic_fatigue(self, alerts: List[Dict]) -> float:
        """
        Detect chronic fatigue (persistent drowsiness baseline).
        Returns score based on drowsy ratio and multi-day spread.
        """
        if not alerts:
            return 0.0

        drowsy_alerts = [a for a in alerts if a['triggered_by']
                         in ['drowsiness', 'eyes_closed']]
        total_alerts = len(alerts)

        drowsy_ratio = len(drowsy_alerts) / \
            total_alerts if total_alerts > 0 else 0.0

        # Check multi-day spread
        dates = set()
        for alert in drowsy_alerts:
            ts = datetime.fromisoformat(alert['timestamp'])
            dates.add(ts.date())

        day_spread = len(dates)
        spread_factor = min(day_spread / 7.0, 1.0)  # Normalized to 7 days

        # Combined score: drowsy ratio (60%) + spread across days (40%)
        score = (drowsy_ratio * 0.6) + (spread_factor * 0.4)
        return min(score, 1.0)

    def _detect_sudden_change(self, alerts: List[Dict]) -> float:
        """
        Detect sudden health change (alert frequency doubling).
        Compares first half vs second half of alert history.
        """
        if len(alerts) < 4:
            return 0.0

        midpoint = len(alerts) // 2
        first_half = alerts[:midpoint]
        second_half = alerts[midpoint:]

        first_half_rate = len(first_half) / \
            max(1, self._get_time_span_hours(first_half))
        second_half_rate = len(second_half) / \
            max(1, self._get_time_span_hours(second_half))

        # Frequency increase ratio
        increase_ratio = (second_half_rate /
                          first_half_rate) if first_half_rate > 0 else 1.0

        # Score: how much did it increase?
        # 2x increase = 0.5, 3x increase = 0.75, etc.
        change_score = min((increase_ratio - 1.0) / 2.0, 1.0)
        return max(change_score, 0.0)

    def _detect_time_pattern(self, alerts: List[Dict]) -> float:
        """
        Detect time-based patterns (drowsiness at specific hours).
        Returns score based on hour concentration.
        """
        hour_counts = defaultdict(int)

        for alert in alerts:
            ts = datetime.fromisoformat(alert['timestamp'])
            hour_counts[ts.hour] += 1

        if not hour_counts:
            return 0.0

        # Calculate concentration (entropy-based)
        total = sum(hour_counts.values())
        max_count = max(hour_counts.values())

        # If drowsiness concentrated in one hour, score increases
        concentration = max_count / total

        # Score high if >40% of alerts in single hour
        pattern_score = (concentration - 0.3) / \
            0.7 if concentration > 0.3 else 0.0
        return min(max(pattern_score, 0.0), 1.0)

    def _get_severity_level(self, score: float) -> str:
        """Convert score to severity level."""
        if score >= self.severity_thresholds['high']:
            return 'high'
        elif score >= self.severity_thresholds['medium']:
            return 'medium'
        else:
            return 'low'

    def _get_time_span_hours(self, alerts: List[Dict]) -> float:
        """Calculate time span of alerts in hours."""
        if len(alerts) < 2:
            return 1.0

        first_ts = datetime.fromisoformat(alerts[0]['timestamp'])
        last_ts = datetime.fromisoformat(alerts[-1]['timestamp'])

        span_seconds = (last_ts - first_ts).total_seconds()
        span_hours = max(span_seconds / 3600.0, 0.1)  # Minimum 0.1 hours
        return span_hours

    def _get_most_common_hour(self, alerts: List[Dict]) -> int:
        """Get the most common hour in alerts."""
        hour_counts = defaultdict(int)

        for alert in alerts:
            ts = datetime.fromisoformat(alert['timestamp'])
            hour_counts[ts.hour] += 1

        if not hour_counts:
            return 0

        return max(hour_counts, key=hour_counts.get)
