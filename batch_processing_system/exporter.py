from fpdf import FPDF
from datetime import datetime
import os

class PDF(FPDF):
    def header(self):
        # Logo placeholder or icon
        self.set_font('Arial', 'B', 15)
        self.set_text_color(40, 50, 150)
        self.cell(0, 10, 'BATCH PROCESSING SYSTEM - OFFICIAL REPORT', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.set_text_color(100)
        self.cell(0, 10, f'Generated on: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()} | System Verified Internal Document', 0, 0, 'C')

def generate_batch_report_pdf(report, log):
    pdf = PDF()
    pdf.add_page()
    
    # Report Section
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f"Summary for Date: {report['report_date']}", 1, 1, 'L', True)
    
    pdf.set_font('Arial', '', 10)
    pdf.ln(5)
    pdf.cell(50, 8, "Total Amount:", 0, 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, f"INR {report['total_amount']:,.2f}", 0, 1)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 8, "Transactions:", 0, 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, str(report['transaction_count']), 0, 1)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 8, "Processed At:", 0, 0)
    pdf.cell(0, 8, report['processed_at'], 0, 1)
    
    pdf.ln(10)
    
    # Execution Details Section
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "Execution Logs & Technical Details", 1, 1, 'L', True)
    
    pdf.set_font('Arial', '', 10)
    pdf.ln(5)
    pdf.cell(50, 8, "Job Name:", 0, 0)
    pdf.cell(0, 8, log.get('job_name', 'Manual Run'), 0, 1)
    
    pdf.cell(50, 8, "Duration:", 0, 0)
    pdf.cell(0, 8, log.get('duration', 'N/A'), 0, 1)
    
    pdf.cell(50, 8, "Status:", 0, 0)
    status = log.get('status', 'Unknown')
    if status == 'Success':
        pdf.set_text_color(0, 150, 0)
    else:
        pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 8, status, 0, 1)
    pdf.set_text_color(0)
    
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, "Raw Execution Logs:", 0, 1)
    pdf.set_font('Courier', '', 8)
    pdf.multi_cell(0, 5, log.get('logs', 'No logs available.'))
    
    output_path = f"report_{report['report_date']}.pdf"
    pdf.output(output_path)
    return output_path

def generate_history_export_pdf(logs):
    pdf = PDF()
    pdf.add_page()
    
    # Analytics Summary Section
    pdf.set_font('Arial', 'B', 14)
    pdf.set_fill_color(240, 245, 255)
    pdf.cell(0, 12, "SYSTEM PERFORMANCE ANALYTICS SUMMARY", 0, 1, 'L', True)
    pdf.ln(5)
    
    # Calculate stats
    total_logs = len(logs)
    success_logs = len([l for l in logs if l['status'] == 'Success'])
    failed_logs = len([l for l in logs if l['status'] == 'Failed'])
    success_rate = (success_logs / total_logs * 100) if total_logs > 0 else 0
    
    # Draw a simple visual "Success Box"
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 10, f"TOTAL JOBS: {total_logs}", 1, 0, 'C')
    pdf.set_text_color(0, 120, 0)
    pdf.cell(60, 10, f"SUCCESS: {success_logs}", 1, 0, 'C')
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 10, f"FAILED: {failed_logs}", 1, 1, 'C')
    pdf.set_text_color(0)
    
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_fill_color(230, 255, 230)
    pdf.cell(0, 15, f"OVERALL SUCCESS RATE: {success_rate:.1f}%", 1, 1, 'C', True)
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "DETAILED EXECUTION HISTORY", 0, 1, 'L')
    pdf.ln(2)
    
    # Table Header
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(60, 80, 160)
    pdf.set_text_color(255)
    pdf.cell(15, 8, "ID", 1, 0, 'C', True)
    pdf.cell(60, 8, "Job Name", 1, 0, 'C', True)
    pdf.cell(40, 8, "Start Time", 1, 0, 'C', True)
    pdf.cell(30, 8, "Duration", 1, 0, 'C', True)
    pdf.cell(45, 8, "Status", 1, 1, 'C', True)
    pdf.set_text_color(0)
    
    # Table Body
    pdf.set_font('Arial', '', 8)
    for l in logs:
        pdf.cell(15, 7, str(l['id']), 1, 0, 'C')
        pdf.cell(60, 7, str(l['job_name'])[:35], 1, 0, 'L')
        pdf.cell(40, 7, str(l['start_time'])[:19], 1, 0, 'C')
        pdf.cell(30, 7, str(l['duration']), 1, 0, 'C')
        
        status = str(l['status'])
        if status == 'Success':
            pdf.set_text_color(0, 150, 0)
        elif status == 'Failed':
            pdf.set_text_color(200, 0, 0)
        pdf.cell(45, 7, status, 1, 1, 'C')
        pdf.set_text_color(0)
        
    output_path = "execution_history.pdf"
    pdf.output(output_path)
    return output_path
