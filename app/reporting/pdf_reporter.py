"""
PDF Reporter
Generates PDF certificate reports (using HTML to PDF conversion)
"""

import logging
from pathlib import Path
from datetime import datetime
from app.models.schemas import TestSession, Report
from config.settings import settings

logger = logging.getLogger(__name__)


class PDFReporter:
    """Generates PDF certificate reports"""
    
    def __init__(self, output_dir: str = "reports/pdf"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate(self, session: TestSession) -> Report:
        """Generate PDF certificate"""
        logger.info(f"Generating PDF report for session {session.session_id}")
        
        try:
            # Try to use weasyprint for PDF generation
            from weasyprint import HTML, CSS
            
            html_content = self._build_certificate_html(session)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"void_certificate_{session.ipc_id}_{timestamp}.pdf"
            filepath = self.output_dir / filename
            
            # Generate PDF
            HTML(string=html_content).write_pdf(
                filepath,
                stylesheets=[CSS(string=self._get_pdf_styles())]
            )
            
            # Create report metadata - use relative path from reports directory
            relative_path = filepath.relative_to(Path("reports"))
            report = Report(
                report_id=f"pdf_{session.session_id}",
                session_id=session.session_id,
                format="pdf",
                file_path=str(relative_path),
                size_bytes=filepath.stat().st_size
            )
            
            logger.info(f"PDF report generated: {filepath}")
            return report
            
        except ImportError:
            logger.warning("WeasyPrint not installed. Generating text-based PDF alternative")
            return self._generate_text_pdf(session)
    
    def _build_certificate_html(self, session: TestSession) -> str:
        """Build HTML for PDF certificate"""
        
        decision_text = session.decision.decision.value if session.decision else "PENDING"
        score = session.decision.score if session.decision else 0
        decision_color = "#43A047" if decision_text == "GO" else "#E53935"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VOID Test Certificate</title>
</head>
<body>
    <div class="certificate">
        <div class="header">
            <h1>VOID Framework</h1>
            <p>Validation Of Industrial Devices</p>
        </div>
        
        <div class="title">
            <h2>IPC TEST CERTIFICATE</h2>
        </div>
        
        <div class="content">
            <div class="info-row">
                <span class="label">IPC Model:</span>
                <span class="value">{session.hardware_profile.ipc_model if session.hardware_profile else 'Unknown'}</span>
            </div>
            
            <div class="info-row">
                <span class="label">IPC ID:</span>
                <span class="value">{session.ipc_id}</span>
            </div>
            
            <div class="info-row">
                <span class="label">Session ID:</span>
                <span class="value">{session.session_id}</span>
            </div>
            
            <div class="info-row">
                <span class="label">Test Date:</span>
                <span class="value">{session.start_time.strftime('%Y-%m-%d %H:%M')}</span>
            </div>
            
            <div class="info-row">
                <span class="label">Total Tests:</span>
                <span class="value">{len(session.test_results)}</span>
            </div>
            
            <div class="info-row">
                <span class="label">Duration:</span>
                <span class="value">{round(session.total_duration, 2) if session.total_duration else 0} hours</span>
            </div>
            
            <div class="score-box" style="background: {decision_color};">
                <div class="score-label">Final Score</div>
                <div class="score-value">{round(score, 1)}/100</div>
            </div>
            
            <div class="decision-box" style="border-color: {decision_color}; color: {decision_color};">
                <h3>{decision_text}</h3>
            </div>
        </div>
        
        <div class="footer">
            <p>This certificate confirms that the IPC has undergone comprehensive automated testing.</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>VOID Framework {settings.app_version}</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _get_pdf_styles(self) -> str:
        """Get CSS styles for PDF"""
        return """
        @page { size: A4; margin: 2cm; }
        body { font-family: 'Helvetica', Arial, sans-serif; }
        .certificate { padding: 40px; }
        .header { text-align: center; border-bottom: 3px solid #1976D2; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { font-size: 32px; color: #1976D2; margin: 0; }
        .header p { font-size: 14px; color: #757575; margin: 5px 0 0 0; }
        .title { text-align: center; margin: 30px 0; }
        .title h2 { font-size: 24px; color: #212121; font-weight: 300; }
        .content { margin: 30px 0; }
        .info-row { padding: 12px 0; border-bottom: 1px solid #E0E0E0; display: flex; justify-content: space-between; }
        .label { font-weight: 500; color: #616161; }
        .value { color: #212121; }
        .score-box { background: #43A047; color: white; padding: 30px; text-align: center; margin: 30px 0; border-radius: 8px; }
        .score-label { font-size: 14px; margin-bottom: 10px; }
        .score-value { font-size: 48px; font-weight: bold; }
        .decision-box { border: 4px solid #43A047; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }
        .decision-box h3 { font-size: 36px; margin: 0; }
        .footer { text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid #E0E0E0; font-size: 11px; color: #757575; }
        """
    
    def _generate_text_pdf(self, session: TestSession) -> Report:
        """Generate text-based PDF alternative (if WeasyPrint not available)"""
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"void_certificate_{session.ipc_id}_{timestamp}.pdf"
        filepath = self.output_dir / filename
        
        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor("#1976D2"), alignment=1)
        story.append(Paragraph("VOID Framework", title_style))
        story.append(Paragraph("IPC Test Certificate", styles['Heading2']))
        story.append(Spacer(1, 1*cm))
        
        # Certificate data
        data = [
            ["IPC Model:", session.hardware_profile.ipc_model if session.hardware_profile else "Unknown"],
            ["IPC ID:", session.ipc_id],
            ["Session ID:", session.session_id],
            ["Test Date:", session.start_time.strftime('%Y-%m-%d %H:%M')],
            ["Total Tests:", str(len(session.test_results))],
            ["Score:", f"{round(session.decision.score, 1) if session.decision else 0}/100"],
            ["Decision:", session.decision.decision.value if session.decision else "PENDING"]
        ]
        
        table = Table(data, colWidths=[6*cm, 10*cm])
        table.setStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#616161")),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ])
        
        story.append(table)
        story.append(Spacer(1, 1*cm))
        
        # Hardware Details
        if session.hardware_profile:
            hw_title_style = ParagraphStyle('HardwareTitle', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor("#1976D2"), spaceAfter=12)
            story.append(Paragraph("Hardware Details", hw_title_style))
            
            hw_data = []
            
            # CPU
            if session.hardware_profile.cpu:
                hw_data.append(["CPU", session.hardware_profile.cpu.name])
                if session.hardware_profile.cpu.details:
                    for key, value in list(session.hardware_profile.cpu.details.items())[:5]:  # Limit to 5 details
                        hw_data.append([f"  {key.replace('_', ' ').title()}", str(value)])
            
            # GPU
            if session.hardware_profile.gpu:
                for gpu in session.hardware_profile.gpu:
                    hw_data.append(["GPU", gpu.name])
                    if gpu.details:
                        for key, value in list(gpu.details.items())[:5]:  # Limit to 5 details
                            hw_data.append([f"  {key.replace('_', ' ').title()}", str(value)])
            
            # RAM
            if session.hardware_profile.ram:
                for ram in session.hardware_profile.ram:
                    hw_data.append(["RAM", ram.name])
            
            if hw_data:
                hw_table = Table(hw_data, colWidths=[6*cm, 10*cm])
                hw_table.setStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#616161")),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ])
                story.append(hw_table)
        
        story.append(Spacer(1, 1*cm))
        
        # Footer
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=10, textColor=colors.grey, alignment=1)
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))
        story.append(Paragraph(f"VOID Framework {settings.app_version}", footer_style))
        
        doc.build(story)
        
        # Create report metadata - use relative path from reports directory
        relative_path = filepath.relative_to(Path("reports"))
        report = Report(
            report_id=f"pdf_{session.session_id}",
            session_id=session.session_id,
            format="pdf",
            file_path=str(relative_path),
            size_bytes=filepath.stat().st_size
        )
        
        logger.info(f"Text-based PDF report generated: {filepath}")
        return report

