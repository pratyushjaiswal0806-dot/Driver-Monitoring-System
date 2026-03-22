"""Alert logbook system for persistent logging and audit trail."""

import sqlite3
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import csv


@dataclass
class AlertLog:
    """Data structure for a single alert log entry."""
    timestamp: str
    risk_level: str  # 'MILD', 'WARNING', 'HIGH', 'CRITICAL'
    risk_score: float  # 0-100
    # Component that triggered alert (e.g., 'eye_closurre', 'phone_detection')
    triggered_by: str
    duration_sec: float = 0.0  # How long risk level was active
    notes: str = ""


class LogbookManager:
    """Manages persistent alert logging using SQLite."""

    def __init__(self, db_path: str, auto_cleanup_days: int = 30):
        """
        Initialize logbook manager.

        Args:
            db_path: Path to SQLite database file
            auto_cleanup_days: Delete logs older than this many days
        """
        self.db_path = db_path
        self.auto_cleanup_days = auto_cleanup_days
        self.connection = None

        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            Path(db_dir).mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database and create schema if needed."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row

            cursor = self.connection.cursor()

            # Create alerts table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    triggered_by TEXT NOT NULL,
                    duration_sec REAL NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON alerts(timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_risk_level 
                ON alerts(risk_level)
            """)

            self.connection.commit()

        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            if self.connection:
                self.connection.close()
                self.connection = None

    def log_alert(self, alert: AlertLog) -> bool:
        """
        Log an alert to the database.

        Args:
            alert: AlertLog instance to log

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                INSERT INTO alerts 
                (timestamp, risk_level, risk_score, triggered_by, duration_sec, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert.timestamp,
                alert.risk_level,
                alert.risk_score,
                alert.triggered_by,
                alert.duration_sec,
                alert.notes
            ))

            self.connection.commit()
            return True

        except sqlite3.Error as e:
            print(f"Error logging alert: {e}")
            return False

    def get_today_statistics(self) -> Dict[str, any]:
        """
        Get alert statistics for today.

        Returns:
            Dict with counts by level, average risk, total alerts
        """
        if not self.connection:
            return self._empty_stats()

        try:
            cursor = self.connection.cursor()

            # Get today's date
            today = datetime.now().date().isoformat()

            cursor.execute("""
                SELECT risk_level, COUNT(*) as count, AVG(risk_score) as avg_risk
                FROM alerts
                WHERE DATE(timestamp) = ?
                GROUP BY risk_level
            """, (today,))

            rows = cursor.fetchall()

            stats = {
                'MILD': 0,
                'WARNING': 0,
                'HIGH': 0,
                'CRITICAL': 0,
                'total': 0,
                'average_risk': 0.0,
                'timestamp': datetime.now().isoformat()
            }

            total_risk = 0
            total_count = 0

            for row in rows:
                level = row['risk_level']
                count = row['count']
                avg_risk = row['avg_risk']

                stats[level] = count
                stats['total'] += count
                total_risk += avg_risk * count
                total_count += count

            if total_count > 0:
                stats['average_risk'] = total_risk / total_count

            return stats

        except sqlite3.Error as e:
            print(f"Error getting statistics: {e}")
            return self._empty_stats()

    def get_statistics_by_date_range(self, days: int = 7) -> Dict[str, any]:
        """
        Get alert statistics for a date range.

        Args:
            days: Number of past days to include

        Returns:
            Dict with statistics grouped by date
        """
        if not self.connection:
            return {}

        try:
            cursor = self.connection.cursor()

            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days - 1)

            cursor.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    risk_level,
                    COUNT(*) as count,
                    AVG(risk_score) as avg_risk,
                    MAX(risk_score) as max_risk
                FROM alerts
                WHERE DATE(timestamp) >= ? AND DATE(timestamp) <= ?
                GROUP BY DATE(timestamp), risk_level
                ORDER BY DATE(timestamp) DESC
            """, (start_date.isoformat(), end_date.isoformat()))

            rows = cursor.fetchall()

            # Organize by date
            stats_by_date = {}
            for row in rows:
                date = row['date']
                if date not in stats_by_date:
                    stats_by_date[date] = {
                        'MILD': 0,
                        'WARNING': 0,
                        'HIGH': 0,
                        'CRITICAL': 0,
                        'total': 0,
                        'average_risk': 0.0,
                        'max_risk': 0.0
                    }

                level = row['risk_level']
                stats_by_date[date][level] = row['count']
                stats_by_date[date]['total'] += row['count']
                stats_by_date[date]['average_risk'] += row['avg_risk']
                stats_by_date[date]['max_risk'] = max(
                    stats_by_date[date]['max_risk'],
                    row['max_risk']
                )

            return stats_by_date

        except sqlite3.Error as e:
            print(f"Error getting date range statistics: {e}")
            return {}

    def get_triggered_components(self, days: int = 7) -> Dict[str, int]:
        """
        Get frequency of each component triggering alerts.

        Args:
            days: Number of past days to include

        Returns:
            Dict mapping component names to trigger counts
        """
        if not self.connection:
            return {}

        try:
            cursor = self.connection.cursor()

            start_date = (datetime.now().date() -
                          timedelta(days=days - 1)).isoformat()

            cursor.execute("""
                SELECT triggered_by, COUNT(*) as count
                FROM alerts
                WHERE DATE(timestamp) >= ?
                GROUP BY triggered_by
                ORDER BY count DESC
            """, (start_date,))

            rows = cursor.fetchall()

            return {row['triggered_by']: row['count'] for row in rows}

        except sqlite3.Error as e:
            print(f"Error getting triggered components: {e}")
            return {}

    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """
        Get most recent alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of alert dictionaries
        """
        if not self.connection:
            return []

        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT 
                    timestamp,
                    risk_level,
                    risk_score,
                    triggered_by,
                    duration_sec,
                    notes
                FROM alerts
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            print(f"Error getting recent alerts: {e}")
            return []

    def export_to_csv(self, output_path: str,
                      days: Optional[int] = None) -> bool:
        """
        Export alerts to CSV file.

        Args:
            output_path: Path to save CSV file
            days: If specified, only export last N days; if None, export all

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()

            # Build query
            query = "SELECT * FROM alerts"
            params = []

            if days:
                start_date = (datetime.now().date() -
                              timedelta(days=days - 1)).isoformat()
                query += " WHERE DATE(timestamp) >= ?"
                params.append(start_date)

            query += " ORDER BY timestamp DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Write to CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if rows:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            'timestamp',
                            'risk_level',
                            'risk_score',
                            'triggered_by',
                            'duration_sec',
                            'notes'
                        ]
                    )
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(dict(row))

                    print(f"Exported {len(rows)} alerts to {output_path}")
                    return True
                else:
                    print("No alerts to export")
                    return False

        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False

    def clear_old_logs(self, days: Optional[int] = None) -> int:
        """
        Delete logs older than the specified days (default: auto_cleanup_days).

        Args:
            days: Days to keep (defaults to auto_cleanup_days)

        Returns:
            Number of records deleted
        """
        if not self.connection:
            return 0

        cleanup_days = days if days is not None else self.auto_cleanup_days

        try:
            cursor = self.connection.cursor()

            cutoff_date = (datetime.now().date() -
                           timedelta(days=cleanup_days)).isoformat()

            cursor.execute(
                "DELETE FROM alerts WHERE DATE(timestamp) < ?",
                (cutoff_date,)
            )

            self.connection.commit()
            deleted = cursor.rowcount

            if deleted > 0:
                print(f"Cleaned up {deleted} old alert logs")

            return deleted

        except sqlite3.Error as e:
            print(f"Error clearing old logs: {e}")
            return 0

    def get_alert_count(self) -> int:
        """Get total number of alerts in database."""
        if not self.connection:
            return 0

        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM alerts")
            result = cursor.fetchone()
            return result['count'] if result else 0

        except sqlite3.Error as e:
            print(f"Error getting alert count: {e}")
            return 0

    def print_console_stats(self, days: int = 7) -> None:
        """Print detailed statistics to console."""
        print("\n" + "=" * 60)
        print("  DRIVER MONITORING ALERT LOGBOOK")
        print("=" * 60)

        # Today's stats
        today_stats = self.get_today_statistics()
        print("\nTODAY'S ALERTS:")
        print(f"  Total: {today_stats['total']}")
        print(f"  ├─ MILD:     {today_stats['MILD']}")
        print(f"  ├─ WARNING:  {today_stats['WARNING']}")
        print(f"  ├─ HIGH:     {today_stats['HIGH']}")
        print(f"  └─ CRITICAL: {today_stats['CRITICAL']}")
        print(f"  Average Risk Score: {today_stats['average_risk']:.1f}%")

        # Date range stats
        print(f"\nLAST {days} DAYS BY LEVEL:")
        date_stats = self.get_statistics_by_date_range(days)

        for date in sorted(date_stats.keys(), reverse=True):
            stats = date_stats[date]
            print(f"  {date}: {stats['total']:3d} alerts " +
                  f"(M:{stats['MILD']:2d} W:{stats['WARNING']:2d} " +
                  f"H:{stats['HIGH']:2d} C:{stats['CRITICAL']:2d}) " +
                  f"avg:{stats['average_risk']:5.1f}% max:{stats['max_risk']:5.1f}%")

        # Top triggers
        print("\nTOP ALERT TRIGGERS (last {days} days):")
        triggers = self.get_triggered_components(days)
        if triggers:
            for i, (component, count) in enumerate(
                    sorted(triggers.items(),
                           key=lambda x: x[1], reverse=True)[:5],
                    1):
                print(f"  {i}. {component:30s} - {count:4d} times")
        else:
            print("  No alerts recorded")

        # Recent alerts
        print("\nRECENT ALERTS (last 5):")
        recent = self.get_recent_alerts(5)
        if recent:
            for alert in recent:
                print(f"  {alert['timestamp']} - {alert['risk_level']:8s} " +
                      f"({alert['risk_score']:5.1f}%) - {alert['triggered_by']}")
        else:
            print("  No recent alerts")

        total_count = self.get_alert_count()
        print(f"\nTOTAL ALERTS IN DATABASE: {total_count}")
        print("=" * 60 + "\n")

    def release(self) -> None:
        """Close database connection with proper cleanup."""
        if self.connection:
            try:
                # Bug fix: Commit any pending transactions before closing
                self.connection.commit()
            except Exception:
                pass

            try:
                self.connection.close()
            except Exception:
                pass

            self.connection = None

    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.release()

    @staticmethod
    def _empty_stats() -> Dict[str, any]:
        """Return empty statistics dictionary."""
        return {
            'MILD': 0,
            'WARNING': 0,
            'HIGH': 0,
            'CRITICAL': 0,
            'total': 0,
            'average_risk': 0.0,
            'timestamp': datetime.now().isoformat()
        }
