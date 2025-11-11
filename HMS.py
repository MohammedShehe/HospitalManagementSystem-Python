"""
Vital Sign Informatics Console - Professional Healthcare System
Enhanced version with modern UI, improved data visualization, and professional styling
Including Pharmacist role and enhanced functionality with PDF export
With patient history tracking and editing capabilities
With QR code generation for patient visit history - MODIFIED FOR READABLE FORMAT
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import json
import os
import sys

# Matplotlib for embedded charts
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# PDF Export functionality
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import tempfile

# QR Code generation - NEW ADDITION
import qrcode
from PIL import Image, ImageTk
import io

# Professional color scheme
COLORS = {
    'primary': '#2C3E50',      # Dark blue - professional medical
    'secondary': '#3498DB',    # Bright blue
    'accent': '#E74C3C',       # Red for alerts
    'success': '#27AE60',      # Green
    'warning': '#F39C12',      # Orange
    'light': '#ECF0F1',        # Light gray
    'dark': '#2C3E50',         # Dark text
    'background': '#F8F9FA',   # Off-white background
    'card_bg': '#FFFFFF',      # White cards
    'border': '#BDC3C7'        # Border color
}

DB_FILE = "vital_signs.db"

# ---------------------
# QR Code Generator - MODIFIED VERSION
# ---------------------
class QRCodeGenerator:
    def __init__(self, db):
        self.db = db

    def generate_patient_qr_data(self, patient_id):
        """Generate QR code data for a patient with last 4 visits in a readable format"""
        patient = self.db.get_patient(patient_id)
        if not patient:
            return None

        # Get last 4 visits
        visits = self.db.get_visits_for_patient(patient_id)
        last_4_visits = visits[:4] if len(visits) > 4 else visits

        # Create readable text format instead of JSON
        qr_text = f"BOOLEAN BROS HOSPITAL\n"
        qr_text += f"PATIENT INFORMATION\n"
        qr_text += f"{'='*40}\n"
        qr_text += f"Patient ID: {patient_id}\n"
        qr_text += f"Name: {patient['full_name']}\n"
        qr_text += f"Date of Birth: {patient['dob'] or 'Not provided'}\n"
        qr_text += f"Address: {patient['address'] or 'Not provided'}\n"
        qr_text += f"Registered: {patient['created_at'][:10]}\n"
        qr_text += f"\n"
        qr_text += f"RECENT VISIT HISTORY (Last {len(last_4_visits)} visits)\n"
        qr_text += f"{'='*40}\n"

        for i, visit in enumerate(last_4_visits, 1):
            qr_text += f"\nVisit {i} - {visit['date']}\n"
            qr_text += f"  Service: {visit['service'] or 'Not specified'}\n"
            qr_text += f"  Doctor: {visit['doctor_name'] or 'Unassigned'}\n"
            qr_text += f"  Status: {visit['status'] or 'Unknown'}\n"
            qr_text += f"  Time: {visit['time_in'] or 'N/A'} - {visit['time_out'] or 'N/A'}\n"

            # Add vital signs if available
            vitals = visit.get('vitals', {})
            if vitals:
                qr_text += f"  Vital Signs:\n"
                if vitals.get('bp'):
                    qr_text += f"    BP: {vitals['bp']}\n"
                if vitals.get('hr'):
                    qr_text += f"    Heart Rate: {vitals['hr']} bpm\n"
                if vitals.get('temp'):
                    qr_text += f"    Temp: {vitals['temp']}°F\n"
                if vitals.get('resp'):
                    qr_text += f"    Resp: {vitals['resp']} breaths/min\n"
                if vitals.get('spo2'):
                    qr_text += f"    SpO2: {vitals['spo2']}%\n"

            qr_text += f"  Pharmacy: {visit.get('pharmacy_status', 'N/A')}\n"

        qr_text += f"\n"
        qr_text += f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        qr_text += f"{'='*40}\n"
        qr_text += f"Boolean Bros General Hospital\n"
        qr_text += f"Confidential Patient Information"

        return qr_text

    def generate_qr_code_image(self, patient_id, size=200):
        """Generate QR code as PIL Image"""
        qr_data = self.generate_patient_qr_data(patient_id)
        if not qr_data:
            return None

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        return img

    def generate_qr_code_tk_image(self, patient_id, size=200):
        """Generate QR code as Tkinter PhotoImage"""
        pil_image = self.generate_qr_code_image(patient_id, size)
        if pil_image:
            return ImageTk.PhotoImage(pil_image)
        return None

    def save_qr_code_image(self, patient_id, filepath, size=300):
        """Save QR code to file"""
        pil_image = self.generate_qr_code_image(patient_id, size)
        if pil_image:
            pil_image.save(filepath, "PNG")
            return True
        return False

# ---------------------
# Utilities
# ---------------------
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def ensure_db():
    """Create DB and seed sample users if not exists."""
    create = not os.path.exists(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Users: id, name, mobile (unique), password_hash, role ('receptionist'|'doctor'|'pharmacist')
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Patients: id, full_name, address, dob (optional), created_at
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            address TEXT,
            dob TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Visits: id, patient_id, assigned_doctor_id (references users.id), date (YYYY-MM-DD), time_in, time_out, service, status, vitals_json, doctor_notes
    c.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            assigned_doctor_id INTEGER,
            date TEXT NOT NULL,
            time_in TEXT,
            time_out TEXT,
            service TEXT,
            status TEXT,
            vitals_json TEXT,
            doctor_notes TEXT,
            pharmacy_instructions TEXT,
            pharmacy_status TEXT DEFAULT 'Pending'
        )
    """)

    conn.commit()

    # Seed users if DB new
    if create:
        try:
            # Clear existing users first
            c.execute("DELETE FROM users")

            # Add new users with provided credentials
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("MO11", "0788365067", sha256("recept123"), "receptionist"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Fabby", "0677532140", sha256("recept123"), "receptionist"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Mohammed Aminu", "7681969865", sha256("doctor123"), "doctor"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Collins Mark", "9781328959", sha256("doctor123"), "doctor"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Little MO", "0777730606", sha256("pharma123"), "pharmacist"))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

        # Create sample patients and visits
        sample_patients = [
            ("John Doe", "123 Main St", "1990-01-01"),
            ("Jane Smith", "456 Oak Ave", "1985-03-15"),
            ("Robert Brown", "789 Pine Rd", "1978-07-22"),
            ("Emily Davis", "321 Elm St", "1995-12-10")
        ]

        for patient in sample_patients:
            c.execute("INSERT INTO patients (full_name,address,dob,created_at) VALUES (?,?,?,?)",
                      (patient[0], patient[1], patient[2], datetime.now().isoformat()))

        # Sample visits - create visits for multiple days
        today = date.today()
        vitals_samples = [
            {"bp": "120/80", "hr": 78, "temp": 98.6, "resp": 16, "spo2": 98},
            {"bp": "130/85", "hr": 72, "temp": 98.4, "resp": 18, "spo2": 99},
            {"bp": "118/75", "hr": 65, "temp": 98.8, "resp": 15, "spo2": 97},
            {"bp": "140/90", "hr": 82, "temp": 99.1, "resp": 20, "spo2": 96}
        ]

        # Create visits for the last 5 days
        for day_offset in range(5):
            visit_date = (today - timedelta(days=day_offset)).isoformat()
            for i, vitals in enumerate(vitals_samples, 1):
                patient_id = i
                if patient_id > len(sample_patients):
                    patient_id = len(sample_patients)  # Ensure valid patient ID

                c.execute("""INSERT INTO visits 
                        (patient_id, assigned_doctor_id, date, time_in, time_out, service, status, vitals_json, doctor_notes, pharmacy_instructions, pharmacy_status)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                          (patient_id, 3 if i % 2 == 0 else 4, visit_date, f"09:{30+i%4}0", f"10:{15+i%4}0",
                           "General Consultation", "Done" if i % 2 == 0 else "Visit Pharmacy",
                           json.dumps(vitals), "Patient recovering well." if i % 2 == 0 else "Needs medication review.",
                           "Take medication as prescribed" if i % 2 == 0 else "Dispense antibiotics and pain relievers",
                           "Completed" if i % 2 == 0 else "Pending"))
        conn.commit()

    conn.close()

# ---------------------
# PDF Export Utilities
# ---------------------
class PDFExporter:
    def __init__(self, db):
        self.db = db

    def get_default_save_path(self, filename):
        """Get sensible default save paths"""
        # Try user's Desktop first
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.path.exists(desktop_path):
            return os.path.join(desktop_path, filename)

        # Fallback to user's Documents folder
        documents_path = os.path.join(os.path.expanduser("~"), "Documents")
        if os.path.exists(documents_path):
            return os.path.join(documents_path, filename)

        # Fallback to user's home directory
        home_path = os.path.expanduser("~")
        if os.path.exists(home_path):
            return os.path.join(home_path, filename)

        # Final fallback: current directory
        return filename

    def export_patient_report(self, patient_id, output_path=None):
        """Export comprehensive patient report to PDF"""
        patient = self.db.get_patient(patient_id)
        if not patient:
            raise ValueError("Patient not found")

        visits = self.db.get_visits_for_patient(patient_id)

        if not output_path:
            # Create default filename with better path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in patient["full_name"] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"patient_report_{safe_name}_{timestamp}.pdf"
            output_path = self.get_default_save_path(filename)

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Container for the 'Flowable' objects
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor(COLORS['primary'])
        )

        story.append(Paragraph("BOOLEAN BROS GENERAL HOSPITAL", title_style))
        story.append(Paragraph("PATIENT MEDICAL REPORT", title_style))
        story.append(Spacer(1, 20))

        # Patient Information Section
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )

        # Patient details table
        patient_data = [
            ["PATIENT INFORMATION", ""],
            ["Full Name:", patient["full_name"]],
            ["Patient ID:", str(patient["id"])],
            ["Date of Birth:", patient["dob"] or "Not provided"],
            ["Address:", patient["address"] or "Not provided"],
            ["Registered Date:", patient["created_at"][:10]],
            ["Report Generated:", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Total Visits:", str(len(visits))]
        ]

        patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['primary'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(patient_table)
        story.append(Spacer(1, 20))

        # Visit History Section
        if visits:
            story.append(Paragraph("VISIT HISTORY", styles['Heading2']))
            story.append(Spacer(1, 12))

            for i, visit in enumerate(visits, 1):
                # Visit header
                visit_header = f"Visit {i} - {visit['date']}"
                story.append(Paragraph(visit_header, styles['Heading3']))

                # Visit details table
                visit_data = [
                    ["Time", f"{visit['time_in'] or 'N/A'} - {visit['time_out'] or 'N/A'}"],
                    ["Service", visit['service'] or "Not specified"],
                    ["Status", visit['status'] or "Unknown"],
                    ["Doctor", visit['doctor_name'] or "Unassigned"],
                    ["Pharmacy Status", visit.get('pharmacy_status', 'N/A')]
                ]

                visit_table = Table(visit_data, colWidths=[1.5*inch, 4.5*inch])
                visit_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['secondary'])),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                ]))

                story.append(visit_table)
                story.append(Spacer(1, 10))

                # Vital Signs
                vitals = visit.get('vitals', {})
                if vitals:
                    story.append(Paragraph("Vital Signs:", styles['Heading4']))
                    vitals_data = [
                        ["Blood Pressure", vitals.get('bp', 'N/A')],
                        ["Heart Rate", str(vitals.get('hr', 'N/A')) + " bpm"],
                        ["Temperature", str(vitals.get('temp', 'N/A')) + " °F"],
                        ["Respiratory Rate", str(vitals.get('resp', 'N/A')) + " breaths/min"],
                        ["SpO2", str(vitals.get('spo2', 'N/A')) + " %"]
                    ]

                    vitals_table = Table(vitals_data, colWidths=[2*inch, 1*inch])
                    vitals_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.mistyrose),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                    ]))

                    story.append(vitals_table)
                    story.append(Spacer(1, 10))

                # Doctor Notes
                if visit.get('notes'):
                    story.append(Paragraph("Doctor's Notes:", styles['Heading4']))
                    notes_style = ParagraphStyle(
                        'NotesStyle',
                        parent=styles['Normal'],
                        fontSize=9,
                        backColor=colors.lightblue,
                        borderPadding=10,
                        spaceAfter=12
                    )
                    story.append(Paragraph(visit['notes'], notes_style))

                # Pharmacy Instructions
                if visit.get('pharmacy_instructions'):
                    story.append(Paragraph("Pharmacy Instructions:", styles['Heading4']))
                    pharma_style = ParagraphStyle(
                        'PharmaStyle',
                        parent=styles['Normal'],
                        fontSize=9,
                        backColor=colors.lightgreen,
                        borderPadding=10,
                        spaceAfter=12
                    )
                    story.append(Paragraph(visit['pharmacy_instructions'], pharma_style))

                story.append(Spacer(1, 15))

        else:
            story.append(Paragraph("No visit history found.", styles['Normal']))

        # Footer
        story.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        story.append(Paragraph("This is an official medical report from Boolean Bros General Hospital", footer_style))
        story.append(Paragraph("Confidential - For authorized personnel only", footer_style))

        # Build PDF
        doc.build(story)
        return output_path

    def export_visit_summary_report(self, visit_ids, output_path=None):
        """Export summary report for multiple visits"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"visit_summary_report_{timestamp}.pdf"
            output_path = self.get_default_save_path(filename)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor(COLORS['primary'])
        )

        story.append(Paragraph("BOOLEAN BROS GENERAL HOSPITAL", title_style))
        story.append(Paragraph("VISIT SUMMARY REPORT", title_style))
        story.append(Spacer(1, 20))

        # Summary information
        summary_data = [
            ["Report Date:", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Total Visits in Report:", str(len(visit_ids))],
            ["Generated By:", "Receptionist System"]
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Visit summaries
        for visit_id in visit_ids:
            visits = self.db.search_visits(str(visit_id), "all")
            if visits:
                visit = visits[0]
                story.append(Paragraph(f"Visit ID: {visit_id}", styles['Heading3']))

                visit_summary = [
                    ["Patient:", visit["patient_name"]],
                    ["Date:", visit["date"]],
                    ["Service:", visit["service"]],
                    ["Doctor:", visit["doctor_name"]],
                    ["Status:", visit["status"]],
                    ["Pharmacy Status:", visit.get("pharmacy_status", "N/A")]
                ]

                visit_table = Table(visit_summary, colWidths=[1.5*inch, 4.5*inch])
                visit_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['secondary'])),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                ]))

                story.append(visit_table)
                story.append(Spacer(1, 15))

        doc.build(story)
        return output_path

# ---------------------
# Database access helpers
# ---------------------
class DB:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file

    def connect(self):
        return sqlite3.connect(self.db_file)

    # User auth
    def authenticate_user(self, mobile, password_plain):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT id, name, mobile, password_hash, role FROM users WHERE mobile = ?", (mobile,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        uid, name, mob, pwd_hash, role = row
        if sha256(password_plain) == pwd_hash:
            return {"id": uid, "name": name, "mobile": mob, "role": role}
        return None

    def get_doctors(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT id, name, mobile FROM users WHERE role = 'doctor'")
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "mobile": r[2]} for r in rows]

    def get_pharmacists(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT id, name, mobile FROM users WHERE role = 'pharmacist'")
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "mobile": r[2]} for r in rows]

    # Patients
    def add_patient(self, full_name, address, dob):
        conn = self.connect()
        c = conn.cursor()
        c.execute("INSERT INTO patients (full_name,address,dob,created_at) VALUES (?,?,?,?)",
                  (full_name, address, dob or "", datetime.now().isoformat()))
        pid = c.lastrowid
        conn.commit()
        conn.close()
        return pid

    def update_patient(self, patient_id, full_name, address, dob):
        """Update patient information"""
        conn = self.connect()
        c = conn.cursor()
        c.execute("UPDATE patients SET full_name = ?, address = ?, dob = ? WHERE id = ?",
                  (full_name, address, dob or "", patient_id))
        conn.commit()
        conn.close()
        return True

    def list_patients(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT id, full_name, address, dob, created_at FROM patients ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "full_name": r[1], "address": r[2], "dob": r[3], "created_at": r[4]} for r in rows]

    def search_patients(self, search_term):
        conn = self.connect()
        c = conn.cursor()

        # Try to convert search term to integer for ID search
        try:
            search_id = int(search_term)
            c.execute("""SELECT id, full_name, address, dob, created_at FROM patients 
                         WHERE id = ? OR full_name LIKE ? OR address LIKE ? OR dob LIKE ?
                         ORDER BY id DESC""",
                      (search_id, f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        except ValueError:
            # If not a number, search only by text fields
            c.execute("""SELECT id, full_name, address, dob, created_at FROM patients 
                         WHERE full_name LIKE ? OR address LIKE ? OR dob LIKE ?
                         ORDER BY id DESC""",
                      (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))

        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "full_name": r[1], "address": r[2], "dob": r[3], "created_at": r[4]} for r in rows]

    def get_patient(self, patient_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT id, full_name, address, dob, created_at FROM patients WHERE id = ?", (patient_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        return {"id": row[0], "full_name": row[1], "address": row[2], "dob": row[3], "created_at": row[4]}

    def get_patient_visit_history(self, patient_id, days=5):
        """Get patient visit history for specified number of days"""
        conn = self.connect()
        c = conn.cursor()

        # Calculate date range
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=days-1)).isoformat()

        c.execute("""SELECT v.id, v.date, v.time_in, v.time_out, v.service, v.status, v.vitals_json, v.doctor_notes, 
                            v.pharmacy_instructions, v.pharmacy_status, u.id, u.name
                     FROM visits v LEFT JOIN users u ON v.assigned_doctor_id = u.id
                     WHERE v.patient_id = ? AND v.date BETWEEN ? AND ?
                     ORDER BY v.date DESC, v.time_in DESC""", (patient_id, start_date, end_date))
        rows = c.fetchall()
        conn.close()
        visits = []
        for r in rows:
            vid, date_s, tin, tout, service, status, vitals_json, notes, pharma_inst, pharma_status, doc_id, doc_name = r
            vitals = json.loads(vitals_json) if vitals_json else {}
            visits.append({
                "id": vid, "date": date_s, "time_in": tin, "time_out": tout, "service": service,
                "status": status, "vitals": vitals, "notes": notes,
                "pharmacy_instructions": pharma_inst, "pharmacy_status": pharma_status,
                "doctor_id": doc_id, "doctor_name": doc_name
            })
        return visits

    # Visits
    def add_visit(self, patient_id, assigned_doctor_id, visit_date, time_in, time_out, service, status, vitals_dict, doctor_notes, pharmacy_instructions=None):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""INSERT INTO visits 
            (patient_id, assigned_doctor_id, date, time_in, time_out, service, status, vitals_json, doctor_notes, pharmacy_instructions, pharmacy_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (patient_id, assigned_doctor_id, visit_date, time_in, time_out, service, status,
                   json.dumps(vitals_dict) if vitals_dict else None, doctor_notes, pharmacy_instructions, "Pending"))
        vid = c.lastrowid
        conn.commit()
        conn.close()
        return vid

    def update_visit(self, visit_id, assigned_doctor_id, visit_date, time_in, time_out, service, status, vitals_dict, doctor_notes, pharmacy_instructions=None):
        """Update existing visit information"""
        conn = self.connect()
        c = conn.cursor()
        c.execute("""UPDATE visits 
                    SET assigned_doctor_id = ?, date = ?, time_in = ?, time_out = ?, service = ?, 
                        status = ?, vitals_json = ?, doctor_notes = ?, pharmacy_instructions = ?
                    WHERE id = ?""",
                  (assigned_doctor_id, visit_date, time_in, time_out, service, status,
                   json.dumps(vitals_dict) if vitals_dict else None, doctor_notes,
                   pharmacy_instructions, visit_id))
        conn.commit()
        conn.close()
        return True

    def get_visit(self, visit_id):
        """Get specific visit by ID"""
        conn = self.connect()
        c = conn.cursor()
        c.execute("""SELECT v.id, v.patient_id, p.full_name, v.assigned_doctor_id, u.name as doctor_name,
                            v.date, v.time_in, v.time_out, v.service, v.status, v.vitals_json, 
                            v.doctor_notes, v.pharmacy_instructions, v.pharmacy_status
                     FROM visits v 
                     JOIN patients p ON v.patient_id = p.id 
                     LEFT JOIN users u ON v.assigned_doctor_id = u.id
                     WHERE v.id = ?""", (visit_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return None

        vid, pid, pname, doc_id, doc_name, date_s, tin, tout, service, status, vitals_json, notes, pharma_inst, pharma_status = row
        vitals = json.loads(vitals_json) if vitals_json else {}

        return {
            "visit_id": vid, "patient_id": pid, "patient_name": pname,
            "assigned_doctor_id": doc_id, "doctor_name": doc_name,
            "date": date_s, "time_in": tin, "time_out": tout, "service": service,
            "status": status, "vitals": vitals, "notes": notes,
            "pharmacy_instructions": pharma_inst, "pharmacy_status": pharma_status
        }

    def get_visits_for_patient(self, patient_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""SELECT v.id, v.date, v.time_in, v.time_out, v.service, v.status, v.vitals_json, v.doctor_notes, 
                            v.pharmacy_instructions, v.pharmacy_status, u.id, u.name
                     FROM visits v LEFT JOIN users u ON v.assigned_doctor_id = u.id
                     WHERE v.patient_id = ?
                     ORDER BY v.date DESC, v.time_in DESC""", (patient_id,))
        rows = c.fetchall()
        conn.close()
        visits = []
        for r in rows:
            vid, date_s, tin, tout, service, status, vitals_json, notes, pharma_inst, pharma_status, doc_id, doc_name = r
            vitals = json.loads(vitals_json) if vitals_json else {}
            visits.append({
                "id": vid, "date": date_s, "time_in": tin, "time_out": tout, "service": service,
                "status": status, "vitals": vitals, "notes": notes,
                "pharmacy_instructions": pharma_inst, "pharmacy_status": pharma_status,
                "doctor_id": doc_id, "doctor_name": doc_name
            })
        return visits

    def get_visits_for_doctor(self, doctor_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""SELECT v.id, v.patient_id, p.full_name, v.date, v.time_in, v.time_out, v.service, v.status, 
                            v.vitals_json, v.doctor_notes, v.pharmacy_instructions, v.pharmacy_status
                     FROM visits v JOIN patients p ON v.patient_id = p.id
                     WHERE v.assigned_doctor_id = ?
                     ORDER BY v.date DESC, v.time_in DESC""", (doctor_id,))
        rows = c.fetchall()
        conn.close()
        result = []
        for r in rows:
            vid, pid, pname, date_s, tin, tout, service, status, vitals_json, notes, pharma_inst, pharma_status = r
            vitals = json.loads(vitals_json) if vitals_json else {}
            result.append({
                "visit_id": vid, "patient_id": pid, "patient_name": pname, "date": date_s, "time_in": tin,
                "time_out": tout, "service": service, "status": status, "vitals": vitals, "notes": notes,
                "pharmacy_instructions": pharma_inst, "pharmacy_status": pharma_status
            })
        return result

    def get_visits_for_pharmacy(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""SELECT v.id, v.patient_id, p.full_name, v.date, v.time_in, v.time_out, v.service, v.status, 
                            v.vitals_json, v.doctor_notes, v.pharmacy_instructions, v.pharmacy_status, u.name as doctor_name
                     FROM visits v 
                     JOIN patients p ON v.patient_id = p.id 
                     LEFT JOIN users u ON v.assigned_doctor_id = u.id
                     WHERE v.pharmacy_status = 'Pending' OR v.status = 'Visit Pharmacy'
                     ORDER BY v.date DESC, v.time_in DESC""")
        rows = c.fetchall()
        conn.close()
        result = []
        for r in rows:
            vid, pid, pname, date_s, tin, tout, service, status, vitals_json, notes, pharma_inst, pharma_status, doc_name = r
            vitals = json.loads(vitals_json) if vitals_json else {}
            result.append({
                "visit_id": vid, "patient_id": pid, "patient_name": pname, "date": date_s, "time_in": tin,
                "time_out": tout, "service": service, "status": status, "vitals": vitals, "notes": notes,
                "pharmacy_instructions": pharma_inst, "pharmacy_status": pharma_status, "doctor_name": doc_name
            })
        return result

    def update_visit_status(self, visit_id, new_status, doctor_notes=None, pharmacy_instructions=None):
        conn = self.connect()
        c = conn.cursor()
        if pharmacy_instructions:
            c.execute("UPDATE visits SET status = ?, doctor_notes = ?, pharmacy_instructions = ? WHERE id = ?",
                     (new_status, doctor_notes, pharmacy_instructions, visit_id))
        else:
            c.execute("UPDATE visits SET status = ?, doctor_notes = ? WHERE id = ?",
                     (new_status, doctor_notes, visit_id))
        conn.commit()
        conn.close()

    def update_pharmacy_status_and_timeout(self, visit_id, new_status):
        """Update pharmacy status and set time_out when marking as completed"""
        conn = self.connect()
        c = conn.cursor()

        if new_status == "Completed":
            time_out = datetime.now().strftime("%H:%M")
            c.execute("UPDATE visits SET pharmacy_status = ?, time_out = ? WHERE id = ?",
                     (new_status, time_out, visit_id))
        else:
            c.execute("UPDATE visits SET pharmacy_status = ? WHERE id = ?", (new_status, visit_id))

        conn.commit()
        conn.close()

    def search_visits(self, search_term, role="all"):
        conn = self.connect()
        c = conn.cursor()

        # Try to convert search term to integer for ID search
        try:
            search_id = int(search_term)
            if role == "pharmacy":
                query = """SELECT v.id, v.patient_id, p.full_name, v.date, v.time_in, v.time_out, v.service, v.status, 
                                  v.vitals_json, v.doctor_notes, v.pharmacy_instructions, v.pharmacy_status, u.name as doctor_name
                           FROM visits v 
                           JOIN patients p ON v.patient_id = p.id 
                           JOIN users u ON v.assigned_doctor_id = u.id
                           WHERE (v.id = ? OR p.full_name LIKE ? OR v.service LIKE ? OR v.pharmacy_instructions LIKE ?)
                             AND (v.pharmacy_status = 'Pending' OR v.status = 'Visit Pharmacy')
                           ORDER BY v.date DESC, v.time_in DESC"""
                c.execute(query, (search_id, f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            else:
                query = """SELECT v.id, v.patient_id, p.full_name, v.date, v.time_in, v.time_out, v.service, v.status, 
                                  v.vitals_json, v.doctor_notes, v.pharmacy_instructions, v.pharmacy_status, u.name as doctor_name
                           FROM visits v 
                           JOIN patients p ON v.patient_id = p.id 
                           JOIN users u ON v.assigned_doctor_id = u.id
                           WHERE v.id = ? OR p.full_name LIKE ? OR v.service LIKE ? OR v.doctor_notes LIKE ? OR v.pharmacy_instructions LIKE ?
                           ORDER BY v.date DESC, v.time_in DESC"""
                c.execute(query, (search_id, f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        except ValueError:
            # If not a number, search only by text fields
            if role == "pharmacy":
                query = """SELECT v.id, v.patient_id, p.full_name, v.date, v.time_in, v.time_out, v.service, v.status, 
                                  v.vitals_json, v.doctor_notes, v.pharmacy_instructions, v.pharmacy_status, u.name as doctor_name
                           FROM visits v 
                           JOIN patients p ON v.patient_id = p.id 
                           JOIN users u ON v.assigned_doctor_id = u.id
                           WHERE (p.full_name LIKE ? OR v.service LIKE ? OR v.pharmacy_instructions LIKE ?)
                             AND (v.pharmacy_status = 'Pending' OR v.status = 'Visit Pharmacy')
                           ORDER BY v.date DESC, v.time_in DESC"""
                c.execute(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            else:
                query = """SELECT v.id, v.patient_id, p.full_name, v.date, v.time_in, v.time_out, v.service, v.status, 
                                  v.vitals_json, v.doctor_notes, v.pharmacy_instructions, v.pharmacy_status, u.name as doctor_name
                           FROM visits v 
                           JOIN patients p ON v.patient_id = p.id 
                           JOIN users u ON v.assigned_doctor_id = u.id
                           WHERE p.full_name LIKE ? OR v.service LIKE ? OR v.doctor_notes LIKE ? OR v.pharmacy_instructions LIKE ?
                           ORDER BY v.date DESC, v.time_in DESC"""
                c.execute(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))

        rows = c.fetchall()
        conn.close()
        result = []
        for r in rows:
            vid, pid, pname, date_s, tin, tout, service, status, vitals_json, notes, pharma_inst, pharma_status, doc_name = r
            vitals = json.loads(vitals_json) if vitals_json else {}
            result.append({
                "visit_id": vid, "patient_id": pid, "patient_name": pname, "date": date_s, "time_in": tin,
                "time_out": tout, "service": service, "status": status, "vitals": vitals, "notes": notes,
                "pharmacy_instructions": pharma_inst, "pharmacy_status": pharma_status, "doctor_name": doc_name
            })
        return result

    # Dashboard stats
    def visits_on_date(self, date_str):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""SELECT id, status FROM visits WHERE date = ?""", (date_str,))
        rows = c.fetchall()
        conn.close()
        return rows

    def get_todays_visits_count(self):
        conn = self.connect()
        c = conn.cursor()
        today = date.today().isoformat()
        c.execute("SELECT COUNT(*) FROM visits WHERE date = ?", (today,))
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_total_patients_count(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM patients")
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_pending_pharmacy_count(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM visits WHERE pharmacy_status = 'Pending'")
        count = c.fetchone()[0]
        conn.close()
        return count

# ---------------------
# Styled Widgets
# ---------------------
class StyledButton(ttk.Button):
    def __init__(self, parent, text, command, style="Accent.TButton", width=None):
        super().__init__(parent, text=text, command=command, style=style, width=width)

class CardFrame(ttk.Frame):
    def __init__(self, parent, title="", padding=10, width=200, height=100):
        super().__init__(parent, relief="raised", borderwidth=1, padding=padding)
        self.configure(style="Card.TFrame")
        if title:
            title_label = ttk.Label(self, text=title, font=("Helvetica", 10, "bold"),
                     foreground=COLORS['primary'], style="Card.TLabel")
            title_label.pack(anchor="w", pady=(0, 5))

    def add_content(self, widget):
        widget.pack(fill="both", expand=True, pady=(5, 0))

# ---------------------
# GUI Application
# ---------------------
class VitalSignApp(tk.Tk):
    def __init__(self, db: DB):
        super().__init__()
        self.title("VitalSign Pro - Medical Informatics Console")
        self.geometry("1200x750")
        self.minsize(1100, 700)
        self.db = db
        self.current_user = None
        self._frame = None
        self.pdf_exporter = PDFExporter(db)
        self.qr_generator = QRCodeGenerator(db)  # NEW ADDITION

        # Configure styles
        self.configure_styles()
        self.show_login()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors
        self.configure(bg=COLORS['background'])

        # Primary button style - Improved visibility
        style.configure("Accent.TButton",
                       background=COLORS['primary'],
                       foreground="white",
                       borderwidth=0,
                       focuscolor="none",
                       padding=(15, 8),
                       font=('Helvetica', 9, 'bold'))
        style.map("Accent.TButton",
                 background=[('active', COLORS['secondary']),
                           ('pressed', COLORS['primary'])])

        # Secondary button style - Improved visibility
        style.configure("Secondary.TButton",
                       background=COLORS['light'],
                       foreground=COLORS['dark'],
                       borderwidth=1,
                       focuscolor="none",
                       padding=(15, 8),
                       font=('Helvetica', 9))
        style.map("Secondary.TButton",
                 background=[('active', COLORS['border'])])

        # Card styles
        style.configure("Card.TFrame", background=COLORS['card_bg'])
        style.configure("Card.TLabel", background=COLORS['card_bg'])

        # Treeview style
        style.configure("Treeview",
                       background=COLORS['card_bg'],
                       fieldbackground=COLORS['card_bg'],
                       foreground=COLORS['dark'],
                       rowheight=25)
        style.configure("Treeview.Heading",
                       background=COLORS['primary'],
                       foreground="white",
                       relief="flat",
                       padding=(5, 5),
                       font=('Helvetica', 9, 'bold'))
        style.map("Treeview.Heading",
                 background=[('active', COLORS['secondary'])])

        # Label styles
        style.configure("Title.TLabel",
                       font=("Helvetica", 16, "bold"),
                       foreground=COLORS['primary'],
                       background=COLORS['background'])

        style.configure("Subtitle.TLabel",
                       font=("Helvetica", 12),
                       foreground=COLORS['dark'],
                       background=COLORS['background'])

        style.configure("Bold.TLabel",
                       font=("Helvetica", 10, "bold"),
                       foreground=COLORS['dark'],
                       background=COLORS['card_bg'])

        # Status bar style
        style.configure("Status.TFrame", background=COLORS['primary'])
        style.configure("Status.TLabel",
                       background=COLORS['primary'],
                       foreground="white",
                       font=('Helvetica', 9))

    def show_frame(self, frame_class, *args, **kwargs):
        """Destroys current frame and replaces with new one"""
        new_frame = frame_class(self, *args, **kwargs)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.pack(fill="both", expand=True)

    def show_login(self):
        self.show_frame(LoginFrame)

    def login_success(self, user_dict):
        self.current_user = user_dict
        if user_dict["role"] == "receptionist":
            self.show_frame(ReceptionistMain, user_dict)
        elif user_dict["role"] == "doctor":
            self.show_frame(DoctorMain, user_dict)
        elif user_dict["role"] == "pharmacist":
            self.show_frame(PharmacistMain, user_dict)
        else:
            messagebox.showerror("Role Error", f"Unknown role: {user_dict['role']}")
            self.show_login()

    def logout(self):
        self.current_user = None
        self.show_login()

# ---------------------
# Login Frame
# ---------------------
class LoginFrame(tk.Frame):
    def __init__(self, master: VitalSignApp):
        super().__init__(master, bg=COLORS['background'])
        self.master = master
        self.db = master.db
        self.build()

    def build(self):
        # Main container
        main_container = tk.Frame(self, bg=COLORS['background'], padx=40, pady=60)
        main_container.pack(expand=True, fill="both")

        # Login card
        login_card = tk.Frame(main_container, bg=COLORS['card_bg'], padx=40, pady=40,
                            relief="raised", borderwidth=1)
        login_card.pack(expand=True)

        # Title
        title = ttk.Label(login_card, text="VitalSign Pro",
                         font=("Helvetica", 24, "bold"),
                         foreground=COLORS['primary'],
                         background=COLORS['card_bg'])
        title.pack(pady=(0, 10))

        subtitle = ttk.Label(login_card, text="Medical Informatics Console",
                           font=("Helvetica", 12),
                           foreground=COLORS['dark'],
                           background=COLORS['card_bg'])
        subtitle.pack(pady=(0, 30))

        # Form container
        form_frame = tk.Frame(login_card, bg=COLORS['card_bg'])
        form_frame.pack(fill="x")

        # Mobile field
        ttk.Label(form_frame, text="Mobile Number:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.mobile_var = tk.StringVar()
        mobile_entry = ttk.Entry(form_frame, textvariable=self.mobile_var, font=("Helvetica", 11), width=25)
        mobile_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        # Password field
        ttk.Label(form_frame, text="Password:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(form_frame, show="•", textvariable=self.password_var,
                                 font=("Helvetica", 11), width=25)
        password_entry.grid(row=3, column=0, sticky="ew", pady=(0, 25))

        # Login button
        login_btn = StyledButton(form_frame, text="Login", command=self.attempt_login, width=20)
        login_btn.grid(row=4, column=0, pady=(0, 20))

        # Bind Enter key to login
        mobile_entry.bind('<Return>', lambda e: self.attempt_login())
        password_entry.bind('<Return>', lambda e: self.attempt_login())

        # Focus on mobile field
        mobile_entry.focus()

    def attempt_login(self):
        mobile = self.mobile_var.get().strip()
        pwd = self.password_var.get()
        if not mobile or not pwd:
            messagebox.showwarning("Input Required", "Please enter mobile number and password.")
            return
        user = self.db.authenticate_user(mobile, pwd)
        if not user:
            messagebox.showerror("Login Failed", "Invalid mobile number or password.")
            return
        self.master.login_success(user)

# ---------------------
# Base Main Frame with common layout helpers
# ---------------------
class MainBaseFrame(tk.Frame):
    def __init__(self, master: VitalSignApp, user):
        super().__init__(master, bg=COLORS['background'])
        self.master = master
        self.user = user
        self.db = master.db
        self.qr_generator = master.qr_generator  # NEW ADDITION
        self.build_layout()

    def build_layout(self):
        # Top header
        header = tk.Frame(self, bg=COLORS['primary'], height=80)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        # Hospital name and welcome - Improved styling
        title_frame = tk.Frame(header, bg=COLORS['primary'])
        title_frame.pack(side="left", padx=20, pady=15)

        hospital_label = ttk.Label(title_frame, text="Boolean Bros General Hospital",
                                 font=("Helvetica", 16, "bold"),
                                 foreground="white",
                                 background=COLORS['primary'])
        hospital_label.pack(anchor="w")

        welcome_label = ttk.Label(title_frame, text=f"Welcome, {self.user['name']} ({self.user['role'].title()})",
                                font=("Helvetica", 11, "bold"),
                                foreground=COLORS['light'],
                                background=COLORS['primary'])
        welcome_label.pack(anchor="w", pady=(2, 0))

        # Logout button
        logout_btn = StyledButton(header, text=f"Logout",
                                command=self.master.logout,
                                style="Secondary.TButton")
        logout_btn.pack(side="right", padx=20, pady=20)

        # Main content area
        self.main_pane = tk.Frame(self, bg=COLORS['background'])
        self.main_pane.pack(fill="both", expand=True, padx=20, pady=20)

        # Left navigation
        self.left_nav = tk.Frame(self.main_pane, bg=COLORS['card_bg'], width=220,
                               relief="raised", borderwidth=1)
        self.left_nav.pack(side="left", fill="y", padx=(0, 20))
        self.left_nav.pack_propagate(False)

        # Logo/header in nav
        nav_header = tk.Frame(self.left_nav, bg=COLORS['primary'], height=100)
        nav_header.pack(fill="x")
        nav_header.pack_propagate(False)

        ttk.Label(nav_header, text="Navigation",
                 font=("Helvetica", 12, "bold"),
                 foreground="white",
                 background=COLORS['primary']).pack(expand=True, pady=35)

        # Navigation buttons container
        self.nav_buttons_frame = tk.Frame(self.left_nav, bg=COLORS['card_bg'], padx=10, pady=20)
        self.nav_buttons_frame.pack(fill="both", expand=True)

        # Right content area
        self.right_content = tk.Frame(self.main_pane, bg=COLORS['background'])
        self.right_content.pack(side="left", fill="both", expand=True)

    def add_nav_button(self, text, command, is_selected=False):
        btn_frame = tk.Frame(self.nav_buttons_frame, bg=COLORS['card_bg'])
        btn_frame.pack(fill="x", pady=2)

        btn_style = "Accent.TButton" if is_selected else "Secondary.TButton"
        btn = StyledButton(btn_frame, text=text, command=command, style=btn_style, width=18)
        btn.pack(fill="x")

    def clear_right(self):
        for w in self.right_content.winfo_children():
            w.destroy()

    def create_card(self, parent, title, width=200, height=120):
        return CardFrame(parent, title=title, width=width, height=height)

    def create_search_bar(self, parent, search_callback, placeholder="Search..."):
        search_frame = tk.Frame(parent, bg=COLORS['background'])
        search_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(search_frame, text="Search:", background=COLORS['background'],
                 font=('Helvetica', 9, 'bold')).pack(side="left", padx=(0, 10))

        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40, font=('Helvetica', 9))
        search_entry.pack(side="left", padx=(0, 10))
        search_entry.insert(0, placeholder)

        search_btn = StyledButton(search_frame, text="Search",
                                 command=lambda: search_callback(search_var.get()),
                                 width=10)
        search_btn.pack(side="left", padx=(0, 10))

        clear_btn = StyledButton(search_frame, text="Clear",
                                command=lambda: [search_var.set(""), search_callback("")],
                                style="Secondary.TButton", width=8)
        clear_btn.pack(side="left")

        return search_var

    def create_status_bar(self, parent, initial_text=""):
        """Create a visible status bar at the bottom"""
        status_frame = ttk.Frame(parent, style="Status.TFrame", height=28)
        status_frame.pack(fill="x", pady=(10, 0))
        status_frame.pack_propagate(False)

        status_label = ttk.Label(status_frame, text=initial_text, style="Status.TLabel")
        status_label.pack(side="left", padx=10, pady=5)

        return status_label

# ---------------------
# Receptionist Main UI
# ---------------------
class ReceptionistMain(MainBaseFrame):
    def __init__(self, master, user):
        super().__init__(master, user)
        self.build_navigation()
        self.show_dashboard()

    def build_navigation(self):
        self.nav_buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("👥 View Patients", self.show_view_patients),
            ("➕ Add Patient", self.show_add_patient),
            ("📅 Today's Visits", self.show_todays_visits),
            ("💊 Pharmacy Queue", self.show_pharmacy_queue),
            ("📄 Export Reports", self.show_export_reports),
            ("🔲 QR Codes", self.show_qr_codes)  # NEW ADDITION
        ]

        for i, (text, command) in enumerate(self.nav_buttons):
            self.add_nav_button(text, command, is_selected=(i == 0))

    def show_dashboard(self):
        self.clear_right()

        # Header
        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 20))

        today = date.today().strftime("%A, %d %B %Y")
        ttk.Label(header_frame, text=f"Receptionist Dashboard — {today}",
                 style="Title.TLabel").pack(anchor="w")

        # Stats cards
        stats_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        stats_frame.pack(fill="x", pady=(0, 20))

        # Stats data
        total_patients = self.db.get_total_patients_count()
        todays_visits = self.db.get_todays_visits_count()
        pending_pharmacy = self.db.get_pending_pharmacy_count()
        date_str = date.today().isoformat()
        visits_data = self.db.visits_on_date(date_str)

        # Status distribution
        status_counts = {}
        for vid, status in visits_data:
            key = status or "Unknown"
            status_counts[key] = status_counts.get(key, 0) + 1

        if not status_counts:
            status_counts = {"Scheduled": 3, "In Progress": 2, "Completed": 5}

        # Create stat cards
        cards_data = [
            ("Total Patients", total_patients, COLORS['primary']),
            ("Today's Visits", todays_visits, COLORS['secondary']),
            ("Pending", status_counts.get("Pending", 0), COLORS['warning']),
            ("Pharmacy Queue", pending_pharmacy, COLORS['accent']),
            ("Completed", status_counts.get("Done", 0), COLORS['success'])
        ]

        for i, (title, value, color) in enumerate(cards_data):
            if i < 5:  # Limit to 5 cards per row
                card = self.create_card(stats_frame, title, width=180, height=100)
                card.grid(row=0, column=i, padx=(0, 15), sticky="nsew")

                value_label = ttk.Label(card, text=str(value),
                                      font=("Helvetica", 24, "bold"),
                                      foreground=color,
                                      background=COLORS['card_bg'])
                value_label.pack(expand=True)

        # Charts section
        charts_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        charts_frame.pack(fill="both", expand=True)

        # Left chart - Status distribution
        left_chart_frame = CardFrame(charts_frame, title="Today's Visit Status", padding=15)
        left_chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        labels = list(status_counts.keys())
        sizes = list(status_counts.values())

        fig1 = Figure(figsize=(5, 4), dpi=80, facecolor=COLORS['card_bg'])
        ax1 = fig1.add_subplot(111)
        colors = [COLORS['primary'], COLORS['secondary'], COLORS['success'], COLORS['warning'], COLORS['accent']]
        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors[:len(labels)])
        ax1.set_title("Visit Status Distribution", fontsize=12, fontweight='bold', pad=20)

        canvas1 = FigureCanvasTkAgg(fig1, left_chart_frame)
        canvas1.get_tk_widget().pack(fill="both", expand=True)
        canvas1.draw()

        # Right chart - Daily trend (simplified)
        right_chart_frame = CardFrame(charts_frame, title="Weekly Visit Trend", padding=15)
        right_chart_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        fig2 = Figure(figsize=(5, 4), dpi=80, facecolor=COLORS['card_bg'])
        ax2 = fig2.add_subplot(111)

        # Sample weekly data
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        visits = [12, 19, 15, 17, 14, 8, 10]  # Sample data

        ax2.bar(days, visits, color=COLORS['secondary'], alpha=0.7)
        ax2.set_ylabel('Number of Visits')
        ax2.set_title('Weekly Visit Volume', fontsize=12, fontweight='bold', pad=20)
        ax2.grid(True, alpha=0.3)

        canvas2 = FigureCanvasTkAgg(fig2, right_chart_frame)
        canvas2.get_tk_widget().pack(fill="both", expand=True)
        canvas2.draw()

        # Status bar
        self.create_status_bar(self.right_content, f"Dashboard loaded successfully | Total Patients: {total_patients} | Today's Visits: {todays_visits}")

    def show_view_patients(self):
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(header_frame, text="Patient Management", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="View and manage all registered patients",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # Search functionality - FIXED SEARCH
        def perform_search(search_term):
            if not search_term.strip():
                patients = self.db.list_patients()
            else:
                patients = self.db.search_patients(search_term)

            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)

            # Load filtered patients
            for p in patients:
                tree.insert("", "end", values=(
                    p["id"],
                    p["full_name"],
                    p["address"] or "Not provided",
                    p["dob"] or "Unknown",
                    p["created_at"][:10]
                ))

            # Update status
            status_label.config(text=f"Total patients: {len(patients)}")

        search_var = self.create_search_bar(self.right_content, perform_search, "Search by ID, name, address, or DOB...")

        # Patients table
        table_frame = CardFrame(self.right_content, padding=0)
        table_frame.pack(fill="both", expand=True)

        # Create treeview with scrollbar
        tree_scroll = ttk.Scrollbar(table_frame)
        tree_scroll.pack(side="right", fill="y")

        cols = ("id", "name", "address", "dob", "created_at")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15,
                           yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=tree.yview)

        # Configure columns
        columns_config = [
            ("id", "ID", 60),
            ("name", "Full Name", 200),
            ("address", "Address", 180),
            ("dob", "Date of Birth", 100),
            ("created_at", "Registered", 120)
        ]

        for col_id, heading, width in columns_config:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Load patients
        patients = self.db.list_patients()
        for p in patients:
            tree.insert("", "end", values=(
                p["id"],
                p["full_name"],
                p["address"] or "Not provided",
                p["dob"] or "Unknown",
                p["created_at"][:10]
            ))

        def on_select(event):
            item = tree.selection()
            if not item:
                return
            values = tree.item(item[0], "values")
            pid = int(values[0])
            self.show_patient_details(pid)

        tree.bind("<Double-1>", on_select)

        # Status bar with improved visibility
        status_label = self.create_status_bar(self.right_content, f"Total patients: {len(patients)}")

    def show_patient_details(self, patient_id):
        p = self.db.get_patient(patient_id)
        if not p:
            messagebox.showerror("Not Found", "Patient not found.")
            return

        top = tk.Toplevel(self)
        top.title(f"Patient Details — {p['full_name']} (ID: {p['id']})")
        top.geometry("1100x700")  # Adjusted size
        top.configure(bg=COLORS['background'])

        # Main container with tabs - NEW ADDITION
        notebook = ttk.Notebook(top)
        notebook.pack(fill="both", expand=True, padx=20, pady=20)

        # Tab 1: Patient Information
        info_tab = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(info_tab, text="Patient Information")

        # Header in info tab
        header = CardFrame(info_tab, padding=20)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(header, text=p["full_name"],
                 font=("Helvetica", 18, "bold"),
                 background=COLORS['card_bg']).pack(anchor="w")

        info_text = f"ID: {p['id']} | DOB: {p['dob'] or 'Not provided'} | Address: {p['address'] or 'Not provided'}"
        ttk.Label(header, text=info_text,
                 font=("Helvetica", 10),
                 background=COLORS['card_bg']).pack(anchor="w", pady=(5, 0))

        # Action buttons
        action_frame = tk.Frame(header, bg=COLORS['card_bg'])
        action_frame.pack(fill="x", pady=(10, 0))

        def edit_patient():
            self.edit_patient_details(p, top)

        def add_new_visit():
            self.add_visit_for_patient(p, top)

        def export_patient_pdf():
            try:
                filename = self.master.pdf_exporter.export_patient_report(patient_id)
                messagebox.showinfo("Export Successful", f"Patient report exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export PDF: {str(e)}")

        StyledButton(action_frame, text="✏️ Edit Patient",
                    command=edit_patient, style="Secondary.TButton").pack(side="left", padx=(0, 10))
        StyledButton(action_frame, text="➕ Add New Visit",
                    command=add_new_visit, style="Secondary.TButton").pack(side="left", padx=(0, 10))
        StyledButton(action_frame, text="📄 Export Patient Report (PDF)",
                    command=export_patient_pdf).pack(side="right")

        # Visit history with vitals - Show last 5 days
        visits_frame = CardFrame(info_tab, title=f"Visit History (Last 5 Days)", padding=15)
        visits_frame.pack(fill="both", expand=True, pady=(0, 20))

        visits = self.db.get_patient_visit_history(patient_id, days=5)

        if not visits:
            ttk.Label(visits_frame, text="No visit history found for the last 5 days.",
                     background=COLORS['card_bg']).pack(expand=True)
        else:
            # Create visits table with vitals and action buttons
            cols = ("date", "time", "service", "status", "doctor", "bp", "hr", "temp", "resp", "spo2", "pharmacy", "actions")
            tree = ttk.Treeview(visits_frame, columns=cols, show="headings", height=12)

            columns_config = [
                ("date", "Date", 100),
                ("time", "Time", 100),
                ("service", "Service", 150),
                ("status", "Status", 120),
                ("doctor", "Doctor", 150),
                ("bp", "BP", 80),
                ("hr", "HR", 60),
                ("temp", "Temp", 70),
                ("resp", "Resp", 70),
                ("spo2", "SpO2", 70),
                ("pharmacy", "Pharmacy", 120),
                ("actions", "Actions", 100)
            ]

            for col_id, heading, width in columns_config:
                tree.heading(col_id, text=heading)
                tree.column(col_id, width=width, anchor="w")

            # Add scrollbar
            tree_scroll = ttk.Scrollbar(visits_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=tree_scroll.set)
            tree.pack(side="left", fill="both", expand=True)
            tree_scroll.pack(side="right", fill="y")

            for v in visits:
                time_str = f"{v['time_in'] or ''} - {v['time_out'] or ''}"
                vitals = v.get('vitals', {})
                pharmacy_status = v.get("pharmacy_status", "N/A")

                tree.insert("", "end", values=(
                    v["date"],
                    time_str,
                    v["service"] or "Not specified",
                    v["status"] or "Unknown",
                    v["doctor_name"] or "Unassigned",
                    vitals.get('bp', 'N/A'),
                    vitals.get('hr', 'N/A'),
                    vitals.get('temp', 'N/A'),
                    vitals.get('resp', 'N/A'),
                    vitals.get('spo2', 'N/A'),
                    pharmacy_status,
                    "Edit"
                ))

            def on_tree_double_click(event):
                item = tree.selection()
                if not item:
                    return
                values = tree.item(item[0], "values")
                visit_date = values[0]

                # Find the visit ID
                visit_id = None
                for v in visits:
                    if v["date"] == visit_date and v["time_in"] == values[1].split(" - ")[0]:
                        visit_id = v["id"]
                        break

                if visit_id:
                    self.edit_visit_details(visit_id, top)

            tree.bind("<Double-1>", on_tree_double_click)

        # Tab 2: QR Code - MODIFIED VERSION
        qr_tab = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(qr_tab, text="Patient QR Code")

        # QR Code content - SIMPLIFIED
        qr_frame = CardFrame(qr_tab, padding=30)
        qr_frame.pack(fill="both", expand=True)

        ttk.Label(qr_frame, text="Patient QR Code",
                 font=("Helvetica", 16, "bold"),
                 background=COLORS['card_bg']).pack(pady=(0, 20))

        ttk.Label(qr_frame, text="Scan this QR code to view the patient's last 4 hospital visits",
                 background=COLORS['card_bg']).pack(pady=(0, 30))

        # Generate and display QR code
        qr_image = self.qr_generator.generate_qr_code_tk_image(patient_id, size=300)
        if qr_image:
            qr_label = ttk.Label(qr_frame, image=qr_image, background=COLORS['card_bg'])
            qr_label.image = qr_image  # Keep a reference to prevent garbage collection
            qr_label.pack(pady=20)

        # SINGLE ACTION BUTTON - Print QR (Non-functional)
        action_frame = tk.Frame(qr_frame, bg=COLORS['card_bg'])
        action_frame.pack(fill="x", pady=(30, 0))

        def print_qr_nothing():
            # This button does nothing as requested
            pass

        # Only one button now - Print QR (non-functional)
        print_btn = StyledButton(action_frame, text="🖨️ Print QR",
                    command=print_qr_nothing)
        print_btn.pack()

    def show_qr_codes(self):
        """NEW FEATURE: View and manage all patient QR codes"""
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 20))

        ttk.Label(header_frame, text="Patient QR Codes", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Generate and manage QR codes for all patients",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # Search functionality - FIXED SEARCH
        def perform_search(search_term):
            if not search_term.strip():
                patients = self.db.list_patients()
            else:
                patients = self.db.search_patients(search_term)

            # Clear existing content
            for widget in patients_frame.winfo_children():
                widget.destroy()

            # Display patients in a grid with their QR codes
            if not patients:
                ttk.Label(patients_frame, text="No patients found.",
                         background=COLORS['background']).pack(expand=True)
                return

            # Create a scrollable frame for patients
            canvas = tk.Canvas(patients_frame, bg=COLORS['background'], highlightthickness=0)
            scrollbar = ttk.Scrollbar(patients_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas, style="Card.TFrame")

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Display patients in a grid (2 columns)
            row, col = 0, 0
            for patient in patients:
                patient_card = CardFrame(scrollable_frame, padding=15)
                patient_card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

                # Patient info
                ttk.Label(patient_card, text=patient["full_name"],
                         font=("Helvetica", 12, "bold"),
                         background=COLORS['card_bg']).pack(anchor="w")

                ttk.Label(patient_card, text=f"ID: {patient['id']} | DOB: {patient['dob'] or 'N/A'}",
                         background=COLORS['card_bg']).pack(anchor="w", pady=(2, 10))

                # Generate and display QR code
                qr_image = self.qr_generator.generate_qr_code_tk_image(patient["id"], size=150)
                if qr_image:
                    qr_label = ttk.Label(patient_card, image=qr_image, background=COLORS['card_bg'])
                    qr_label.image = qr_image
                    qr_label.pack(pady=5)

                # SINGLE ACTION BUTTON - Print QR (Non-functional)
                btn_frame = tk.Frame(patient_card, bg=COLORS['card_bg'])
                btn_frame.pack(fill="x", pady=(10, 0))

                def print_qr_nothing():
                    # This button does nothing as requested
                    pass

                StyledButton(btn_frame, text="🖨️ Print QR",
                            command=print_qr_nothing,
                            style="Secondary.TButton").pack(fill="x")

                # Update grid position
                col += 1
                if col >= 2:  # 2 columns
                    col = 0
                    row += 1

            # Configure grid weights for responsive layout
            scrollable_frame.columnconfigure(0, weight=1)
            scrollable_frame.columnconfigure(1, weight=1)

        search_var = self.create_search_bar(self.right_content, perform_search, "Search patients by ID or name...")

        # Patients container
        patients_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        patients_frame.pack(fill="both", expand=True)

        # Bulk actions
        bulk_frame = CardFrame(self.right_content, title="Bulk QR Code Operations", padding=15)
        bulk_frame.pack(fill="x", pady=(20, 0))

        def generate_all_qr_codes():
            patients = self.db.list_patients()
            if not patients:
                messagebox.showinfo("No Patients", "No patients found to generate QR codes for.")
                return

            from tkinter import filedialog
            folder = filedialog.askdirectory(title="Select folder to save all QR codes")
            if folder:
                success_count = 0
                for patient in patients:
                    filename = os.path.join(folder, f"patient_{patient['id']}_{patient['full_name'].replace(' ', '_')}.png")
                    if self.qr_generator.save_qr_code_image(patient["id"], filename):
                        success_count += 1

                messagebox.showinfo("Bulk Export Complete",
                                  f"Successfully generated {success_count} out of {len(patients)} QR codes in:\n{folder}")

        StyledButton(bulk_frame, text="📁 Generate All QR Codes",
                    command=generate_all_qr_codes).pack(side="left")

        # Load initial patients
        perform_search("")

        # Status bar
        self.create_status_bar(self.right_content, "QR code management - Scan any code to view patient's last 4 visits")

    def edit_patient_details(self, patient, parent_window):
        """Edit patient information"""
        top = tk.Toplevel(parent_window)
        top.title(f"Edit Patient — {patient['full_name']}")
        top.geometry("500x400")
        top.configure(bg=COLORS['background'])

        main_frame = CardFrame(top, padding=20)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text=f"Edit Patient: {patient['full_name']}",
                 font=("Helvetica", 16, "bold"),
                 background=COLORS['card_bg']).pack(anchor="w", pady=(0, 20))

        # Form fields
        fields_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        fields_frame.pack(fill="both", expand=True)

        # Full Name
        ttk.Label(fields_frame, text="Full Name:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=0, column=0, sticky="w", pady=8)
        name_var = tk.StringVar(value=patient["full_name"])
        ttk.Entry(fields_frame, textvariable=name_var, width=40).grid(row=0, column=1, sticky="w", pady=8, padx=(10, 0))

        # Address
        ttk.Label(fields_frame, text="Address:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=1, column=0, sticky="w", pady=8)
        address_var = tk.StringVar(value=patient["address"] or "")
        ttk.Entry(fields_frame, textvariable=address_var, width=40).grid(row=1, column=1, sticky="w", pady=8, padx=(10, 0))

        # Date of Birth
        ttk.Label(fields_frame, text="Date of Birth (YYYY-MM-DD):",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=2, column=0, sticky="w", pady=8)
        dob_var = tk.StringVar(value=patient["dob"] or "")
        ttk.Entry(fields_frame, textvariable=dob_var, width=40).grid(row=2, column=1, sticky="w", pady=8, padx=(10, 0))

        def save_changes():
            if not name_var.get().strip():
                messagebox.showwarning("Input Required", "Full name is required.")
                return

            self.db.update_patient(patient["id"], name_var.get().strip(),
                                 address_var.get().strip(), dob_var.get().strip())
            messagebox.showinfo("Success", "Patient information updated successfully.")
            top.destroy()
            parent_window.destroy()  # Close the details window to refresh
            self.show_patient_details(patient["id"])  # Reopen with updated data

        # Buttons
        button_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        button_frame.pack(fill="x", pady=(20, 0))

        StyledButton(button_frame, text="Save Changes",
                    command=save_changes).pack(side="right", padx=(10, 0))

        StyledButton(button_frame, text="Cancel",
                    command=top.destroy,
                    style="Secondary.TButton").pack(side="right")

    def add_visit_for_patient(self, patient, parent_window):
        """Add a new visit for existing patient"""
        top = tk.Toplevel(parent_window)
        top.title(f"Add Visit — {patient['full_name']}")
        top.geometry("600x500")
        top.configure(bg=COLORS['background'])

        main_frame = CardFrame(top, padding=20)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text=f"Add New Visit for: {patient['full_name']}",
                 font=("Helvetica", 16, "bold"),
                 background=COLORS['card_bg']).pack(anchor="w", pady=(0, 20))

        # Form fields
        fields_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        fields_frame.pack(fill="both", expand=True)

        # Date
        ttk.Label(fields_frame, text="Date (YYYY-MM-DD):",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=0, column=0, sticky="w", pady=8)
        date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(fields_frame, textvariable=date_var, width=30).grid(row=0, column=1, sticky="w", pady=8, padx=(10, 0))

        # Time In
        ttk.Label(fields_frame, text="Time In (HH:MM):",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=1, column=0, sticky="w", pady=8)
        time_in_var = tk.StringVar(value=datetime.now().strftime("%H:%M"))
        ttk.Entry(fields_frame, textvariable=time_in_var, width=30).grid(row=1, column=1, sticky="w", pady=8, padx=(10, 0))

        # Assign Doctor
        ttk.Label(fields_frame, text="Assign Doctor:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=2, column=0, sticky="w", pady=8)

        doctors = self.db.get_doctors()
        doctor_map = {f"{d['name']} ({d['mobile']})": d['id'] for d in doctors}
        doctor_var = tk.StringVar()
        doctor_combo = ttk.Combobox(fields_frame, textvariable=doctor_var,
                                   values=list(doctor_map.keys()), state="readonly", width=28)
        doctor_combo.grid(row=2, column=1, sticky="w", pady=8, padx=(10, 0))

        # Service
        ttk.Label(fields_frame, text="Service:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=3, column=0, sticky="w", pady=8)
        service_var = tk.StringVar()
        service_combo = ttk.Combobox(fields_frame, textvariable=service_var,
                                    values=["General Consultation", "Follow-up", "Emergency", "Specialist Referral", "Lab Test"],
                                    state="readonly", width=28)
        service_combo.grid(row=3, column=1, sticky="w", pady=8, padx=(10, 0))

        # Status
        ttk.Label(fields_frame, text="Status:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=4, column=0, sticky="w", pady=8)
        status_var = tk.StringVar(value="Scheduled")
        status_combo = ttk.Combobox(fields_frame, textvariable=status_var,
                                   values=["Scheduled", "In Progress", "Done", "Visit Pharmacy", "Come again"],
                                   state="readonly", width=28)
        status_combo.grid(row=4, column=1, sticky="w", pady=8, padx=(10, 0))

        def save_visit():
            if not doctor_var.get():
                messagebox.showwarning("Input Required", "Please assign a doctor.")
                return

            if not service_var.get():
                messagebox.showwarning("Input Required", "Please select a service.")
                return

            assigned_doc_id = doctor_map.get(doctor_var.get())

            self.db.add_visit(patient["id"], assigned_doc_id, date_var.get(),
                            time_in_var.get(), None, service_var.get(),
                            status_var.get(), {}, None)

            messagebox.showinfo("Success", "New visit added successfully.")
            top.destroy()
            parent_window.destroy()  # Close the details window to refresh
            self.show_patient_details(patient["id"])  # Reopen with updated data

        # Buttons
        button_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        button_frame.pack(fill="x", pady=(20, 0))

        StyledButton(button_frame, text="Add Visit",
                    command=save_visit).pack(side="right", padx=(10, 0))

        StyledButton(button_frame, text="Cancel",
                    command=top.destroy,
                    style="Secondary.TButton").pack(side="right")

    def edit_visit_details(self, visit_id, parent_window):
        """Edit existing visit details"""
        visit = self.db.get_visit(visit_id)
        if not visit:
            messagebox.showerror("Not Found", "Visit not found.")
            return

        top = tk.Toplevel(parent_window)
        top.title(f"Edit Visit — {visit['patient_name']}")
        top.geometry("700x600")
        top.configure(bg=COLORS['background'])

        main_frame = CardFrame(top, padding=20)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text=f"Edit Visit for: {visit['patient_name']}",
                 font=("Helvetica", 16, "bold"),
                 background=COLORS['card_bg']).pack(anchor="w", pady=(0, 20))

        # Form fields
        fields_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        fields_frame.pack(fill="both", expand=True)

        # Date
        ttk.Label(fields_frame, text="Date (YYYY-MM-DD):",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=0, column=0, sticky="w", pady=8)
        date_var = tk.StringVar(value=visit["date"])
        ttk.Entry(fields_frame, textvariable=date_var, width=30).grid(row=0, column=1, sticky="w", pady=8, padx=(10, 0))

        # Time In
        ttk.Label(fields_frame, text="Time In (HH:MM):",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=1, column=0, sticky="w", pady=8)
        time_in_var = tk.StringVar(value=visit["time_in"] or "")
        ttk.Entry(fields_frame, textvariable=time_in_var, width=30).grid(row=1, column=1, sticky="w", pady=8, padx=(10, 0))

        # Time Out
        ttk.Label(fields_frame, text="Time Out (HH:MM):",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=2, column=0, sticky="w", pady=8)
        time_out_var = tk.StringVar(value=visit["time_out"] or "")
        ttk.Entry(fields_frame, textvariable=time_out_var, width=30).grid(row=2, column=1, sticky="w", pady=8, padx=(10, 0))

        # Assign Doctor
        ttk.Label(fields_frame, text="Assign Doctor:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=3, column=0, sticky="w", pady=8)

        doctors = self.db.get_doctors()
        doctor_map = {f"{d['name']} ({d['mobile']})": d['id'] for d in doctors}
        doctor_var = tk.StringVar()

        # Set current doctor if exists
        current_doctor = None
        for doc_text, doc_id in doctor_map.items():
            if doc_id == visit.get("assigned_doctor_id"):
                current_doctor = doc_text
                break

        doctor_combo = ttk.Combobox(fields_frame, textvariable=doctor_var,
                                   values=list(doctor_map.keys()), state="readonly", width=28)
        doctor_combo.grid(row=3, column=1, sticky="w", pady=8, padx=(10, 0))
        if current_doctor:
            doctor_var.set(current_doctor)

        # Service
        ttk.Label(fields_frame, text="Service:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=4, column=0, sticky="w", pady=8)
        service_var = tk.StringVar(value=visit["service"] or "")
        service_entry = ttk.Entry(fields_frame, textvariable=service_var, width=30)
        service_entry.grid(row=4, column=1, sticky="w", pady=8, padx=(10, 0))

        # Status
        ttk.Label(fields_frame, text="Status:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=5, column=0, sticky="w", pady=8)
        status_var = tk.StringVar(value=visit["status"] or "Scheduled")
        status_combo = ttk.Combobox(fields_frame, textvariable=status_var,
                                   values=["Scheduled", "In Progress", "Done", "Visit Pharmacy", "Come again"],
                                   state="readonly", width=28)
        status_combo.grid(row=5, column=1, sticky="w", pady=8, padx=(10, 0))

        # Doctor Notes
        ttk.Label(fields_frame, text="Doctor Notes:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=6, column=0, sticky="w", pady=8)
        notes_text = tk.Text(fields_frame, width=40, height=4, font=("Helvetica", 9))
        notes_text.grid(row=6, column=1, sticky="w", pady=8, padx=(10, 0))
        notes_text.insert("1.0", visit.get("notes", ""))

        # Pharmacy Instructions
        ttk.Label(fields_frame, text="Pharmacy Instructions:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=7, column=0, sticky="w", pady=8)
        pharmacy_text = tk.Text(fields_frame, width=40, height=3, font=("Helvetica", 9))
        pharmacy_text.grid(row=7, column=1, sticky="w", pady=8, padx=(10, 0))
        pharmacy_text.insert("1.0", visit.get("pharmacy_instructions", ""))

        def save_changes():
            if not doctor_var.get():
                messagebox.showwarning("Input Required", "Please assign a doctor.")
                return

            if not service_var.get().strip():
                messagebox.showwarning("Input Required", "Service is required.")
                return

            assigned_doc_id = doctor_map.get(doctor_var.get())
            notes = notes_text.get("1.0", "end-1c").strip()
            pharmacy_instructions = pharmacy_text.get("1.0", "end-1c").strip()

            self.db.update_visit(visit_id, assigned_doc_id, date_var.get(),
                               time_in_var.get(), time_out_var.get(),
                               service_var.get(), status_var.get(),
                               visit.get("vitals", {}), notes, pharmacy_instructions)

            messagebox.showinfo("Success", "Visit updated successfully.")
            top.destroy()
            parent_window.destroy()  # Close the details window to refresh
            self.show_patient_details(visit["patient_id"])  # Reopen with updated data

        # Buttons
        button_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        button_frame.pack(fill="x", pady=(20, 0))

        StyledButton(button_frame, text="Save Changes",
                    command=save_changes).pack(side="right", padx=(10, 0))

        StyledButton(button_frame, text="Cancel",
                    command=top.destroy,
                    style="Secondary.TButton").pack(side="right")

    def show_add_patient(self):
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 20))

        ttk.Label(header_frame, text="Add New Patient", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Register a new patient and create initial visit",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # Form container
        form_card = CardFrame(self.right_content, padding=25)
        form_card.pack(fill="both", expand=True)

        # Personal Information Section
        ttk.Label(form_card, text="Personal Information",
                 font=("Helvetica", 12, "bold"),
                 background=COLORS['card_bg']).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        # Form fields
        fields = [
            ("Full Name:", "name", True),
            ("Address:", "address", False),
            ("Date of Birth (YYYY-MM-DD):", "dob", False),
            ("Assign to Doctor:", "doctor", True),
            ("Visit Service:", "service", True),
        ]

        self.form_vars = {}
        for i, (label, field, required) in enumerate(fields):
            row = i + 1
            star = " *" if required else ""
            ttk.Label(form_card, text=f"{label}{star}",
                     background=COLORS['card_bg'],
                     font=('Helvetica', 9, 'bold')).grid(row=row, column=0, sticky="w", pady=8, padx=(0, 10))

            if field == "doctor":
                doctors = self.db.get_doctors()
                doctor_map = {f"{d['name']} ({d['mobile']})": d['id'] for d in doctors}
                var = tk.StringVar()
                combo = ttk.Combobox(form_card, textvariable=var, values=list(doctor_map.keys()), state="readonly", font=('Helvetica', 9))
                combo.grid(row=row, column=1, sticky="ew", pady=8)
                self.form_vars[field] = var
                self.doctor_map = doctor_map
            else:
                var = tk.StringVar()
                entry = ttk.Entry(form_card, textvariable=var, width=40, font=('Helvetica', 9))
                entry.grid(row=row, column=1, sticky="ew", pady=8)
                self.form_vars[field] = var

        # Configure grid weights
        form_card.columnconfigure(1, weight=1)

        # Buttons
        button_frame = tk.Frame(form_card, bg=COLORS['card_bg'])
        button_frame.grid(row=len(fields) + 2, column=0, columnspan=2, pady=(20, 0))

        StyledButton(button_frame, text="Clear Form",
                    command=self.clear_form,
                    style="Secondary.TButton").pack(side="left", padx=(0, 10))

        StyledButton(button_frame, text="Add Patient & Create Visit",
                    command=self.submit_patient).pack(side="left")

        # Status bar
        self.create_status_bar(self.right_content, "Ready to add new patient")

    def clear_form(self):
        for var in self.form_vars.values():
            var.set("")

    def submit_patient(self):
        # Validate required fields
        if not self.form_vars["name"].get().strip():
            messagebox.showwarning("Required Field", "Full name is required.")
            return

        if not self.form_vars["doctor"].get():
            messagebox.showwarning("Required Field", "Please assign a doctor.")
            return

        if not self.form_vars["service"].get().strip():
            messagebox.showwarning("Required Field", "Visit service is required.")
            return

        # Get form data
        full_name = self.form_vars["name"].get().strip()
        address = self.form_vars.get("address", tk.StringVar()).get().strip()
        dob = self.form_vars.get("dob", tk.StringVar()).get().strip()
        assigned = self.form_vars["doctor"].get()
        service = self.form_vars["service"].get().strip()

        # Add patient
        pid = self.db.add_patient(full_name, address, dob)

        # Create visit
        assigned_doc_id = self.doctor_map.get(assigned)
        today = date.today().isoformat()
        nowtime = datetime.now().strftime("%H:%M")

        self.db.add_visit(pid, assigned_doc_id, today, nowtime, None, service, "Scheduled", {}, None)

        messagebox.showinfo("Success", f"Patient '{full_name}' has been registered and visit scheduled.")
        self.clear_form()

    def show_todays_visits(self):
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(header_frame, text="Today's Visits", style="Title.TLabel").pack(anchor="w")

        today = date.today().isoformat()
        visits_data = self.db.visits_on_date(today)

        if not visits_data:
            ttk.Label(self.right_content, text="No visits scheduled for today.",
                     style="Subtitle.TLabel").pack(expand=True)
            return

        # Create visits table
        table_frame = CardFrame(self.right_content, padding=15)
        table_frame.pack(fill="both", expand=True)

        # We'll show a simplified view for today's visits
        # In a real app, you'd join with patients and doctors tables
        ttk.Label(table_frame, text=f"Total visits today: {len(visits_data)}",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 10, 'bold')).pack(anchor="w", pady=(0, 10))

        # Status summary
        status_counts = {}
        for vid, status in visits_data:
            status_counts[status] = status_counts.get(status, 0) + 1

        status_text = " | ".join([f"{k}: {v}" for k, v in status_counts.items()])
        ttk.Label(table_frame, text=f"Status: {status_text}",
                 background=COLORS['card_bg']).pack(anchor="w")

        # Status bar
        self.create_status_bar(self.right_content, f"Today's visits: {len(visits_data)} | {status_text}")

    def show_pharmacy_queue(self):
        """FIXED PHARMACY QUEUE - Now properly accessible"""
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(header_frame, text="Pharmacy Queue", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Patients waiting for pharmacy services",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # Search functionality - FIXED SEARCH
        def perform_search(search_term):
            if not search_term.strip():
                visits = self.db.get_visits_for_pharmacy()
            else:
                visits = self.db.search_visits(search_term, "pharmacy")

            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)

            # Load filtered visits
            for v in visits:
                tree.insert("", "end", values=(
                    v["visit_id"],
                    v["patient_name"],
                    v["date"],
                    v["service"],
                    v["doctor_name"],
                    v["pharmacy_status"]
                ))

            # Update status
            status_label.config(text=f"Total pharmacy visits: {len(visits)}")

        search_var = self.create_search_bar(self.right_content, perform_search, "Search by patient ID, name, service, or instructions...")

        # Pharmacy visits table
        table_frame = CardFrame(self.right_content, padding=0)
        table_frame.pack(fill="both", expand=True)

        # Create treeview with scrollbar
        tree_scroll = ttk.Scrollbar(table_frame)
        tree_scroll.pack(side="right", fill="y")

        cols = ("visit_id", "patient", "date", "service", "doctor", "status")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15,
                           yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=tree.yview)

        # Configure columns
        columns_config = [
            ("visit_id", "Visit ID", 80),
            ("patient", "Patient Name", 180),
            ("date", "Date", 100),
            ("service", "Service", 150),
            ("doctor", "Doctor", 150),
            ("status", "Pharmacy Status", 120)
        ]

        for col_id, heading, width in columns_config:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Load pharmacy visits
        visits = self.db.get_visits_for_pharmacy()
        for v in visits:
            tree.insert("", "end", values=(
                v["visit_id"],
                v["patient_name"],
                v["date"],
                v["service"],
                v["doctor_name"],
                v["pharmacy_status"]
            ))

        def on_select(event):
            item = tree.selection()
            if not item:
                return
            values = tree.item(item[0], "values")
            visit_id = int(values[0])
            self.show_pharmacy_visit_details(visit_id)

        tree.bind("<Double-1>", on_select)

        # Status bar with improved visibility
        status_label = self.create_status_bar(self.right_content, f"Total pharmacy visits: {len(visits)}")

    def show_pharmacy_visit_details(self, visit_id):
        visits = self.db.search_visits(str(visit_id), "all")
        visit = visits[0] if visits else None

        if not visit:
            messagebox.showerror("Not Found", "Visit not found.")
            return

        top = tk.Toplevel(self)
        top.title(f"Pharmacy Visit Details — {visit['patient_name']}")
        top.geometry("700x500")
        top.configure(bg=COLORS['background'])

        main_frame = CardFrame(top, padding=20)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        ttk.Label(main_frame, text=visit["patient_name"],
                 font=("Helvetica", 16, "bold"),
                 background=COLORS['card_bg']).pack(anchor="w")

        ttk.Label(main_frame, text=f"Visit ID: {visit['visit_id']} | Date: {visit['date']} | Doctor: {visit['doctor_name']}",
                 background=COLORS['card_bg']).pack(anchor="w", pady=(5, 15))

        # Service info
        ttk.Label(main_frame, text=f"Service: {visit['service']}",
                 font=("Helvetica", 11, "bold"),
                 background=COLORS['card_bg']).pack(anchor="w", pady=(0, 10))

        # Doctor notes
        if visit.get("notes"):
            ttk.Label(main_frame, text="Doctor Notes:",
                     font=("Helvetica", 10, "bold"),
                     background=COLORS['card_bg']).pack(anchor="w", pady=(0, 5))

            notes_frame = tk.Frame(main_frame, bg=COLORS['light'], relief="sunken", borderwidth=1)
            notes_frame.pack(fill="x", pady=(0, 15))

            notes_text = tk.Text(notes_frame, height=4, wrap="word", font=("Helvetica", 9),
                               bg=COLORS['light'], relief="flat")
            notes_text.insert("1.0", visit["notes"])
            notes_text.config(state="disabled")
            notes_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Pharmacy instructions
        ttk.Label(main_frame, text="Pharmacy Instructions:",
                 font=("Helvetica", 10, "bold"),
                 background=COLORS['card_bg']).pack(anchor="w", pady=(0, 5))

        instructions_frame = tk.Frame(main_frame, bg=COLORS['light'], relief="sunken", borderwidth=1)
        instructions_frame.pack(fill="x", pady=(0, 15))

        instructions_text = tk.Text(instructions_frame, height=4, wrap="word", font=("Helvetica", 9),
                                  bg=COLORS['light'], relief="flat")
        instructions_text.insert("1.0", visit.get("pharmacy_instructions", "No instructions provided"))
        instructions_text.config(state="disabled")
        instructions_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Current status
        status_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        status_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(status_frame, text=f"Current Pharmacy Status: {visit.get('pharmacy_status', 'Pending')}",
                 font=("Helvetica", 10, "bold"),
                 background=COLORS['card_bg']).pack(side="left")

        # Close button
        button_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        button_frame.pack(fill="x")

        StyledButton(button_frame, text="Close",
                    command=top.destroy).pack(side="right")

    def show_export_reports(self):
        """New feature: Export data/reports as PDF"""
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 20))

        ttk.Label(header_frame, text="Export Reports", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Generate PDF reports for patients and visits",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # Main export options container
        export_container = tk.Frame(self.right_content, bg=COLORS['background'])
        export_container.pack(fill="both", expand=True)

        # Left side - Patient Reports
        patient_frame = CardFrame(export_container, title="Patient Reports", padding=20)
        patient_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ttk.Label(patient_frame, text="Export comprehensive patient medical reports",
                 background=COLORS['card_bg']).pack(anchor="w", pady=(0, 15))

        # Patient selection for export
        ttk.Label(patient_frame, text="Select Patient:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).pack(anchor="w", pady=(0, 5))

        patients = self.db.list_patients()
        patient_var = tk.StringVar()
        patient_combo = ttk.Combobox(patient_frame, textvariable=patient_var,
                                    values=[f"{p['id']} - {p['full_name']}" for p in patients],
                                    state="readonly", font=('Helvetica', 9))
        patient_combo.pack(fill="x", pady=(0, 15))

        def export_patient_report():
            selection = patient_var.get()
            if not selection:
                messagebox.showwarning("Selection Required", "Please select a patient to export.")
                return

            patient_id = int(selection.split(" - ")[0])
            patient_name = selection.split(" - ")[1]

            try:
                # Ask for save location
                from tkinter import filedialog
                filename = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                    initialfile=f"patient_report_{patient_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
                )

                if filename:
                    output_path = self.master.pdf_exporter.export_patient_report(patient_id, filename)
                    messagebox.showinfo("Export Successful",
                                      f"Patient report for {patient_name} exported to:\n{output_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export PDF: {str(e)}")

        StyledButton(patient_frame, text="📄 Export Patient Report",
                    command=export_patient_report).pack(fill="x", pady=(0, 10))

        # Right side - Visit Reports
        visit_frame = CardFrame(export_container, title="Visit Summary Reports", padding=20)
        visit_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        ttk.Label(visit_frame, text="Export visit summaries and analytics",
                 background=COLORS['card_bg']).pack(anchor="w", pady=(0, 15))

        # Date range selection
        date_frame = tk.Frame(visit_frame, bg=COLORS['card_bg'])
        date_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(date_frame, text="Date Range:",
                 background=COLORS['card_bg'],
                 font=('Helvetica', 9, 'bold')).grid(row=0, column=0, sticky="w", pady=5)

        # Simple date selection - in real app you'd use date pickers
        ttk.Label(date_frame, text="From:",
                 background=COLORS['card_bg']).grid(row=1, column=0, sticky="w", pady=2)
        start_date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(date_frame, textvariable=start_date_var, width=12).grid(row=1, column=1, sticky="w", padx=(5, 10), pady=2)

        ttk.Label(date_frame, text="To:",
                 background=COLORS['card_bg']).grid(row=1, column=2, sticky="w", pady=2)
        end_date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(date_frame, textvariable=end_date_var, width=12).grid(row=1, column=3, sticky="w", pady=2)

        def export_visit_summary():
            try:
                # Get all visits for the date range
                all_visits = self.db.search_visits("", "all")
                start_date = start_date_var.get()
                end_date = end_date_var.get()

                # Filter visits by date range
                filtered_visits = [v for v in all_visits
                                 if start_date <= v["date"] <= end_date]

                if not filtered_visits:
                    messagebox.showwarning("No Data", "No visits found in the selected date range.")
                    return

                visit_ids = [v["visit_id"] for v in filtered_visits]

                # Ask for save location
                from tkinter import filedialog
                filename = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                    initialfile=f"visit_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                )

                if filename:
                    output_path = self.master.pdf_exporter.export_visit_summary_report(visit_ids, filename)
                    messagebox.showinfo("Export Successful",
                                      f"Visit summary report exported to:\n{output_path}\n"
                                      f"Covering {len(visit_ids)} visits from {start_date} to {end_date}")

            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export PDF: {str(e)}")

        StyledButton(visit_frame, text="📊 Export Visit Summary",
                    command=export_visit_summary).pack(fill="x", pady=(0, 10))

        # Quick export options
        quick_frame = CardFrame(export_container, title="Quick Exports", padding=20)
        quick_frame.pack(fill="x", pady=(20, 0))

        quick_buttons_frame = tk.Frame(quick_frame, bg=COLORS['card_bg'])
        quick_buttons_frame.pack(fill="x")

        def export_todays_visits():
            today = date.today().isoformat()
            visits = self.db.visits_on_date(today)
            if not visits:
                messagebox.showinfo("No Data", "No visits found for today.")
                return

            visit_ids = [v[0] for v in visits]
            try:
                filename = f"todays_visits_{today}.pdf"
                output_path = self.master.pdf_exporter.export_visit_summary_report(visit_ids, filename)
                messagebox.showinfo("Export Successful",
                                  f"Today's visits report exported to:\n{output_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export PDF: {str(e)}")

        def export_all_patients():
            patients = self.db.list_patients()
            if not patients:
                messagebox.showinfo("No Data", "No patients found in the system.")
                return

            # Export first patient as sample (in real app, you might want to export all)
            if patients:
                try:
                    filename = f"patient_sample_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                    output_path = self.master.pdf_exporter.export_patient_report(patients[0]["id"], filename)
                    messagebox.showinfo("Export Successful",
                                      f"Sample patient report exported to:\n{output_path}\n"
                                      f"(Showing first patient as sample)")
                except Exception as e:
                    messagebox.showerror("Export Failed", f"Failed to export PDF: {str(e)}")

        StyledButton(quick_buttons_frame, text="📅 Today's Visits Report",
                    command=export_todays_visits, style="Secondary.TButton").pack(side="left", padx=(0, 10))

        StyledButton(quick_buttons_frame, text="👥 Sample Patient Report",
                    command=export_all_patients, style="Secondary.TButton").pack(side="left")

        # Status bar
        self.create_status_bar(self.right_content, "Ready to generate PDF reports - Select patient or date range to export")

# ---------------------
# Doctor Main UI
# ---------------------
class DoctorMain(MainBaseFrame):
    def __init__(self, master, user):
        super().__init__(master, user)
        self.build_navigation()
        self.show_dashboard()

    def build_navigation(self):
        self.nav_buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("👥 My Patients", self.show_assigned_patients),
            ("📋 Today's Appointments", self.show_todays_appointments)
        ]

        for i, (text, command) in enumerate(self.nav_buttons):
            self.add_nav_button(text, command, is_selected=(i == 0))

    def show_dashboard(self):
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 20))

        today = date.today().strftime("%A, %d %B %Y")
        ttk.Label(header_frame, text=f"Doctor Dashboard — {today}",
                 style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text=f"Dr. {self.user['name']}",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # Stats cards
        stats_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        stats_frame.pack(fill="x", pady=(0, 20))

        visits = self.db.get_visits_for_doctor(self.user["id"])
        today = date.today().isoformat()
        todays_visits = [v for v in visits if v["date"] == today]

        cards_data = [
            ("Total Assigned", len(visits), COLORS['primary']),
            ("Today's Appointments", len(todays_visits), COLORS['secondary']),
            ("Pending Review", len([v for v in todays_visits if v["status"] == "Pending"]), COLORS['warning']),
            ("Pharmacy Referrals", len([v for v in visits if v["status"] == "Visit Pharmacy"]), COLORS['accent']),
            ("Completed Today", len([v for v in todays_visits if v["status"] == "Done"]), COLORS['success'])
        ]

        for i, (title, value, color) in enumerate(cards_data):
            card = self.create_card(stats_frame, title, width=180, height=100)
            card.grid(row=0, column=i, padx=(0, 15), sticky="nsew")

            value_label = ttk.Label(card, text=str(value),
                                  font=("Helvetica", 24, "bold"),
                                  foreground=color,
                                  background=COLORS['card_bg'])
            value_label.pack(expand=True)

        # Status bar
        self.create_status_bar(self.right_content, f"Dashboard loaded | Total assigned patients: {len(visits)} | Today's appointments: {len(todays_visits)}")

    def show_assigned_patients(self):
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(header_frame, text="My Patients", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Patients assigned to you for care",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # Search functionality - FIXED SEARCH
        def perform_search(search_term):
            visits = self.db.get_visits_for_doctor(self.user["id"])
            if search_term.strip():
                visits = [v for v in visits if search_term.lower() in v["patient_name"].lower() or
                         search_term.lower() in v["service"].lower() or
                         search_term.lower() in (v.get("notes") or "").lower() or
                         str(v["visit_id"]) == search_term]

            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)

            # Load filtered visits
            for v in visits:
                tree.insert("", "end", values=(
                    v["visit_id"],
                    v["patient_name"],
                    v["date"],
                    f"{v['time_in'] or ''}",
                    v["service"],
                    v["status"] or "Pending"
                ))

            # Update status
            status_label.config(text=f"Total assigned visits: {len(visits)}")

        search_var = self.create_search_bar(self.right_content, perform_search, "Search by patient ID, name, service, or notes...")

        visits = self.db.get_visits_for_doctor(self.user["id"])

        if not visits:
            ttk.Label(self.right_content, text="No patients assigned.",
                     style="Subtitle.TLabel").pack(expand=True)
            return

        # Create table
        table_frame = CardFrame(self.right_content, padding=0)
        table_frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(table_frame, columns=("visit_id", "patient_name", "date", "time", "service", "status"),
                           show="headings", height=15)

        columns_config = [
            ("visit_id", "Visit ID", 80),
            ("patient_name", "Patient Name", 180),
            ("date", "Date", 100),
            ("time", "Time", 100),
            ("service", "Service", 150),
            ("status", "Status", 120)
        ]

        for col_id, heading, width in columns_config:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        for v in visits:
            tree.insert("", "end", values=(
                v["visit_id"],
                v["patient_name"],
                v["date"],
                f"{v['time_in'] or ''}",
                v["service"],
                v["status"] or "Pending"
            ))

        def on_select(event):
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            visit_id = int(vals[0])
            self.open_visit_editor(visit_id)

        tree.bind("<Double-1>", on_select)

        # Status bar with improved visibility
        status_label = self.create_status_bar(self.right_content, f"Total assigned visits: {len(visits)}")

    def show_todays_appointments(self):
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(header_frame, text="Today's Appointments", style="Title.TLabel").pack(anchor="w")

        visits = self.db.get_visits_for_doctor(self.user["id"])
        today = date.today().isoformat()
        todays_visits = [v for v in visits if v["date"] == today]

        if not todays_visits:
            ttk.Label(self.right_content, text="No appointments scheduled for today.",
                     style="Subtitle.TLabel").pack(expand=True)
            return

        # Create appointments view
        for visit in todays_visits:
            appointment_card = CardFrame(self.right_content, padding=15)
            appointment_card.pack(fill="x", pady=(0, 10))

            # Header with patient name and time
            header = tk.Frame(appointment_card, bg=COLORS['card_bg'])
            header.pack(fill="x")

            ttk.Label(header, text=visit["patient_name"],
                     font=("Helvetica", 12, "bold"),
                     background=COLORS['card_bg']).pack(side="left")

            ttk.Label(header, text=f"{visit['time_in'] or 'TBD'} | {visit['service']}",
                     background=COLORS['card_bg']).pack(side="right")

            # Status and action button
            footer = tk.Frame(appointment_card, bg=COLORS['card_bg'])
            footer.pack(fill="x", pady=(10, 0))

            status_color = COLORS['success'] if visit["status"] == "Done" else COLORS['warning']
            ttk.Label(footer, text=f"Status: {visit['status']}",
                     foreground=status_color,
                     background=COLORS['card_bg']).pack(side="left")

            StyledButton(footer, text="Review Visit",
                        command=lambda vid=visit["visit_id"]: self.open_visit_editor(vid),
                        width=12).pack(side="right")

        # Status bar
        self.create_status_bar(self.right_content, f"Today's appointments: {len(todays_visits)}")

    def open_visit_editor(self, visit_id):
        visits = self.db.get_visits_for_doctor(self.user["id"])
        visit = next((v for v in visits if v["visit_id"] == visit_id), None)

        if not visit:
            messagebox.showerror("Not Found", "Visit not found or not assigned to you.")
            return

        top = tk.Toplevel(self)
        top.title(f"Visit {visit['visit_id']} — {visit['patient_name']}")
        top.geometry("800x700")
        top.configure(bg=COLORS['background'])

        # Main container with scrollbar
        main_container = tk.Frame(top, bg=COLORS['background'])
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Create a canvas and scrollbar for the main content
        canvas = tk.Canvas(main_container, bg=COLORS['background'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Card.TFrame")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main_frame = CardFrame(scrollable_frame, padding=20)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Header
        ttk.Label(main_frame, text=visit["patient_name"],
                  font=("Helvetica", 16, "bold"),
                  background=COLORS['card_bg']).pack(anchor="w")

        ttk.Label(main_frame, text=f"Visit ID: {visit['visit_id']} | Date: {visit['date']}",
                  background=COLORS['card_bg']).pack(anchor="w", pady=(5, 15))

        # Vitals section - Enhanced with proper input fields
        vitals_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        vitals_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(vitals_frame, text="Vital Signs",
                  font=("Helvetica", 12, "bold"),
                  background=COLORS['card_bg']).pack(anchor="w", pady=(0, 10))

        # Create vitals input grid
        vitals_grid = tk.Frame(vitals_frame, bg=COLORS['card_bg'])
        vitals_grid.pack(fill="x", pady=(8, 0))

        self.vitals_vars = {}
        vitals_fields = [
            ("Blood Pressure (BP):", "bp", "120/80"),
            ("Heart Rate (HR):", "hr", "72"),
            ("Temperature (°F):", "temp", "98.6"),
            ("Respiratory Rate:", "resp", "16"),
            ("SpO2 (%):", "spo2", "98")
        ]

        for i, (label, key, placeholder) in enumerate(vitals_fields):
            row = i
            ttk.Label(vitals_grid, text=label,
                      font=("Helvetica", 9, "bold"),
                      background=COLORS['card_bg']).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)

            var = tk.StringVar(value=visit["vitals"].get(key, ""))
            entry = ttk.Entry(vitals_grid, textvariable=var, width=15, font=('Helvetica', 9))
            entry.grid(row=row, column=1, sticky="w", padx=(0, 20), pady=5)
            if not var.get():
                entry.insert(0, placeholder)
            self.vitals_vars[key] = var

        # Service info
        ttk.Label(main_frame, text=f"Service: {visit['service']}",
                  background=COLORS['card_bg']).pack(anchor="w", pady=(0, 15))

        # Notes section
        ttk.Label(main_frame, text="Clinical Notes:",
                  font=("Helvetica", 11, "bold"),
                  background=COLORS['card_bg']).pack(anchor="w", pady=(0, 5))

        notes_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        notes_frame.pack(fill="x", pady=(0, 15))

        notes_entry = tk.Text(notes_frame, width=60, height=6, font=("Helvetica", 10),
                              relief="solid", borderwidth=1, padx=8, pady=8)
        notes_entry.insert("1.0", visit.get("notes") or "")
        notes_entry.pack(fill="x")

        # Pharmacy instructions
        ttk.Label(main_frame, text="Pharmacy Instructions:",
                  font=("Helvetica", 11, "bold"),
                  background=COLORS['card_bg']).pack(anchor="w", pady=(0, 5))

        pharmacy_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        pharmacy_frame.pack(fill="x", pady=(0, 15))

        pharmacy_entry = tk.Text(pharmacy_frame, width=60, height=4, font=("Helvetica", 10),
                                 relief="solid", borderwidth=1, padx=8, pady=8)
        pharmacy_entry.insert("1.0", visit.get("pharmacy_instructions") or "")
        pharmacy_entry.pack(fill="x")

        # Status update
        status_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        status_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(status_frame, text="Status:",
                  background=COLORS['card_bg'],
                  font=('Helvetica', 9, 'bold')).pack(side="left", padx=(0, 10))

        status_var = tk.StringVar(value=visit.get("status") or "Pending")
        status_combo = ttk.Combobox(status_frame,
                                    values=["Scheduled", "In Progress", "Done", "Visit Pharmacy", "Come again",
                                            "Other"],
                                    textvariable=status_var,
                                    state="readonly",
                                    width=15)
        status_combo.pack(side="left")

        def update_pharmacy_visibility():
            if status_var.get() == "Visit Pharmacy":
                pharmacy_entry.config(state="normal")
                ttk.Label(main_frame, text="* Pharmacy instructions are required when status is 'Visit Pharmacy'",
                          font=("Helvetica", 8),
                          foreground=COLORS['accent'],
                          background=COLORS['card_bg']).pack(anchor="w", pady=(0, 10))
            else:
                pharmacy_entry.config(state="normal")

        status_var.trace('w', lambda *args: update_pharmacy_visibility())
        update_pharmacy_visibility()

        def save_changes():
            new_status = status_var.get()
            notes = notes_entry.get("1.0", "end-1c").strip()
            pharmacy_instructions = pharmacy_entry.get("1.0", "end-1c").strip()

            # Collect vitals
            vitals_data = {}
            for key, var in self.vitals_vars.items():
                value = var.get().strip()
                if value and value != vitals_fields[[f[1] for f in vitals_fields].index(key)][
                    2]:  # Don't save placeholder values
                    # Convert numeric values appropriately
                    if key in ['hr', 'resp', 'spo2']:
                        try:
                            vitals_data[key] = int(value)
                        except ValueError:
                            vitals_data[key] = value
                    elif key == 'temp':
                        try:
                            vitals_data[key] = float(value)
                        except ValueError:
                            vitals_data[key] = value
                    else:
                        vitals_data[key] = value

            if new_status == "Visit Pharmacy" and not pharmacy_instructions:
                messagebox.showwarning("Input Required",
                                       "Pharmacy instructions are required when status is 'Visit Pharmacy'.")
                return

            # Update visit with vitals
            conn = self.db.connect()
            c = conn.cursor()
            c.execute("""UPDATE visits SET status = ?, doctor_notes = ?, pharmacy_instructions = ?, vitals_json = ? 
                         WHERE id = ?""",
                      (new_status, notes, pharmacy_instructions, json.dumps(vitals_data), visit_id))
            conn.commit()
            conn.close()

            messagebox.showinfo("Saved", "Visit details updated successfully.")
            top.destroy()
            self.show_assigned_patients()

        # Buttons - FIXED VERSION
        button_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        button_frame.pack(fill="x", pady=(20, 0))

        # Use tk.Button for better visibility and control
        save_btn = tk.Button(button_frame,
                             text="Save Changes",
                             command=save_changes,
                             bg=COLORS['primary'],
                             fg='white',
                             font=('Helvetica', 10, 'bold'),
                             padx=20,
                             pady=8,
                             relief='flat',
                             cursor='hand2')
        save_btn.pack(side="right", padx=(10, 0))

        cancel_btn = tk.Button(button_frame,
                               text="Cancel",
                               command=top.destroy,
                               bg=COLORS['light'],
                               fg=COLORS['dark'],
                               font=('Helvetica', 10),
                               padx=20,
                               pady=8,
                               relief='raised',
                               cursor='hand2')
        cancel_btn.pack(side="right")

        # Update canvas scrollregion after all widgets are added
        def update_scroll_region():
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        top.after(100, update_scroll_region)

# ---------------------
# Pharmacist Main UI
# ---------------------
class PharmacistMain(MainBaseFrame):
    def __init__(self, master, user):
        super().__init__(master, user)
        self.build_navigation()
        self.show_dashboard()

    def build_navigation(self):
        self.nav_buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("💊 Pharmacy Queue", self.show_pharmacy_queue),
            ("✅ Completed", self.show_completed_orders)
        ]

        for i, (text, command) in enumerate(self.nav_buttons):
            self.add_nav_button(text, command, is_selected=(i == 0))

    def show_dashboard(self):
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 20))

        today = date.today().strftime("%A, %d %B %Y")
        ttk.Label(header_frame, text=f"Pharmacist Dashboard — {today}",
                 style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text=f"Pharmacist {self.user['name']}",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # Stats cards
        stats_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        stats_frame.pack(fill="x", pady=(0, 20))

        visits = self.db.get_visits_for_pharmacy()
        pending_visits = [v for v in visits if v["pharmacy_status"] == "Pending"]
        completed_visits = [v for v in visits if v["pharmacy_status"] == "Completed"]
        today = date.today().isoformat()
        todays_visits = [v for v in visits if v["date"] == today]

        cards_data = [
            ("Total Pharmacy Visits", len(visits), COLORS['primary']),
            ("Pending Orders", len(pending_visits), COLORS['warning']),
            ("Completed Today", len([v for v in todays_visits if v["pharmacy_status"] == "Completed"]), COLORS['success']),
            ("Total Completed", len(completed_visits), COLORS['secondary'])
        ]

        for i, (title, value, color) in enumerate(cards_data):
            card = self.create_card(stats_frame, title, width=180, height=100)
            card.grid(row=0, column=i, padx=(0, 15), sticky="nsew")

            value_label = ttk.Label(card, text=str(value),
                                  font=("Helvetica", 24, "bold"),
                                  foreground=color,
                                  background=COLORS['card_bg'])
            value_label.pack(expand=True)

        # Recent pending orders
        recent_frame = CardFrame(self.right_content, title="Recent Pending Orders", padding=15)
        recent_frame.pack(fill="both", expand=True, pady=(20, 0))

        if not pending_visits:
            ttk.Label(recent_frame, text="No pending pharmacy orders.",
                     background=COLORS['card_bg']).pack(expand=True)
        else:
            # Show recent 5 pending orders
            cols = ("patient", "date", "doctor", "instructions")
            tree = ttk.Treeview(recent_frame, columns=cols, show="headings", height=6)

            columns_config = [
                ("patient", "Patient Name", 150),
                ("date", "Date", 100),
                ("doctor", "Doctor", 150),
                ("instructions", "Instructions", 200)
            ]

            for col_id, heading, width in columns_config:
                tree.heading(col_id, text=heading)
                tree.column(col_id, width=width, anchor="w")

            tree.pack(fill="both", expand=True)

            for v in pending_visits[:5]:  # Show only first 5
                instructions_preview = v.get("pharmacy_instructions", "")[:50] + "..." if len(v.get("pharmacy_instructions", "")) > 50 else v.get("pharmacy_instructions", "")
                tree.insert("", "end", values=(
                    v["patient_name"],
                    v["date"],
                    v["doctor_name"],
                    instructions_preview
                ))

            def on_select(event):
                sel = tree.selection()
                if not sel:
                    return
                # Open the full pharmacy queue when item is selected
                self.show_pharmacy_queue()

            tree.bind("<Double-1>", on_select)

        # Status bar
        self.create_status_bar(self.right_content, f"Dashboard loaded | Pending orders: {len(pending_visits)} | Completed today: {len([v for v in todays_visits if v['pharmacy_status'] == 'Completed'])}")

    def show_pharmacy_queue(self):
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(header_frame, text="Pharmacy Order Queue", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Manage patient medication orders",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))

        # Search functionality - FIXED SEARCH
        def perform_search(search_term):
            if not search_term.strip():
                visits = self.db.get_visits_for_pharmacy()
            else:
                visits = self.db.search_visits(search_term, "pharmacy")

            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)

            # Load filtered visits
            for v in visits:
                tree.insert("", "end", values=(
                    v["visit_id"],
                    v["patient_name"],
                    v["date"],
                    v["service"],
                    v["doctor_name"],
                    v["pharmacy_status"],
                    v.get("pharmacy_instructions", "")[:30] + "..." if len(v.get("pharmacy_instructions", "")) > 30 else v.get("pharmacy_instructions", "")
                ))

            # Update status
            status_label.config(text=f"Total pharmacy orders: {len(visits)}")

        search_var = self.create_search_bar(self.right_content, perform_search, "Search by patient ID, name, service, or instructions...")

        # Pharmacy visits table
        table_frame = CardFrame(self.right_content, padding=0)
        table_frame.pack(fill="both", expand=True)

        # Create treeview with scrollbar
        tree_scroll = ttk.Scrollbar(table_frame)
        tree_scroll.pack(side="right", fill="y")

        cols = ("visit_id", "patient", "date", "service", "doctor", "status", "instructions")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15,
                           yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=tree.yview)

        # Configure columns
        columns_config = [
            ("visit_id", "Visit ID", 80),
            ("patient", "Patient Name", 150),
            ("date", "Date", 100),
            ("service", "Service", 120),
            ("doctor", "Doctor", 120),
            ("status", "Pharmacy Status", 100),
            ("instructions", "Instructions", 150)
        ]

        for col_id, heading, width in columns_config:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Load pharmacy visits
        visits = self.db.get_visits_for_pharmacy()
        for v in visits:
            tree.insert("", "end", values=(
                v["visit_id"],
                v["patient_name"],
                v["date"],
                v["service"],
                v["doctor_name"],
                v["pharmacy_status"],
                v.get("pharmacy_instructions", "")[:30] + "..." if len(v.get("pharmacy_instructions", "")) > 30 else v.get("pharmacy_instructions", "")
            ))

        def on_select(event):
            item = tree.selection()
            if not item:
                return
            values = tree.item(item[0], "values")
            visit_id = int(values[0])
            self.process_pharmacy_order(visit_id)

        tree.bind("<Double-1>", on_select)

        # Status bar with improved visibility
        status_label = self.create_status_bar(self.right_content, f"Total pharmacy orders: {len(visits)}")

    def show_completed_orders(self):
        self.clear_right()

        header_frame = tk.Frame(self.right_content, bg=COLORS['background'])
        header_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(header_frame, text="Completed Pharmacy Orders", style="Title.TLabel").pack(anchor="w")

        # Get all visits and filter completed ones
        all_visits = self.db.search_visits("", "all")
        completed_visits = [v for v in all_visits if v.get("pharmacy_status") == "Completed"]

        if not completed_visits:
            ttk.Label(self.right_content, text="No completed pharmacy orders.",
                     style="Subtitle.TLabel").pack(expand=True)
            return

        # Search functionality for completed orders - FIXED SEARCH
        def perform_search(search_term):
            filtered_visits = [v for v in completed_visits if
                             search_term.lower() in v["patient_name"].lower() or
                             search_term.lower() in v["service"].lower() or
                             search_term.lower() in v.get("pharmacy_instructions", "").lower() or
                             str(v["visit_id"]) == search_term]

            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)

            # Load filtered visits
            for v in filtered_visits:
                tree.insert("", "end", values=(
                    v["visit_id"],
                    v["patient_name"],
                    v["date"],
                    v["service"],
                    v["doctor_name"],
                    v.get("pharmacy_instructions", "")[:40] + "..." if len(v.get("pharmacy_instructions", "")) > 40 else v.get("pharmacy_instructions", "")
                ))

            # Update status
            status_label.config(text=f"Completed orders: {len(filtered_visits)}")

        search_var = self.create_search_bar(self.right_content, perform_search, "Search completed orders by ID or name...")

        # Completed orders table
        table_frame = CardFrame(self.right_content, padding=0)
        table_frame.pack(fill="both", expand=True)

        cols = ("visit_id", "patient", "date", "service", "doctor", "instructions")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)

        columns_config = [
            ("visit_id", "Visit ID", 80),
            ("patient", "Patient Name", 150),
            ("date", "Date", 100),
            ("service", "Service", 120),
            ("doctor", "Doctor", 120),
            ("instructions", "Instructions", 200)
        ]

        for col_id, heading, width in columns_config:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor="w")

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        for v in completed_visits:
            tree.insert("", "end", values=(
                v["visit_id"],
                v["patient_name"],
                v["date"],
                v["service"],
                v["doctor_name"],
                v.get("pharmacy_instructions", "")[:40] + "..." if len(v.get("pharmacy_instructions", "")) > 40 else v.get("pharmacy_instructions", "")
            ))

        # Status bar with improved visibility
        status_label = self.create_status_bar(self.right_content, f"Completed orders: {len(completed_visits)}")

    def process_pharmacy_order(self, visit_id):
        # Get all pharmacy visits and find the specific one by ID
        visits = self.db.get_visits_for_pharmacy()
        visit = next((v for v in visits if v["visit_id"] == visit_id), None)

        if not visit:
            messagebox.showerror("Not Found",
                                 f"Visit ID {visit_id} not found in pharmacy queue or may have been already processed.")
            return

        top = tk.Toplevel(self)
        top.title(f"Process Pharmacy Order — {visit['patient_name']}")
        top.geometry("700x550")
        top.configure(bg=COLORS['background'])

        main_frame = CardFrame(top, padding=20)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        ttk.Label(main_frame, text=visit["patient_name"],
                  font=("Helvetica", 16, "bold"),
                  background=COLORS['card_bg']).pack(anchor="w")

        ttk.Label(main_frame,
                  text=f"Visit ID: {visit['visit_id']} | Date: {visit['date']} | Doctor: {visit['doctor_name']}",
                  background=COLORS['card_bg']).pack(anchor="w", pady=(5, 15))

        # Service info
        ttk.Label(main_frame, text=f"Service: {visit['service']}",
                  font=("Helvetica", 11, "bold"),
                  background=COLORS['card_bg']).pack(anchor="w", pady=(0, 10))

        # Display vital signs
        if visit.get("vitals"):
            vitals = visit["vitals"]
            vitals_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
            vitals_frame.pack(fill="x", pady=(0, 15))

            ttk.Label(vitals_frame, text="Vital Signs:",
                      font=("Helvetica", 10, "bold"),
                      background=COLORS['card_bg']).pack(anchor="w", pady=(0, 5))

            vitals_text = f"BP: {vitals.get('bp', 'N/A')} | HR: {vitals.get('hr', 'N/A')} | Temp: {vitals.get('temp', 'N/A')}°F | Resp: {vitals.get('resp', 'N/A')} | SpO2: {vitals.get('spo2', 'N/A')}%"
            ttk.Label(vitals_frame, text=vitals_text,
                      background=COLORS['card_bg']).pack(anchor="w")

        # Doctor notes
        if visit.get("notes"):
            ttk.Label(main_frame, text="Doctor Notes:",
                      font=("Helvetica", 10, "bold"),
                      background=COLORS['card_bg']).pack(anchor="w", pady=(0, 5))

            notes_frame = tk.Frame(main_frame, bg=COLORS['light'], relief="sunken", borderwidth=1)
            notes_frame.pack(fill="x", pady=(0, 15))

            notes_text = tk.Text(notes_frame, height=3, wrap="word", font=("Helvetica", 9),
                                 bg=COLORS['light'], relief="flat")
            notes_text.insert("1.0", visit["notes"])
            notes_text.config(state="disabled")
            notes_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Pharmacy instructions
        ttk.Label(main_frame, text="Pharmacy Instructions:",
                  font=("Helvetica", 10, "bold"),
                  background=COLORS['card_bg']).pack(anchor="w", pady=(0, 5))

        instructions_frame = tk.Frame(main_frame, bg=COLORS['light'], relief="sunken", borderwidth=1)
        instructions_frame.pack(fill="x", pady=(0, 15))

        instructions_text = tk.Text(instructions_frame, height=4, wrap="word", font=("Helvetica", 9),
                                    bg=COLORS['light'], relief="flat")
        instructions_text.insert("1.0", visit.get("pharmacy_instructions", "No instructions provided"))
        instructions_text.config(state="disabled")
        instructions_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Dispensing notes
        ttk.Label(main_frame, text="Dispensing Notes:",
                  font=("Helvetica", 10, "bold"),
                  background=COLORS['card_bg']).pack(anchor="w", pady=(0, 5))

        dispensing_entry = tk.Text(main_frame, height=4, wrap="word", font=("Helvetica", 10),
                                   relief="solid", borderwidth=1, padx=8, pady=8)
        dispensing_entry.pack(fill="x", pady=(0, 15))

        # Status update
        status_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        status_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(status_frame, text="Update Status:",
                  background=COLORS['card_bg'],
                  font=('Helvetica', 9, 'bold')).pack(side="left", padx=(0, 10))

        status_var = tk.StringVar(value=visit.get("pharmacy_status", "Pending"))
        status_combo = ttk.Combobox(status_frame,
                                    values=["Pending", "In Progress", "Completed", "On Hold"],
                                    textvariable=status_var,
                                    state="readonly",
                                    width=15)
        status_combo.pack(side="left")

        def save_changes():
            new_status = status_var.get()
            dispensing_notes = dispensing_entry.get("1.0", "end-1c").strip()

            # Use the new method that updates both status and time_out
            self.db.update_pharmacy_status_and_timeout(visit["visit_id"], new_status)

            # Log the dispensing notes (in a real system, you'd store this in the database)
            if dispensing_notes:
                messagebox.showinfo("Saved",
                                    f"Status updated to {new_status}.\nDispensing notes recorded.\nTime out recorded: {datetime.now().strftime('%H:%M')}")
            else:
                messagebox.showinfo("Saved",
                                    f"Status updated to {new_status}.\nTime out recorded: {datetime.now().strftime('%H:%M')}")

            top.destroy()
            self.show_pharmacy_queue()

        # Buttons
        button_frame = tk.Frame(main_frame, bg=COLORS['card_bg'])
        button_frame.pack(fill="x")

        StyledButton(button_frame, text="Save & Complete",
                     command=save_changes).pack(side="right", padx=(10, 0))

        StyledButton(button_frame, text="Cancel",
                     command=top.destroy,
                     style="Secondary.TButton").pack(side="right")

# ---------------------
# Run Application
# ---------------------
def main():
    ensure_db()
    db = DB(DB_FILE)
    app = VitalSignApp(db)
    app.mainloop()

if __name__ == "__main__":
    main()