"""
HTML Reporter
Generates interactive HTML dashboard reports
"""

import logging
from pathlib import Path
from datetime import datetime
from jinja2 import Template
from app.models.schemas import TestSession, Report

logger = logging.getLogger(__name__)


class HTMLReporter:
    """Generates HTML dashboard reports"""
    
    def __init__(self, output_dir: str = "reports/html"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate(self, session: TestSession) -> Report:
        """Generate HTML report"""
        logger.info(f"Generating HTML report for session {session.session_id}")
        
        # Generate HTML content
        html_content = self._build_html(session)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"void_dashboard_{session.ipc_id}_{timestamp}.html"
        filepath = self.output_dir / filename
        
        # Write HTML file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Create report metadata - use relative path from reports directory
        relative_path = filepath.relative_to(Path("reports"))
        report = Report(
            report_id=f"html_{session.session_id}",
            session_id=session.session_id,
            format="html",
            file_path=str(relative_path),
            size_bytes=filepath.stat().st_size
        )
        
        logger.info(f"HTML report generated: {filepath}")
        return report
    
    def _build_html(self, session: TestSession) -> str:
        """Build HTML dashboard"""
        
        # Calculate statistics
        total_tests = len(session.test_results)
        passed = sum(1 for r in session.test_results if r.status.value == "passed")
        failed = sum(1 for r in session.test_results if r.status.value == "failed")
        errors = sum(1 for r in session.test_results if r.status.value == "error")
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        # Decision info
        decision_color = "#43A047" if session.decision and session.decision.decision.value == "GO" else "#E53935"
        decision_text = session.decision.decision.value if session.decision else "PENDING"
        score = session.decision.score if session.decision else 0
        
        html_template = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VOID Test Report - {{ ipc_id }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Roboto', sans-serif; background: #FAFAFA; color: #212121; line-height: 1.6; }
        .header { background: #FFFFFF; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 24px 0; }
        .header-content { max-width: 1200px; margin: 0 auto; padding: 0 24px; }
        .header h1 { font-size: 24px; font-weight: 400; color: #212121; }
        .header .subtitle { font-size: 14px; color: #757575; margin-top: 4px; }
        .container { max-width: 1200px; margin: 0 auto; padding: 48px 24px; }
        .section { background: #FFFFFF; border-radius: 8px; padding: 32px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        .section-title { font-size: 24px; font-weight: 300; margin-bottom: 16px; color: #212121; }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 24px 0; }
        .card { background: #F5F5F5; border-radius: 4px; padding: 20px; text-align: center; }
        .card-value { font-size: 32px; font-weight: 500; color: #1976D2; margin: 8px 0; }
        .card-label { font-size: 13px; color: #757575; }
        .decision-box { background: {{ decision_color }}; color: white; padding: 32px; border-radius: 8px; text-align: center; margin: 24px 0; }
        .decision-box h2 { font-size: 48px; font-weight: 300; margin-bottom: 8px; }
        .decision-box p { font-size: 16px; opacity: 0.9; }
        .progress-bar { background: #E0E0E0; border-radius: 8px; height: 24px; margin: 8px 0; overflow: hidden; }
        .progress-fill { background: #43A047; height: 100%; transition: width 0.3s; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 500; }
        .progress-fill.warning { background: #FB8C00; }
        .progress-fill.danger { background: #E53935; }
        .test-result { padding: 12px; border-left: 4px solid #E0E0E0; margin: 8px 0; background: #FAFAFA; }
        .test-result.passed { border-left-color: #43A047; }
        .test-result.failed { border-left-color: #E53935; }
        .test-result.error { border-left-color: #FF9800; }
        .test-result-name { font-weight: 500; color: #212121; }
        .test-result-status { font-size: 12px; color: #757575; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; }
        th { background: #F5F5F5; padding: 12px; text-align: left; font-weight: 500; font-size: 13px; color: #616161; }
        td { padding: 12px; font-size: 14px; color: #757575; border-bottom: 1px solid #F5F5F5; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 500; }
        .badge.success { background: #E8F5E9; color: #2E7D32; }
        .badge.danger { background: #FFEBEE; color: #C62828; }
        .badge.warning { background: #FFF3E0; color: #E65100; }
        .badge.info { background: #E3F2FD; color: #1565C0; }
        .footer { background: #212121; color: #BDBDBD; padding: 24px; text-align: center; margin-top: 48px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>VOID Framework - Test Report</h1>
            <div class="subtitle">Validation Of Industrial Devices</div>
        </div>
    </div>

    <div class="container">
        <!-- Decision Section -->
        <div class="decision-box" style="background: {{ decision_color }};">
            <h2>{{ decision_text }}</h2>
            <p>Final Score: {{ score }}/100 | Session: {{ session_id }}</p>
        </div>

        <!-- Summary Cards -->
        <div class="card-grid">
            <div class="card">
                <div class="card-label">IPC Model</div>
                <div class="card-value" style="font-size: 16px;">{{ ipc_model }}</div>
            </div>
            <div class="card">
                <div class="card-label">Total Tests</div>
                <div class="card-value">{{ total_tests }}</div>
            </div>
            <div class="card">
                <div class="card-label">Passed</div>
                <div class="card-value" style="color: #43A047;">{{ passed }}</div>
            </div>
            <div class="card">
                <div class="card-label">Failed</div>
                <div class="card-value" style="color: #E53935;">{{ failed }}</div>
            </div>
            <div class="card">
                <div class="card-label">Pass Rate</div>
                <div class="card-value">{{ pass_rate }}%</div>
            </div>
        </div>

        <!-- Test Results -->
        <div class="section">
            <h2 class="section-title">Test Results</h2>
            {% for result in test_results %}
            <div class="test-result {{ result.status }}">
                <div class="test-result-name">{{ result.test_name }}</div>
                <div class="test-result-status">
                    Status: <span class="badge {{ result.badge_class }}">{{ result.status|upper }}</span> |
                    Duration: {{ result.duration }}s
                    {% if result.metrics %}
                    {% if result.metrics.cpu_avg %} | CPU: {{ result.metrics.cpu_avg|round(1) }}%{% endif %}
                    {% if result.metrics.memory_avg %} | RAM: {{ result.metrics.memory_avg|round(1) }}%{% endif %}
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- AI Analysis -->
        {% if ai_analysis %}
        <div class="section">
            <h2 class="section-title">AI/ML Analysis</h2>
            <p><strong>Risk Level:</strong> <span class="badge {{ risk_badge }}">{{ ai_analysis.risk_level }}</span></p>
            <p><strong>Anomaly Score:</strong> {{ ai_analysis.overall_anomaly_score|round(1) }}/100</p>
            
            <h3 style="margin-top: 24px; font-size: 18px;">Recommendations</h3>
            <ul style="margin-left: 24px; margin-top: 12px;">
                {% for rec in ai_analysis.recommendations %}
                <li>{{ rec }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        <!-- Hardware Profile -->
        {% if hardware_profile %}
        <div class="section">
            <h2 class="section-title">Hardware Profile</h2>
            <table>
                <tr>
                    <th>Component</th>
                    <th>Details</th>
                </tr>
                {% if hardware_profile.cpu %}
                <tr>
                    <td><strong>CPU</strong></td>
                    <td>{{ hardware_profile.cpu.name }}</td>
                </tr>
                {% endif %}
                {% for ram in hardware_profile.ram %}
                <tr>
                    <td><strong>RAM</strong></td>
                    <td>{{ ram.name }}</td>
                </tr>
                {% endfor %}
                {% for gpu in hardware_profile.gpu %}
                <tr>
                    <td><strong>GPU</strong></td>
                    <td>{{ gpu.name }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}

        <!-- Session Info -->
        <div class="section">
            <h2 class="section-title">Session Information</h2>
            <p><strong>Session ID:</strong> {{ session_id }}</p>
            <p><strong>IPC ID:</strong> {{ ipc_id }}</p>
            <p><strong>Start Time:</strong> {{ start_time }}</p>
            <p><strong>End Time:</strong> {{ end_time }}</p>
            <p><strong>Duration:</strong> {{ duration_hours }} hours</p>
            <p><strong>Report Generated:</strong> {{ generated_at }}</p>
        </div>
    </div>

    <div class="footer">
        <p><strong>VOID Framework v1.0.0</strong></p>
        <p>Validation Of Industrial Devices</p>
    </div>
</body>
</html>
"""
        
        # Prepare data for template
        test_results_data = []
        for r in session.test_results:
            badge_class = "success" if r.status.value == "passed" else "danger" if r.status.value == "failed" else "warning"
            test_results_data.append({
                "test_name": r.test_name,
                "status": r.status.value,
                "badge_class": badge_class,
                "duration": round(r.duration, 1) if r.duration else 0,
                "metrics": r.metrics
            })
        
        risk_badge = "danger" if session.ai_analysis and session.ai_analysis.risk_level == "CRITICAL" else \
                     "warning" if session.ai_analysis and session.ai_analysis.risk_level in ["HIGH", "MEDIUM"] else "success"
        
        template = Template(html_template)
        html_content = template.render(
            ipc_id=session.ipc_id,
            ipc_model=session.hardware_profile.ipc_model if session.hardware_profile else "Unknown",
            session_id=session.session_id,
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            errors=errors,
            pass_rate=round(pass_rate, 1),
            decision_color=decision_color,
            decision_text=decision_text,
            score=round(score, 1),
            test_results=test_results_data,
            ai_analysis=session.ai_analysis,
            risk_badge=risk_badge,
            hardware_profile=session.hardware_profile,
            start_time=session.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=session.end_time.strftime("%Y-%m-%d %H:%M:%S") if session.end_time else "In Progress",
            duration_hours=round(session.total_duration, 2) if session.total_duration else 0,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return html_content

