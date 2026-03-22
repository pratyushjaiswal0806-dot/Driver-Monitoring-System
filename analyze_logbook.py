"""
Logbook Data Analysis and Visualization
Generates comprehensive statistics and graphs from alerts.db
"""

from config import LOGBOOK_DB_PATH
import sqlite3
import sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import os

sys.path.insert(0, 'c:/Users/praty/driver_monitor')

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib not installed. Install with: pip install matplotlib")


class LogbookAnalyzer:
    """Analyzes alert history from SQLite database."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.alerts = []
        self.load_data()

    def load_data(self):
        """Load all alerts from database."""
        if not os.path.exists(self.db_path):
            print(f"❌ Database not found: {self.db_path}")
            return

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT timestamp, risk_level, triggered_by, risk_score, duration_sec
            FROM alerts
            ORDER BY timestamp
        """)

        for row in cursor.fetchall():
            self.alerts.append({
                'timestamp': datetime.fromisoformat(row['timestamp']),
                'risk_level': row['risk_level'],
                'triggered_by': row['triggered_by'],
                'risk_score': float(row['risk_score']),
                'duration_sec': float(row['duration_sec'])
            })

        conn.close()

    def generate_summary(self) -> str:
        """Generate text summary statistics."""
        if not self.alerts:
            return "No alert data available"

        lines = []
        lines.append("=" * 70)
        lines.append("LOGBOOK DATA ANALYSIS SUMMARY")
        lines.append("=" * 70)
        lines.append("")

        # Basic stats
        lines.append("📊 OVERVIEW")
        lines.append(f"  Total Alerts: {len(self.alerts)}")
        lines.append(
            f"  Date Range: {self.alerts[0]['timestamp'].date()} to {self.alerts[-1]['timestamp'].date()}")
        days_span = (self.alerts[-1]['timestamp'] -
                     self.alerts[0]['timestamp']).days
        lines.append(f"  Duration: {days_span} days")
        lines.append(
            f"  Average Alerts/Day: {len(self.alerts) / max(days_span, 1):.1f}")
        lines.append(
            f"  Average Risk Score: {np.mean([a['risk_score'] for a in self.alerts]):.1f}/100")
        lines.append("")

        # Risk level breakdown
        lines.append("⚠️  RISK LEVEL BREAKDOWN")
        risk_counts = Counter(a['risk_level'] for a in self.alerts)
        risk_order = ['SAFE', 'MILD', 'WARNING', 'HIGH', 'CRITICAL']
        for level in risk_order:
            count = risk_counts.get(level, 0)
            if count > 0:
                pct = (count / len(self.alerts)) * 100
                lines.append(f"  {level:12}: {count:4d} ({pct:5.1f}%)")
        lines.append("")

        # Trigger breakdown
        lines.append("🎯 ALERT TRIGGERS (Top 5)")
        trigger_counts = Counter(a['triggered_by'] for a in self.alerts)
        for trigger, count in trigger_counts.most_common(5):
            pct = (count / len(self.alerts)) * 100
            lines.append(f"  {trigger:20}: {count:4d} ({pct:5.1f}%)")
        lines.append("")

        # Time analysis
        lines.append("⏰ TIME PATTERNS")
        hours = [a['timestamp'].hour for a in self.alerts]
        hour_counts = Counter(hours)
        peak_hour = hour_counts.most_common(1)[0]
        lines.append(
            f"  Peak Hour: {peak_hour[0]:02d}:00 - {peak_hour[1]} alerts")

        quiet_hours = [h for h in range(24) if hour_counts.get(h, 0) == 0]
        if quiet_hours:
            lines.append(
                f"  Quietest Hours: {', '.join([f'{h:02d}:00' for h in quiet_hours[:3]])}")

        # Day of week analysis
        lines.append("")
        lines.append("📅 DAY OF WEEK BREAKDOWN")
        day_names = ['Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_counts = Counter(a['timestamp'].weekday() for a in self.alerts)
        for day_idx in range(7):
            count = day_counts.get(day_idx, 0)
            pct = (count / len(self.alerts)) * 100
            lines.append(
                f"  {day_names[day_idx]:10}: {count:4d} ({pct:5.1f}%)")
        lines.append("")

        # High-risk sessions
        lines.append("🔴 CRITICAL ALERTS (Risk >= 80)")
        critical = [a for a in self.alerts if a['risk_score'] >= 80]
        if critical:
            lines.append(f"  Count: {len(critical)}")
            lines.append(
                f"  Percentage: {(len(critical)/len(self.alerts))*100:.1f}%")
            lines.append(
                f"  Average Score: {np.mean([a['risk_score'] for a in critical]):.1f}")
        else:
            lines.append("  Count: 0")
        lines.append("")

        # Duration stats
        durations = [a['duration_sec']
                     for a in self.alerts if a['duration_sec'] > 0]
        if durations:
            lines.append("⏱️  ALERT DURATION")
            lines.append(
                f"  Average Duration: {np.mean(durations):.1f} seconds")
            lines.append(f"  Longest Alert: {max(durations):.1f} seconds")
            lines.append(
                f"  Total Alert Time: {sum(durations)/60:.1f} minutes")
        lines.append("")

        lines.append("=" * 70)

        return '\n'.join(lines)

    def plot_risk_timeline(self):
        """Plot risk scores over time."""
        if not MATPLOTLIB_AVAILABLE:
            return

        timestamps = [a['timestamp'] for a in self.alerts]
        scores = [a['risk_score'] for a in self.alerts]

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(timestamps, scores, alpha=0.6, linewidth=1, color='blue')
        ax.axhline(y=20, color='green', linestyle='--',
                   alpha=0.3, label='Safe')
        ax.axhline(y=40, color='orange', linestyle='--',
                   alpha=0.3, label='Mild')
        ax.axhline(y=60, color='red', linestyle='--',
                   alpha=0.3, label='Warning')
        ax.axhline(y=80, color='darkred', linestyle='--',
                   alpha=0.3, label='Critical')

        ax.set_xlabel('Time')
        ax.set_ylabel('Risk Score')
        ax.set_title('Driver Risk Score Timeline')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('risk_timeline.png', dpi=150, bbox_inches='tight')
        print("✅ Saved: risk_timeline.png")
        plt.close()

    def plot_risk_distribution(self):
        """Plot histogram of risk scores."""
        if not MATPLOTLIB_AVAILABLE:
            return

        scores = [a['risk_score'] for a in self.alerts]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(scores, bins=20, color='steelblue',
                edgecolor='black', alpha=0.7)
        ax.axvline(x=20, color='green', linestyle='--',
                   linewidth=2, label='Safe threshold')
        ax.axvline(x=40, color='orange', linestyle='--',
                   linewidth=2, label='Mild threshold')
        ax.axvline(x=60, color='red', linestyle='--',
                   linewidth=2, label='Warning threshold')
        ax.axvline(x=80, color='darkred', linestyle='--',
                   linewidth=2, label='Critical threshold')

        ax.set_xlabel('Risk Score')
        ax.set_ylabel('Frequency')
        ax.set_title('Distribution of Risk Scores')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig('risk_distribution.png', dpi=150, bbox_inches='tight')
        print("✅ Saved: risk_distribution.png")
        plt.close()

    def plot_hourly_pattern(self):
        """Plot alerts by hour of day."""
        if not MATPLOTLIB_AVAILABLE:
            return

        hour_counts = Counter(a['timestamp'].hour for a in self.alerts)
        hours = list(range(24))
        counts = [hour_counts.get(h, 0) for h in hours]

        fig, ax = plt.subplots(figsize=(12, 5))
        colors = ['red' if c > np.mean(
            counts) else 'steelblue' for c in counts]
        ax.bar(hours, counts, color=colors, edgecolor='black', alpha=0.7)

        ax.set_xlabel('Hour of Day')
        ax.set_ylabel('Alert Count')
        ax.set_title('Alerts by Hour (Red = Above Average)')
        ax.set_xticks(range(0, 24, 2))
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig('hourly_pattern.png', dpi=150, bbox_inches='tight')
        print("✅ Saved: hourly_pattern.png")
        plt.close()

    def plot_triggers(self):
        """Plot alert triggers as pie chart."""
        if not MATPLOTLIB_AVAILABLE:
            return

        trigger_counts = Counter(a['triggered_by'] for a in self.alerts)
        labels = list(trigger_counts.keys())
        sizes = list(trigger_counts.values())

        fig, ax = plt.subplots(figsize=(10, 8))
        colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                          colors=colors, startangle=90)

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        ax.set_title('Alert Triggers Distribution')
        plt.tight_layout()
        plt.savefig('triggers_pie.png', dpi=150, bbox_inches='tight')
        print("✅ Saved: triggers_pie.png")
        plt.close()

    def plot_daily_alerts(self):
        """Plot alerts per day."""
        if not MATPLOTLIB_AVAILABLE:
            return

        # Group by date
        daily_counts = defaultdict(int)
        for alert in self.alerts:
            date = alert['timestamp'].date()
            daily_counts[date] += 1

        dates = sorted(daily_counts.keys())
        counts = [daily_counts[d] for d in dates]

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.bar(dates, counts, color='steelblue', edgecolor='black', alpha=0.7)

        ax.set_xlabel('Date')
        ax.set_ylabel('Alert Count')
        ax.set_title('Daily Alert Count')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig('daily_alerts.png', dpi=150, bbox_inches='tight')
        print("✅ Saved: daily_alerts.png")
        plt.close()

    def plot_risk_levels(self):
        """Plot breakdown of risk levels."""
        if not MATPLOTLIB_AVAILABLE:
            return

        risk_counts = Counter(a['risk_level'] for a in self.alerts)
        risk_order = ['SAFE', 'MILD', 'WARNING', 'HIGH', 'CRITICAL']
        labels = [r for r in risk_order if r in risk_counts]
        sizes = [risk_counts[r] for r in labels]

        # Color mapping
        color_map = {
            'SAFE': 'green',
            'MILD': 'yellow',
            'WARNING': 'orange',
            'HIGH': 'red',
            'CRITICAL': 'darkred'
        }
        colors = [color_map[r] for r in labels]

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(labels, sizes, color=colors,
                      edgecolor='black', alpha=0.7)

        # Add count labels on bars
        for bar, size in zip(bars, sizes):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(size)}',
                    ha='center', va='bottom', fontweight='bold')

        ax.set_ylabel('Count')
        ax.set_title('Alert Distribution by Risk Level')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig('risk_levels.png', dpi=150, bbox_inches='tight')
        print("✅ Saved: risk_levels.png")
        plt.close()


def main():
    """Main analysis function."""
    print("\n" + "=" * 70)
    print("LOGBOOK DATA ANALYSIS")
    print("=" * 70 + "\n")

    if not os.path.exists(LOGBOOK_DB_PATH):
        print(f"❌ Database not found: {LOGBOOK_DB_PATH}")
        print("Run the monitoring system first to generate alert data.")
        return

    analyzer = LogbookAnalyzer(LOGBOOK_DB_PATH)

    if not analyzer.alerts:
        print("❌ No alert data found in database")
        return

    # Print summary
    summary = analyzer.generate_summary()
    print(summary)

    # Generate visualizations
    if MATPLOTLIB_AVAILABLE:
        print("\n📈 Generating visualizations...\n")

        print("1. Risk Score Timeline:")
        analyzer.plot_risk_timeline()

        print("\n2. Risk Score Distribution:")
        analyzer.plot_risk_distribution()

        print("\n3. Hourly Pattern:")
        analyzer.plot_hourly_pattern()

        print("\n4. Alert Triggers:")
        analyzer.plot_triggers()

        print("\n5. Daily Alerts:")
        analyzer.plot_daily_alerts()

        print("\n6. Risk Levels:")
        analyzer.plot_risk_levels()

        print("\n✅ All visualizations saved to current directory!")
        print(
            "   Check: risk_timeline.png, risk_distribution.png, hourly_pattern.png, etc.")
    else:
        print("\n⚠️  matplotlib not installed. Install with:")
        print("   pip install matplotlib numpy")
        print("\n   Text summary generated above.")


if __name__ == '__main__':
    main()
