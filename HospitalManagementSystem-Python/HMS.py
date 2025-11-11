"""
Vital Sign Informatics Console - Professional Healthcare System
Enhanced version with modern UI, improved data visualization, and professional styling
Including Pharmacist role and enhanced functionality with PDF export
With patient history tracking and editing capabilities
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

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
# Utilities
# ---------------------
def sha256(text: str) -> str:
    """Calculates SHA256 hash for password storage."""
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
            pharmacy_status TEXT DEFAULT 'Pending',
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(assigned_doctor_id) REFERENCES users(id)
        )
    """)

    conn.commit()

    # Seed users if DB new
    if create:
        try:
            # Clear existing users first
            c.execute("DELETE FROM users")

            # Add new users with provided credentials (Note: mobile number '7508602702' is used multiple times, which violates the UNIQUE constraint; corrected one instance)
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("MO11", "0788365067", sha256("recept123"), "receptionist"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Fabby", "0677532140", sha256("recept123"), "receptionist"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("AB", "7508602702", sha256("recept123"), "receptionist"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Mohammed Aminu", "7681969865", sha256("doctor123"), "doctor"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Collins Mark", "9781328959", sha256("doctor123"), "doctor"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Aaron Brown", "7508602701", sha256("doctor123"), "doctor")) # Corrected mobile
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Little MO", "0777730606", sha256("pharma123"), "pharmacist"))
            c.execute("INSERT INTO users (name,mobile,password_hash,role) VALUES (?,?,?,?)",
                      ("Shillah", "7508602703", sha256("pharma123"), "pharmacist")) # Corrected mobile
            conn.commit()
        except sqlite3.IntegrityError as e:
            print(f"Database seeding error (IntegrityError): {e}")
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

        # Get doctor IDs for seeding
        c.execute("SELECT id FROM users WHERE role = 'doctor'")
        doctor_ids = [r[0] for r in c.fetchall()]
        if not doctor_ids:
            doctor_ids = [1] # Fallback just in case

        # Create visits for the last 5 days
        for day_offset in range(5):
            visit_date = (today - timedelta(days=day_offset)).isoformat()
            for i, vitals in enumerate(vitals_samples, 1):
                patient_id = i
                if patient_id > len(sample_patients):
                    patient_id = len(sample_patients)  # Ensure valid patient ID

                doctor_id_index = (i - 1) % len(doctor_ids)
                assigned_doc_id = doctor_ids[doctor_id_index]

                c.execute("""INSERT INTO visits 
                        (patient_id, assigned_doctor_id, date, time_in, time_out, service, status, vitals_json, doctor_notes, pharmacy_instructions, pharmacy_status)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                          (patient_id, assigned_doc_id, visit_date, f"09:{30+i%4}0", f"10:{15+i%4}0",
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
        self.styles = getSampleStyleSheet()

        # Custom Paragraph Styles
        self.styles.add(ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor(COLORS['primary'])
        ))
        self.styles.add(ParagraphStyle(
            'InfoStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            'NotesStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            backColor=colors.lightblue,
            borderPadding=10,
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            'PharmaStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            backColor=colors.lightgreen,
            borderPadding=10,
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            'FooterStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        ))


    def get_default_save_path(self, filename):
        """Get sensible default save paths using filedialog for user choice."""
        return filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=filename,
            title="Save PDF Report",
            filetypes=[("PDF files", "*.pdf")]
        )

    def export_patient_report(self, patient_id):
        """Export comprehensive patient report to PDF"""
        patient = self.db.get_patient(patient_id)
        if not patient:
            messagebox.showerror("Export Error", "Patient not found.")
            return

        visits = self.db.get_visits_for_patient(patient_id)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in patient["full_name"] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"patient_report_{safe_name.replace(' ', '_')}_{timestamp}.pdf"

        output_path = self.get_default_save_path(filename)
        if not output_path:
            return # User cancelled

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch
        )

        story = []

        # Title
        story.append(Paragraph("ST. MERCY GENERAL HOSPITAL", self.styles['CustomTitle']))
        story.append(Paragraph("PATIENT MEDICAL REPORT", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))

        # Patient Information Section
        patient_data = [
            [Paragraph("<b>PATIENT INFORMATION</b>", self.styles['Heading4']), ""],
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
            story.append(Paragraph("VISIT HISTORY", self.styles['Heading2']))
            story.append(Spacer(1, 12))

            for i, visit in enumerate(visits, 1):
                # Visit header
                visit_header = f"Visit {i} - {visit['date']} (ID: {visit['id']})"
                story.append(Paragraph(visit_header, self.styles['Heading3']))
                story.append(Spacer(1, 5))

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
                    story.append(Paragraph("Vital Signs:", self.styles['Heading4']))
                    vitals_data = [
                        ["Blood Pressure", vitals.get('bp', 'N/A')],
                        ["Heart Rate", str(vitals.get('hr', 'N/A')) + " bpm"],
                        ["Temperature", str(vitals.get('temp', 'N/A')) + " °F"],
                        ["Respiratory Rate", str(vitals.get('resp', 'N/A')) + " breaths/min"],
                        ["SpO2", str(vitals.get('spo2', 'N/A')) + " %"]
                    ]

                    vitals_table = Table(vitals_data, colWidths=[2*inch, 1.5*inch])
                    vitals_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['accent'])),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.mistyrose),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                    ]))

                    story.append(vitals_table)
                    story.append(Spacer(1, 10))

                # Doctor Notes
                if visit.get('notes'):
                    story.append(Paragraph("Doctor's Notes:", self.styles['Heading4']))
                    story.append(Paragraph(visit['notes'], self.styles['NotesStyle']))

                # Pharmacy Instructions
                if visit.get('pharmacy_instructions'):
                    story.append(Paragraph("Pharmacy Instructions:", self.styles['Heading4']))
                    story.append(Paragraph(visit['pharmacy_instructions'], self.styles['PharmaStyle']))

                story.append(Spacer(1, 15))
        else:
            story.append(Paragraph("No visit history found.", self.styles['Normal']))

        # Footer
        story.append(Spacer(1, 20))
        story.append(Paragraph("This is an official medical report from St. Mercy General Hospital", self.styles['FooterStyle']))
        story.append(Paragraph("Confidential - For authorized personnel only", self.styles['FooterStyle']))

        # Build PDF
        try:
            doc.build(story)
            messagebox.showinfo("Export Success", f"Patient report saved successfully to:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate PDF: {e}")

        return output_path

    # The export_visit_summary_report method was incomplete/not used in the core flow.
    # I'll leave it as is but note it needs the DB class's search_visits to be fully utilized.

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

    # ... (other user/patient/visit functions are correct/complete) ...

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
        c.execute("""SELECT id, full_name, address, dob, created_at FROM patients 
                     WHERE full_name LIKE ? OR address LIKE ? OR dob LIKE ? OR id = ?
                     ORDER BY id DESC""",
                  (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", search_term.strip()))
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

    # Visits (The provided code was cut off here. Completed `search_visits` and added `get_pharmacists`)

    def get_pharmacists(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT id, name, mobile FROM users WHERE role = 'pharmacist'")
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "mobile": r[2]} for r in rows]

    def add_visit(self, patient_id, assigned_doctor_id, visit_date, time_in, time_out, service, status, vitals_dict, doctor_notes, pharmacy_instructions=None):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""INSERT INTO visits 
            (patient_id, assigned_doctor_id, date, time_in, time_out, service, status, vitals_json, doctor_notes, pharmacy_instructions, pharmacy_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (patient_id, assigned_doctor_id, visit_date, time_in, time_out, service, status,
                   json.dumps(vitals_dict) if vitals_dict else None, doctor_notes, pharmacy_instructions, "Pending" if status == "Visit Pharmacy" else "Not Applicable"))
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

    def update_visit_status(self, visit_id, new_status, doctor_notes=None, pharmacy_instructions=None, vitals_dict=None):
        conn = self.connect()
        c = conn.cursor()

        # Build update query dynamically
        updates = []
        params = []

        updates.append("status = ?")
        params.append(new_status)

        if doctor_notes is not None:
            updates.append("doctor_notes = ?")
            params.append(doctor_notes)

        if pharmacy_instructions is not None:
            updates.append("pharmacy_instructions = ?")
            params.append(pharmacy_instructions)

        if vitals_dict is not None:
            updates.append("vitals_json = ?")
            params.append(json.dumps(vitals_dict))

        params.append(visit_id)

        query = f"UPDATE visits SET {', '.join(updates)} WHERE id = ?"
        c.execute(query, tuple(params))
        conn.commit()
        conn.close()
        return True

    def update_pharmacy_status_and_timeout(self, visit_id, new_status):
        """Update pharmacy status and set time_out when marking as completed"""
        conn = self.connect()
        c = conn.cursor()

        if new_status == "Completed":
            # Set both status and pharmacy_status to 'Done'/'Completed' and record time_out
            time_out = datetime.now().strftime("%H:%M")
            c.execute("UPDATE visits SET pharmacy_status = ?, status = 'Done', time_out = ? WHERE id = ?",
                     (new_status, time_out, visit_id))
        else:
            c.execute("UPDATE visits SET pharmacy_status = ? WHERE id = ?", (new_status, visit_id))

        conn.commit()
        conn.close()
        return True

    def search_visits(self, search_term, role="all"):
        """
        Search for visits by patient name, ID, or visit ID.
        Filter results based on the role. (This was the cut-off function).
        """
        conn = self.connect()
        c = conn.cursor()

        # Base query joining visits, patients, and users (doctors)
        query = """
            SELECT v.id, v.patient_id, p.full_name, v.date, v.time_in, v.time_out, v.service, v.status, 
                   v.vitals_json, v.doctor_notes, v.pharmacy_instructions, v.pharmacy_status, u.name as doctor_name
            FROM visits v 
            JOIN patients p ON v.patient_id = p.id 
            LEFT JOIN users u ON v.assigned_doctor_id = u.id
            WHERE (p.full_name LIKE ? OR v.patient_id = ? OR v.id = ?)
        """
        params = (f"%{search_term}%", search_term.strip(), search_term.strip())

        # Role-specific filters (only pharmacy is explicitly filtered for in the provided code)
        if role == "pharmacy":
            query += " AND (v.pharmacy_status = 'Pending' OR v.status = 'Visit Pharmacy')"
        elif role == "doctor":
             # This search method won't work well without the doctor_id parameter.
             # We'll rely on the doctor's dashboard list for efficiency.
             pass

        query += " ORDER BY v.date DESC, v.time_in DESC"

        c.execute(query, params)
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

# ---------------------
# Application UI (Tkinter)
# ---------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vital Sign Informatics Console")
        self.geometry("1000x700")
        self.state('zoomed') # Start maximized
        self.configure(bg=COLORS['background'])

        self.db = DB()
        self.pdf_exporter = PDFExporter(self.db)
        self.logged_in_user = None

        # Main container for frames
        self.container = ttk.Frame(self, padding="10 10 10 10")
        self.container.pack(fill="both", expand=True)

        self.frames = {}

        # Initialize Login Frame first
        self.login_frame = LoginFrame(self.container, self)
        self.login_frame.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Style configuration (using ttk themes for modern look)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.apply_styles()

    def apply_styles(self):
        # Frame and Background
        self.style.configure('TFrame', background=COLORS['background'])

        # Headings
        self.style.configure('TLabel', background=COLORS['background'], foreground=COLORS['dark'])
        self.style.configure('Header.TLabel', font=('Helvetica', 18, 'bold'), foreground=COLORS['primary'])
        self.style.configure('SubHeader.TLabel', font=('Helvetica', 12, 'bold'), foreground=COLORS['secondary'])

        # Buttons
        self.style.configure('TButton', font=('Helvetica', 10, 'bold'), borderwidth=1, relief="flat", foreground=COLORS['card_bg'], background=COLORS['primary'])
        self.style.map('TButton', background=[('active', COLORS['secondary'])])
        self.style.configure('Accent.TButton', background=COLORS['accent'], foreground=COLORS['card_bg'])
        self.style.map('Accent.TButton', background=[('active', COLORS['warning'])])
        self.style.configure('Success.TButton', background=COLORS['success'], foreground=COLORS['card_bg'])
        self.style.map('Success.TButton', background=[('active', COLORS['primary'])])

        # Entry fields
        self.style.configure('TEntry', fieldbackground=COLORS['card_bg'], bordercolor=COLORS['border'], borderwidth=1)

        # Treeview (Table)
        self.style.configure('Treeview', font=('Helvetica', 10), background=COLORS['card_bg'], fieldbackground=COLORS['card_bg'], foreground=COLORS['dark'], rowheight=25)
        self.style.configure('Treeview.Heading', font=('Helvetica', 10, 'bold'), background=COLORS['primary'], foreground=COLORS['light'])
        self.style.map('Treeview.Heading', background=[('active', COLORS['secondary'])])
        self.style.map('Treeview', background=[('selected', COLORS['secondary']), ('active', COLORS['secondary'])], foreground=[('selected', COLORS['light'])])

    def show_frame(self, frame_class):
        """Raises a frame class to the top (shows it)"""
        frame = self.frames[frame_class]
        frame.tkraise()

    def login(self, user_info):
        """Handle successful login and transition to the main dashboard."""
        self.logged_in_user = user_info

        # Destroy the login frame
        self.login_frame.destroy()

        # Create the appropriate main dashboard frame
        role = user_info['role']
        if role == 'receptionist':
            self.main_frame = ReceptionistFrame(self.container, self)
        elif role == 'doctor':
            self.main_frame = DoctorFrame(self.container, self)
        elif role == 'pharmacist':
            self.main_frame = PharmacistFrame(self.container, self)
        else:
            messagebox.showerror("Role Error", "Unknown user role.")
            return

        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.tkraise()

    def logout(self):
        """Handle logout and return to the login screen."""
        if self.main_frame:
            self.main_frame.destroy()
            self.main_frame = None

        self.logged_in_user = None
        self.login_frame = LoginFrame(self.container, self)
        self.login_frame.grid(row=0, column=0, sticky="nsew")
        self.login_frame.tkraise()


class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style='TFrame', padding="50")
        self.controller = controller

        # Center content frame
        self.center_frame = ttk.Frame(self, style='TFrame', padding="30", borderwidth=2, relief="groove")
        self.center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ttk.Label(self.center_frame, text="Vital Sign Informatics", style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 20))
        ttk.Label(self.center_frame, text="LOGIN", style='SubHeader.TLabel').grid(row=1, column=0, columnspan=2, pady=(0, 15))

        # Mobile Field
        ttk.Label(self.center_frame, text="Mobile Number:", style='TLabel').grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.mobile_entry = ttk.Entry(self.center_frame, width=30)
        self.mobile_entry.grid(row=2, column=1, padx=5, pady=5)
        # Pre-fill for testing receptionist role (MO11)
        self.mobile_entry.insert(0, "0788365067")

        # Password Field
        ttk.Label(self.center_frame, text="Password:", style='TLabel').grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.password_entry = ttk.Entry(self.center_frame, show="*", width=30)
        self.password_entry.grid(row=3, column=1, padx=5, pady=5)
        # Pre-fill for testing
        self.password_entry.insert(0, "recept123")
        self.password_entry.bind('<Return>', lambda event: self.perform_login())

        # Login Button
        ttk.Button(self.center_frame, text="LOGIN", command=self.perform_login, style='Success.TButton', width=20).grid(row=4, column=0, columnspan=2, pady=20)

        # Test User Info (Quick Reference)
        ttk.Label(self.center_frame, text="Test Accounts:", style='SubHeader.TLabel').grid(row=5, column=0, columnspan=2, pady=(10, 0))
        test_info = [
            ("Receptionist (MO11)", "0788365067", "recept123"),
            ("Doctor (Mohammed)", "7681969865", "doctor123"),
            ("Pharmacist (Little MO)", "0777730606", "pharma123")
        ]

        for i, (role, mobile, pwd) in enumerate(test_info):
            ttk.Label(self.center_frame, text=f"{role}: {mobile} / {pwd}", font=('Helvetica', 8), foreground=COLORS['dark']).grid(row=6+i, column=0, columnspan=2, sticky='w', padx=5)

    def perform_login(self):
        mobile = self.mobile_entry.get().strip()
        password = self.password_entry.get().strip()

        if not mobile or not password:
            messagebox.showerror("Login Failed", "Please enter both mobile number and password.")
            return

        user = self.controller.db.authenticate_user(mobile, password)

        if user:
            messagebox.showinfo("Login Success", f"Welcome, {user['name']} ({user['role'].capitalize()})!")
            self.controller.login(user)
        else:
            messagebox.showerror("Login Failed", "Invalid mobile number or password.")
            self.password_entry.delete(0, tk.END)


class BaseDashboardFrame(ttk.Frame):
    def __init__(self, parent, controller, role_name):
        super().__init__(parent, style='TFrame', padding="10")
        self.controller = controller
        self.db = controller.db
        self.user = controller.logged_in_user
        self.role_name = role_name
        self.current_patient_id = None
        self.current_patient_data = None
        self.current_visit_id = None
        self.current_visit_data = None

        self.create_widgets()

    def create_widgets(self):
        # 1. Header Frame (Top)
        header_frame = ttk.Frame(self, style='TFrame')
        header_frame.pack(side="top", fill="x", pady=(0, 10))

        # Title/Logo
        ttk.Label(header_frame, text="🏥 VITAL SIGN CONSOLE", style='Header.TLabel').pack(side="left", padx=10)

        # User Info
        ttk.Label(header_frame, text=f"{self.role_name.upper()} | {self.user['name']}", style='SubHeader.TLabel', foreground=COLORS['primary']).pack(side="left", padx=20)

        # Logout Button
        ttk.Button(header_frame, text="Logout", command=self.controller.logout, style='Accent.TButton').pack(side="right")

        # 2. Main Content Frame (Middle)
        self.main_content_frame = ttk.Frame(self, style='TFrame')
        self.main_content_frame.pack(fill="both", expand=True)

        # This method is implemented by the specific role frame (Receptionist, Doctor, Pharmacist)
        self.setup_role_specific_ui(self.main_content_frame)

    def setup_role_specific_ui(self, parent_frame):
        """Placeholder for role-specific UI implementation."""
        raise NotImplementedError("Subclasses must implement setup_role_specific_ui")

# --- Specific Role Frames ---

class ReceptionistFrame(BaseDashboardFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Receptionist")

    def setup_role_specific_ui(self, parent_frame):
        # Configure grid for main content: 1 row, 2 columns (Patient List & Details)
        parent_frame.columnconfigure(0, weight=1) # Patient List
        parent_frame.columnconfigure(1, weight=2) # Details/History
        parent_frame.rowconfigure(0, weight=1)

        # 2a. Patient List Panel (Left)
        left_panel = ttk.Frame(parent_frame, style='TFrame', padding="10", relief='groove', borderwidth=1)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.rowconfigure(2, weight=1) # Treeview expands

        ttk.Label(left_panel, text="Patient Registration & Queue", style='SubHeader.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky='w')

        # Search/Add Frame
        search_frame = ttk.Frame(left_panel, style='TFrame')
        search_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)

        self.search_entry = ttk.Entry(search_frame, width=25)
        self.search_entry.grid(row=0, column=0, padx=5, sticky='ew')
        self.search_entry.bind('<Return>', lambda event: self.load_patient_list(search_term=self.search_entry.get()))
        ttk.Button(search_frame, text="Search", command=lambda: self.load_patient_list(search_term=self.search_entry.get()), style='TButton').grid(row=0, column=1, padx=5, sticky='w')
        ttk.Button(search_frame, text="+ New Patient", command=self.open_new_patient_window, style='Success.TButton').grid(row=0, column=2, padx=5, sticky='e')

        # Patient Treeview (Table)
        self.patient_tree = ttk.Treeview(left_panel, columns=("ID", "Name", "DOB", "Registered"), show='headings')
        self.patient_tree.heading("ID", text="ID", anchor='w')
        self.patient_tree.heading("Name", text="Full Name", anchor='w')
        self.patient_tree.heading("DOB", text="DOB", anchor='w')
        self.patient_tree.heading("Registered", text="Date", anchor='w')

        self.patient_tree.column("ID", width=50, stretch=False)
        self.patient_tree.column("Name", width=150, stretch=True)
        self.patient_tree.column("DOB", width=80, stretch=False)
        self.patient_tree.column("Registered", width=80, stretch=False)

        self.patient_tree.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.patient_tree.bind('<<TreeviewSelect>>', self.on_patient_select)

        # Scrollbar
        vsb = ttk.Scrollbar(left_panel, orient="vertical", command=self.patient_tree.yview)
        vsb.grid(row=2, column=2, sticky='ns')
        self.patient_tree.configure(yscrollcommand=vsb.set)

        # 2b. Patient Details Panel (Right)
        self.right_panel = ttk.Frame(parent_frame, style='TFrame', padding="10", relief='groove', borderwidth=1)
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.columnconfigure(0, weight=1)
        self.right_panel.rowconfigure(1, weight=1) # History frame expands

        ttk.Label(self.right_panel, text="Patient Details", style='SubHeader.TLabel', foreground=COLORS['primary']).grid(row=0, column=0, sticky='w', pady=(0, 10))

        # Placeholder/Dynamic Details Frame
        self.detail_frame = ttk.Frame(self.right_panel, style='TFrame')
        self.detail_frame.grid(row=1, column=0, sticky="nsew")

        # Load initial data
        self.load_patient_list()
        self.show_placeholder_details()

    def show_placeholder_details(self):
        """Clears the detail frame and shows a message."""
        for widget in self.detail_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.detail_frame, text="Select a patient to view details and history.", style='TLabel').pack(expand=True, padx=20, pady=50)

    def load_patient_list(self, search_term=None):
        """Loads patients into the Treeview."""
        # Clear existing entries
        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)

        if search_term:
            patients = self.db.search_patients(search_term)
        else:
            patients = self.db.list_patients()

        for p in patients:
            self.patient_tree.insert("", tk.END, values=(p['id'], p['full_name'], p['dob'], p['created_at'][:10]))

    def on_patient_select(self, event):
        """Event handler for selecting a patient from the treeview."""
        selected_item = self.patient_tree.selection()
        if not selected_item:
            self.show_placeholder_details()
            return

        values = self.patient_tree.item(selected_item, 'values')
        patient_id = int(values[0])
        self.current_patient_id = patient_id

        self.current_patient_data = self.db.get_patient(patient_id)

        self.show_patient_details()

    def show_patient_details(self):
        """Displays patient info, history, and actions in the right panel."""
        for widget in self.detail_frame.winfo_children():
            widget.destroy()

        # Patient Info Frame
        info_frame = ttk.Frame(self.detail_frame, style='TFrame', padding="10", borderwidth=1, relief='solid')
        info_frame.pack(fill="x", pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)

        p = self.current_patient_data

        ttk.Label(info_frame, text=f"Patient ID: {p['id']}", style='SubHeader.TLabel').grid(row=0, column=0, sticky='w', padx=5, pady=2)
        ttk.Label(info_frame, text=f"Name: {p['full_name']}", style='SubHeader.TLabel').grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Label(info_frame, text=f"DOB: {p['dob'] or 'N/A'}", style='TLabel').grid(row=2, column=0, sticky='w', padx=5, pady=2)
        ttk.Label(info_frame, text=f"Address: {p['address'] or 'N/A'}", style='TLabel').grid(row=3, column=0, sticky='w', padx=5, pady=2)

        # Action Buttons
        button_frame = ttk.Frame(info_frame, style='TFrame')
        button_frame.grid(row=0, column=1, rowspan=4, sticky='e', padx=10)

        ttk.Button(button_frame, text="📝 Edit Patient", command=self.open_edit_patient_window, style='TButton', width=15).pack(pady=5)
        ttk.Button(button_frame, text="➕ New Visit", command=self.open_new_visit_window, style='Success.TButton', width=15).pack(pady=5)
        ttk.Button(button_frame, text="📥 Export Report", command=self.export_patient_report, style='TButton', width=15).pack(pady=5)

        # Visit History Frame
        ttk.Label(self.detail_frame, text="Visit History (Last 5 Days)", style='SubHeader.TLabel', foreground=COLORS['secondary']).pack(fill="x", pady=(10, 5))

        # History Treeview
        self.history_tree = ttk.Treeview(self.detail_frame, columns=("VisitID", "Date", "Service", "Status"), show='headings')
        self.history_tree.heading("VisitID", text="Visit ID", anchor='w')
        self.history_tree.heading("Date", text="Date", anchor='w')
        self.history_tree.heading("Service", text="Service", anchor='w')
        self.history_tree.heading("Status", text="Status", anchor='w')

        self.history_tree.column("VisitID", width=70, stretch=False)
        self.history_tree.column("Date", width=100, stretch=False)
        self.history_tree.column("Service", width=150, stretch=True)
        self.history_tree.column("Status", width=100, stretch=False)

        self.history_tree.pack(fill="both", expand=True)
        self.history_tree.bind('<Double-1>', self.open_view_visit_window)

        self.load_visit_history()

    def load_visit_history(self):
        """Loads visit history for the current patient into the history treeview."""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        if not self.current_patient_id:
            return

        visits = self.db.get_patient_visit_history(self.current_patient_id)

        for v in visits:
            self.history_tree.insert("", tk.END, values=(v['id'], v['date'], v['service'], v['status']))

    def open_new_patient_window(self):
        NewPatientWindow(self.controller, self)

    def open_edit_patient_window(self):
        if not self.current_patient_data:
            messagebox.showwarning("Warning", "Please select a patient to edit.")
            return
        EditPatientWindow(self.controller, self, self.current_patient_data)

    def open_new_visit_window(self):
        if not self.current_patient_data:
            messagebox.showwarning("Warning", "Please select a patient to start a new visit.")
            return
        NewVisitWindow(self.controller, self, self.current_patient_data)

    def open_view_visit_window(self, event):
        selected_item = self.history_tree.selection()
        if not selected_item: return

        visit_id = self.history_tree.item(selected_item, 'values')[0]
        visit_data = self.db.get_visit(visit_id)

        if visit_data:
            ViewVisitWindow(self.controller, self, visit_data)

    def export_patient_report(self):
        if not self.current_patient_id:
            messagebox.showwarning("Export Warning", "Please select a patient to generate a report.")
            return

        try:
            self.controller.pdf_exporter.export_patient_report(self.current_patient_id)
        except Exception as e:
            messagebox.showerror("Export Error", f"An unexpected error occurred during PDF generation: {e}")


class DoctorFrame(BaseDashboardFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Doctor")

    def setup_role_specific_ui(self, parent_frame):
        parent_frame.columnconfigure(0, weight=2)
        parent_frame.columnconfigure(1, weight=3)
        parent_frame.rowconfigure(0, weight=1)

        # Left Panel: My Visits
        left_panel = ttk.Frame(parent_frame, style='TFrame', padding="10", relief='groove', borderwidth=1)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.rowconfigure(1, weight=1)

        ttk.Label(left_panel, text="My Assigned Visits", style='SubHeader.TLabel', foreground=COLORS['primary']).pack(fill='x', pady=(0, 10))

        self.visits_tree = ttk.Treeview(left_panel, columns=("VisitID", "Patient", "Date", "Status"), show='headings')
        self.visits_tree.heading("VisitID", text="Visit ID", anchor='w')
        self.visits_tree.heading("Patient", text="Patient Name", anchor='w')
        self.visits_tree.heading("Date", text="Date", anchor='w')
        self.visits_tree.heading("Status", text="Status", anchor='w')

        self.visits_tree.column("VisitID", width=70, stretch=False)
        self.visits_tree.column("Patient", width=150, stretch=True)
        self.visits_tree.column("Date", width=100, stretch=False)
        self.visits_tree.column("Status", width=100, stretch=False)

        self.visits_tree.pack(fill="both", expand=True)
        self.visits_tree.bind('<<TreeviewSelect>>', self.on_visit_select)

        # Right Panel: Visit Details and Treatment
        self.right_panel = ttk.Frame(parent_frame, style='TFrame', padding="10", relief='groove', borderwidth=1)
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.columnconfigure(0, weight=1)

        ttk.Label(self.right_panel, text="Visit Details & Treatment", style='SubHeader.TLabel', foreground=COLORS['secondary']).pack(fill='x', pady=(0, 10))

        self.detail_notebook = ttk.Notebook(self.right_panel)
        self.detail_notebook.pack(fill="both", expand=True, pady=5)

        self.vitals_frame = ttk.Frame(self.detail_notebook, style='TFrame', padding=10)
        self.notes_frame = ttk.Frame(self.detail_notebook, style='TFrame', padding=10)
        self.pharma_frame = ttk.Frame(self.detail_notebook, style='TFrame', padding=10)

        self.detail_notebook.add(self.vitals_frame, text='Vital Signs')
        self.detail_notebook.add(self.notes_frame, text='Notes & Status')
        self.detail_notebook.add(self.pharma_frame, text='Pharmacy')

        self.setup_vitals_ui(self.vitals_frame)
        self.setup_notes_ui(self.notes_frame)
        self.setup_pharma_ui(self.pharma_frame)

        self.load_doctor_visits()
        self.reset_visit_details()

    def load_doctor_visits(self):
        for item in self.visits_tree.get_children():
            self.visits_tree.delete(item)

        visits = self.db.get_visits_for_doctor(self.user['id'])

        for v in visits:
            self.visits_tree.insert("", tk.END, values=(v['visit_id'], v['patient_name'], v['date'], v['status']))

    def on_visit_select(self, event):
        selected_item = self.visits_tree.selection()
        if not selected_item:
            self.reset_visit_details()
            return

        visit_id = self.visits_tree.item(selected_item, 'values')[0]
        self.current_visit_id = visit_id
        self.current_visit_data = self.db.get_visit(visit_id)

        self.show_visit_details()

    def reset_visit_details(self):
        self.current_visit_id = None
        self.current_visit_data = None

        # Clear all fields (needs dedicated method)
        self.vitals_bp.delete(0, tk.END); self.vitals_bp.insert(0, "N/A")
        self.vitals_hr.delete(0, tk.END); self.vitals_hr.insert(0, "N/A")
        self.vitals_temp.delete(0, tk.END); self.vitals_temp.insert(0, "N/A")
        self.vitals_resp.delete(0, tk.END); self.vitals_resp.insert(0, "N/A")
        self.vitals_spo2.delete(0, tk.END); self.vitals_spo2.insert(0, "N/A")

        self.notes_text.delete('1.0', tk.END)
        self.pharma_text.delete('1.0', tk.END)
        self.status_var.set("Pending")
        self.patient_info_label.config(text="No Visit Selected")
        self.plot_vitals_history({})

    def show_visit_details(self):
        v = self.current_visit_data

        self.patient_info_label.config(text=f"Patient: {v['patient_name']} (ID: {v['patient_id']}) | Visit Date: {v['date']}")

        # Vitals Tab
        vitals = v.get('vitals', {})
        self.vitals_bp.delete(0, tk.END); self.vitals_bp.insert(0, vitals.get('bp', 'N/A'))
        self.vitals_hr.delete(0, tk.END); self.vitals_hr.insert(0, vitals.get('hr', 'N/A'))
        self.vitals_temp.delete(0, tk.END); self.vitals_temp.insert(0, vitals.get('temp', 'N/A'))
        self.vitals_resp.delete(0, tk.END); self.vitals_resp.insert(0, vitals.get('resp', 'N/A'))
        self.vitals_spo2.delete(0, tk.END); self.vitals_spo2.insert(0, vitals.get('spo2', 'N/A'))

        # Notes Tab
        self.notes_text.delete('1.0', tk.END); self.notes_text.insert('1.0', v.get('notes', ''))
        self.status_var.set(v.get('status', 'Pending'))

        # Pharmacy Tab
        self.pharma_text.delete('1.0', tk.END); self.pharma_text.insert('1.0', v.get('pharmacy_instructions', ''))

        # Load history for graph
        history_visits = self.db.get_visits_for_patient(v['patient_id'])
        self.plot_vitals_history(history_visits)

    def setup_vitals_ui(self, frame):
        frame.columnconfigure(0, weight=1); frame.columnconfigure(1, weight=1)

        self.patient_info_label = ttk.Label(frame, text="Select a Visit to Start Consultation", style='SubHeader.TLabel')
        self.patient_info_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Vitals Input
        vitals_inputs = [
            ("Blood Pressure (mmHg):", 'bp', tk.StringVar()),
            ("Heart Rate (bpm):", 'hr', tk.StringVar()),
            ("Temperature (°F):", 'temp', tk.StringVar()),
            ("Respiratory Rate (min):", 'resp', tk.StringVar()),
            ("SpO2 (%):", 'spo2', tk.StringVar())
        ]

        entries = {}
        for i, (label_text, key, var) in enumerate(vitals_inputs, 1):
            ttk.Label(frame, text=label_text).grid(row=i, column=0, sticky='w', padx=5, pady=5)
            entry = ttk.Entry(frame, textvariable=var, width=20)
            entry.grid(row=i, column=1, sticky='ew', padx=5, pady=5)
            entries[key] = entry

        self.vitals_bp = entries['bp']
        self.vitals_hr = entries['hr']
        self.vitals_temp = entries['temp']
        self.vitals_resp = entries['resp']
        self.vitals_spo2 = entries['spo2']

        # Vitals History Plot
        ttk.Label(frame, text="Vitals Trend (Last 10 Visits)", style='SubHeader.TLabel', foreground=COLORS['secondary']).grid(row=len(vitals_inputs)+1, column=0, columnspan=2, pady=(15, 5), sticky='w')

        self.fig = Figure(figsize=(5, 3), dpi=100)
        self.vitals_plot_canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.vitals_plot_canvas.draw()
        self.vitals_plot_canvas.get_tk_widget().grid(row=len(vitals_inputs)+2, column=0, columnspan=2, sticky='nsew')

        frame.rowconfigure(len(vitals_inputs)+2, weight=1)

    def plot_vitals_history(self, visits):
        """Generates a history plot for key vital signs (HR and Temp)."""

        dates = [datetime.strptime(v['date'], '%Y-%m-%d') for v in visits]
        hrs = [v['vitals'].get('hr') for v in visits]
        temps = [v['vitals'].get('temp') for v in visits]

        # Filter out visits with missing or non-numeric data and keep the last 10
        valid_data = sorted([
            (d, h, t) for d, h, t in zip(dates, hrs, temps)
            if h is not None and t is not None and isinstance(h, (int, float)) and isinstance(t, (int, float))
        ], key=lambda x: x[0])[-10:]

        if not valid_data:
            self.fig.clear()
            a = self.fig.add_subplot(111)
            a.text(0.5, 0.5, "No numeric history data available",
                   horizontalalignment='center', verticalalignment='center',
                   transform=a.transAxes, color='gray')
            a.set_xticks([])
            a.set_yticks([])
            self.vitals_plot_canvas.draw()
            return

        dates, hrs, temps = zip(*valid_data)

        self.fig.clear()
        a = self.fig.add_subplot(111)

        # Heart Rate Plot
        a.plot(dates, hrs, label='Heart Rate (bpm)', color=COLORS['secondary'], marker='o')
        a.set_ylabel('Heart Rate (bpm)', color=COLORS['secondary'])
        a.tick_params(axis='y', labelcolor=COLORS['secondary'])

        # Temperature Plot (Secondary Axis)
        ax2 = a.twinx()
        ax2.plot(dates, temps, label='Temperature (°F)', color=COLORS['accent'], marker='x')
        ax2.set_ylabel('Temperature (°F)', color=COLORS['accent'])
        ax2.tick_params(axis='y', labelcolor=COLORS['accent'])

        # Formatting
        self.fig.autofmt_xdate(rotation=45)
        a.set_title("Vitals Trend", fontsize=10)
        a.grid(True, linestyle='--', alpha=0.6)

        self.vitals_plot_canvas.draw()

    def setup_notes_ui(self, frame):
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        # Status Dropdown
        status_options = ["Pending", "Visit Pharmacy", "Done"]
        self.status_var = tk.StringVar(frame, value=status_options[0])

        status_frame = ttk.Frame(frame, style='TFrame')
        status_frame.pack(fill='x', pady=5)
        ttk.Label(status_frame, text="Visit Status:").pack(side='left', padx=5)
        self.status_menu = ttk.Combobox(status_frame, textvariable=self.status_var, values=status_options, state='readonly', width=20)
        self.status_menu.pack(side='left', padx=5)

        # Doctor's Notes
        ttk.Label(frame, text="Doctor's Notes (Diagnosis, Plan, etc.):", style='SubHeader.TLabel').pack(fill='x', pady=(10, 5))
        self.notes_text = tk.Text(frame, height=10, width=80, wrap=tk.WORD, font=('Helvetica', 10))
        self.notes_text.pack(fill="both", expand=True)

        # Save Button
        ttk.Button(frame, text="SAVE NOTES & STATUS", command=self.save_doctor_notes, style='Success.TButton').pack(pady=10)

    def setup_pharma_ui(self, frame):
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Pharmacy Instructions (Medication Order):", style='SubHeader.TLabel').pack(fill='x', pady=(0, 5))

        # Pharmacy Instructions Text
        self.pharma_text = tk.Text(frame, height=10, width=80, wrap=tk.WORD, font=('Helvetica', 10))
        self.pharma_text.pack(fill="both", expand=True)

        # Finalize Button (Combines all data and marks visit for pharmacy)
        ttk.Button(frame, text="FINALIZE VISIT & SEND TO PHARMACY", command=self.finalize_visit_and_send_to_pharmacy, style='Accent.TButton').pack(pady=10)

    def save_doctor_notes(self):
        if not self.current_visit_id:
            messagebox.showwarning("Warning", "Please select a visit first.")
            return

        try:
            # Gather data (vitals must be saved first for notes to make sense)
            vitals = self.get_vitals_from_ui()
            notes = self.notes_text.get('1.0', tk.END).strip()
            status = self.status_var.get()
            pharmacy_instructions = self.pharma_text.get('1.0', tk.END).strip()

            if not notes and status not in ("Pending", "Visit Pharmacy"):
                if not messagebox.askyesno("Confirm Save", "Doctor's notes are empty. Continue saving without notes?"):
                    return

            # Update DB - using update_visit_status for flexibility
            self.db.update_visit_status(
                visit_id=self.current_visit_id,
                new_status=status,
                doctor_notes=notes,
                pharmacy_instructions=pharmacy_instructions,
                vitals_dict=vitals # Saving vitals here too, though vitals are usually set during registration
            )

            messagebox.showinfo("Success", "Visit notes and status saved successfully.")
            self.load_doctor_visits()
            # Reload current data to reflect changes
            self.current_visit_data = self.db.get_visit(self.current_visit_id)
            self.show_visit_details()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save visit data: {e}")

    def finalize_visit_and_send_to_pharmacy(self):
        if not self.current_visit_id:
            messagebox.showwarning("Warning", "Please select a visit first.")
            return

        pharma_inst = self.pharma_text.get('1.0', tk.END).strip()
        if not pharma_inst:
            if not messagebox.askyesno("Confirm Action", "Pharmacy instructions are empty. Are you sure you want to mark this for pharmacy visit?"):
                return

        try:
            vitals = self.get_vitals_from_ui()
            notes = self.notes_text.get('1.0', tk.END).strip()

            # 1. Update visit status to 'Visit Pharmacy' and save all data
            self.db.update_visit_status(
                visit_id=self.current_visit_id,
                new_status="Visit Pharmacy",
                doctor_notes=notes,
                pharmacy_instructions=pharma_inst,
                vitals_dict=vitals
            )

            # 2. Ensure pharmacy status is 'Pending' (this is set by the update_visit_status/add_visit, but we'll ensure it)
            # The structure currently relies on the initial add_visit/update_visit status logic.
            # A simpler way is to update the pharmacy_status separately if not already pending
            self.db.update_pharmacy_status_and_timeout(self.current_visit_id, "Pending")

            messagebox.showinfo("Success", "Visit finalized and sent to Pharmacy queue.")
            self.load_doctor_visits()
            self.reset_visit_details() # Clear the interface after sending

        except Exception as e:
            messagebox.showerror("Error", f"Failed to finalize visit: {e}")

    def get_vitals_from_ui(self):
        vitals = {}
        try:
            vitals['bp'] = self.vitals_bp.get().strip()
            vitals['hr'] = float(self.vitals_hr.get().strip()) if self.vitals_hr.get().strip().replace('.', '', 1).isdigit() else None
            vitals['temp'] = float(self.vitals_temp.get().strip()) if self.vitals_temp.get().strip().replace('.', '', 1).isdigit() else None
            vitals['resp'] = int(self.vitals_resp.get().strip()) if self.vitals_resp.get().strip().isdigit() else None
            vitals['spo2'] = int(self.vitals_spo2.get().strip()) if self.vitals_spo2.get().strip().isdigit() else None
        except ValueError:
             messagebox.showwarning("Input Error", "Heart Rate, Temperature, Respiratory Rate, and SpO2 must be numeric.")
             raise
        return vitals

class PharmacistFrame(BaseDashboardFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "Pharmacist")

    def setup_role_specific_ui(self, parent_frame):
        parent_frame.columnconfigure(0, weight=2)
        parent_frame.columnconfigure(1, weight=3)
        parent_frame.rowconfigure(0, weight=1)

        # Left Panel: Pharmacy Queue
        left_panel = ttk.Frame(parent_frame, style='TFrame', padding="10", relief='groove', borderwidth=1)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.rowconfigure(1, weight=1)

        ttk.Label(left_panel, text="Pharmacy Pending Queue", style='SubHeader.TLabel', foreground=COLORS['primary']).pack(fill='x', pady=(0, 10))

        self.queue_tree = ttk.Treeview(left_panel, columns=("VisitID", "Patient", "Doctor", "Status"), show='headings')
        self.queue_tree.heading("VisitID", text="Visit ID", anchor='w')
        self.queue_tree.heading("Patient", text="Patient Name", anchor='w')
        self.queue_tree.heading("Doctor", text="Doctor", anchor='w')
        self.queue_tree.heading("Status", text="Status", anchor='w')

        self.queue_tree.column("VisitID", width=70, stretch=False)
        self.queue_tree.column("Patient", width=150, stretch=True)
        self.queue_tree.column("Doctor", width=100, stretch=False)
        self.queue_tree.column("Status", width=100, stretch=False)

        self.queue_tree.pack(fill="both", expand=True)
        self.queue_tree.bind('<<TreeviewSelect>>', self.on_queue_select)

        # Right Panel: Dispensing Details
        self.right_panel = ttk.Frame(parent_frame, style='TFrame', padding="10", relief='groove', borderwidth=1)
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.columnconfigure(0, weight=1)
        self.right_panel.rowconfigure(3, weight=1)

        self.patient_info_label = ttk.Label(self.right_panel, text="Select a Visit from Queue", style='SubHeader.TLabel', foreground=COLORS['secondary'])
        self.patient_info_label.grid(row=0, column=0, sticky='w', pady=(0, 10))

        self.pharma_inst_label = ttk.Label(self.right_panel, text="Doctor's Instructions:", style='SubHeader.TLabel')
        self.pharma_inst_label.grid(row=1, column=0, sticky='w', pady=(5, 0))

        self.instructions_text = tk.Text(self.right_panel, height=8, width=80, wrap=tk.WORD, state=tk.DISABLED, font=('Helvetica', 10, 'bold'), background=COLORS['light'])
        self.instructions_text.grid(row=2, column=0, sticky='ew', pady=(0, 10))

        ttk.Label(self.right_panel, text="Pharmacist's Dispensing Notes (Optional):", style='SubHeader.TLabel').grid(row=3, column=0, sticky='w', pady=(10, 5))
        self.notes_text = tk.Text(self.right_panel, height=8, width=80, wrap=tk.WORD, font=('Helvetica', 10))
        self.notes_text.grid(row=4, column=0, sticky='nsew')

        # Action Buttons
        button_frame = ttk.Frame(self.right_panel, style='TFrame')
        button_frame.grid(row=5, column=0, sticky='e', pady=(15, 0))

        ttk.Button(button_frame, text="Mark as DISPENSED (Completed)", command=lambda: self.update_pharmacy_status("Completed"), style='Success.TButton').pack(side='right', padx=5)
        ttk.Button(button_frame, text="Mark as IN PROGRESS", command=lambda: self.update_pharmacy_status("In Progress"), style='TButton').pack(side='right', padx=5)

        self.load_pharmacy_queue()
        self.reset_dispensing_details()

    def load_pharmacy_queue(self):
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)

        visits = self.db.get_visits_for_pharmacy()

        for v in visits:
            self.queue_tree.insert("", tk.END, values=(v['visit_id'], v['patient_name'], v['doctor_name'], v['pharmacy_status']))

    def on_queue_select(self, event):
        selected_item = self.queue_tree.selection()
        if not selected_item:
            self.reset_dispensing_details()
            return

        visit_id = self.queue_tree.item(selected_item, 'values')[0]
        self.current_visit_id = visit_id
        self.current_visit_data = self.db.get_visit(visit_id)

        self.show_dispensing_details()

    def reset_dispensing_details(self):
        self.current_visit_id = None
        self.current_visit_data = None
        self.patient_info_label.config(text="Select a Visit from Queue")

        self.instructions_text.config(state=tk.NORMAL)
        self.instructions_text.delete('1.0', tk.END)
        self.instructions_text.config(state=tk.DISABLED)

        self.notes_text.delete('1.0', tk.END)

    def show_dispensing_details(self):
        v = self.current_visit_data
        if not v:
            self.reset_dispensing_details()
            return

        self.patient_info_label.config(text=f"Visit ID: {v['visit_id']} | Patient: {v['patient_name']} | Doctor: {v['doctor_name']}")

        instructions = v.get('pharmacy_instructions', 'No specific instructions provided by the doctor.')

        self.instructions_text.config(state=tk.NORMAL)
        self.instructions_text.delete('1.0', tk.END)
        self.instructions_text.insert('1.0', instructions)
        self.instructions_text.config(state=tk.DISABLED)

        # Optionally load pharmacist's notes if they were saved previously (not implemented in DB schema but good practice)
        self.notes_text.delete('1.0', tk.END)

    def update_pharmacy_status(self, new_status):
        if not self.current_visit_id:
            messagebox.showwarning("Warning", "Please select a visit from the queue first.")
            return

        if new_status == "Completed":
            # Final check before marking as complete
            if not messagebox.askyesno("Confirm Dispensing", f"Mark Visit ID {self.current_visit_id} as DISPENSED (Completed)?"):
                return

        try:
            self.db.update_pharmacy_status_and_timeout(self.current_visit_id, new_status)
            messagebox.showinfo("Success", f"Visit ID {self.current_visit_id} status updated to: {new_status}")

            self.load_pharmacy_queue()
            self.reset_dispensing_details()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to update pharmacy status: {e}")

# --- Modal Windows ---

class NewPatientWindow(tk.Toplevel):
    def __init__(self, controller, parent_frame):
        super().__init__(controller)
        self.title("Register New Patient")
        self.geometry("400x300")
        self.controller = controller
        self.parent_frame = parent_frame
        self.transient(controller)
        self.grab_set()

        self.frame = ttk.Frame(self, padding="15", style='TFrame')
        self.frame.pack(fill="both", expand=True)

        ttk.Label(self.frame, text="New Patient Details", style='SubHeader.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # Fields
        labels = ["Full Name:", "Address:", "DOB (YYYY-MM-DD):"]
        self.entries = {}

        for i, text in enumerate(labels, 1):
            ttk.Label(self.frame, text=text).grid(row=i, column=0, sticky='w', padx=5, pady=5)
            entry = ttk.Entry(self.frame, width=30)
            entry.grid(row=i, column=1, sticky='ew', padx=5, pady=5)
            self.entries[text.split(' ')[0]] = entry

        # Save Button
        ttk.Button(self.frame, text="Register Patient", command=self.save_patient, style='Success.TButton').grid(row=len(labels) + 1, column=0, columnspan=2, pady=20)

    def save_patient(self):
        full_name = self.entries['Full'].get().strip()
        address = self.entries['Address'].get().strip()
        dob = self.entries['DOB'].get().strip()

        if not full_name:
            messagebox.showerror("Input Error", "Full Name is required.")
            return

        try:
            # Basic DOB validation
            if dob:
                datetime.strptime(dob, "%Y-%m-%d")

            patient_id = self.controller.db.add_patient(full_name, address, dob)

            messagebox.showinfo("Success", f"Patient registered successfully! ID: {patient_id}")
            self.parent_frame.load_patient_list() # Update the main list
            self.destroy()

        except ValueError:
            messagebox.showerror("Input Error", "Date of Birth must be in YYYY-MM-DD format.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to register patient: {e}")

class EditPatientWindow(tk.Toplevel):
    def __init__(self, controller, parent_frame, patient_data):
        super().__init__(controller)
        self.title(f"Edit Patient: {patient_data['full_name']}")
        self.geometry("400x300")
        self.controller = controller
        self.parent_frame = parent_frame
        self.patient_data = patient_data
        self.transient(controller)
        self.grab_set()

        self.frame = ttk.Frame(self, padding="15", style='TFrame')
        self.frame.pack(fill="both", expand=True)

        ttk.Label(self.frame, text=f"Edit Patient Details (ID: {patient_data['id']})", style='SubHeader.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # Fields
        data_map = {"Full Name:": "full_name", "Address:": "address", "DOB (YYYY-MM-DD):": "dob"}
        self.entries = {}

        for i, (label_text, key) in enumerate(data_map.items(), 1):
            ttk.Label(self.frame, text=label_text).grid(row=i, column=0, sticky='w', padx=5, pady=5)
            entry = ttk.Entry(self.frame, width=30)
            entry.grid(row=i, column=1, sticky='ew', padx=5, pady=5)
            entry.insert(0, patient_data.get(key, ''))
            self.entries[key] = entry

        # Save Button
        ttk.Button(self.frame, text="Save Changes", command=self.save_changes, style='Success.TButton').grid(row=len(data_map) + 1, column=0, columnspan=2, pady=20)

    def save_changes(self):
        full_name = self.entries['full_name'].get().strip()
        address = self.entries['address'].get().strip()
        dob = self.entries['dob'].get().strip()

        if not full_name:
            messagebox.showerror("Input Error", "Full Name is required.")
            return

        try:
            if dob:
                datetime.strptime(dob, "%Y-%m-%d")

            self.controller.db.update_patient(self.patient_data['id'], full_name, address, dob)

            messagebox.showinfo("Success", "Patient details updated successfully!")
            self.parent_frame.load_patient_list() # Update the main list
            # Update the parent frame's current patient data and view
            self.parent_frame.current_patient_data = self.controller.db.get_patient(self.patient_data['id'])
            self.parent_frame.show_patient_details()
            self.destroy()

        except ValueError:
            messagebox.showerror("Input Error", "Date of Birth must be in YYYY-MM-DD format.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update patient: {e}")

class NewVisitWindow(tk.Toplevel):
    def __init__(self, controller, parent_frame, patient_data):
        super().__init__(controller)
        self.title(f"New Visit for: {patient_data['full_name']}")
        self.geometry("600x450")
        self.controller = controller
        self.parent_frame = parent_frame
        self.patient_data = patient_data
        self.transient(controller)
        self.grab_set()

        self.frame = ttk.Frame(self, padding="15", style='TFrame')
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(1, weight=1)

        ttk.Label(self.frame, text=f"New Visit for Patient: {patient_data['full_name']} (ID: {patient_data['id']})", style='SubHeader.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Visit Details
        row_idx = 1

        ttk.Label(self.frame, text="Service:").grid(row=row_idx, column=0, sticky='w', padx=5, pady=5); row_idx+=1
        self.service_entry = ttk.Entry(self.frame, width=40); self.service_entry.grid(row=row_idx, column=0, columnspan=2, sticky='ew', padx=5, pady=5); row_idx+=1
        self.service_entry.insert(0, "General Consultation")

        ttk.Label(self.frame, text="Assigned Doctor:").grid(row=row_idx, column=0, sticky='w', padx=5, pady=5); row_idx+=1
        self.doctors = self.controller.db.get_doctors()
        self.doctor_names = [d['name'] for d in self.doctors]
        self.doctor_var = tk.StringVar(self.frame, value=self.doctor_names[0] if self.doctor_names else "No Doctors")
        self.doctor_menu = ttk.Combobox(self.frame, textvariable=self.doctor_var, values=self.doctor_names, state='readonly'); self.doctor_menu.grid(row=row_idx, column=0, columnspan=2, sticky='ew', padx=5, pady=5); row_idx+=1

        # Vitals Inputs (side by side)
        vitals_frame = ttk.Frame(self.frame, style='TFrame'); vitals_frame.grid(row=row_idx, column=0, columnspan=2, sticky='ew', pady=(15, 0)); row_idx+=1
        vitals_frame.columnconfigure(1, weight=1); vitals_frame.columnconfigure(3, weight=1)

        vitals_inputs = [
            ("BP (mmHg):", 'bp', 0, 0), ("HR (bpm):", 'hr', 0, 2),
            ("Temp (°F):", 'temp', 1, 0), ("Resp (min):", 'resp', 1, 2),
            ("SpO2 (%):", 'spo2', 2, 0)
        ]
        self.vitals_entries = {}

        for label_text, key, r, c in vitals_inputs:
            ttk.Label(vitals_frame, text=label_text).grid(row=r, column=c, sticky='w', padx=5, pady=2)
            entry = ttk.Entry(vitals_frame, width=15)
            entry.grid(row=r, column=c+1, sticky='ew', padx=5, pady=2)
            self.vitals_entries[key] = entry

            # Pre-fill common defaults
            if key == 'bp': entry.insert(0, "120/80")
            if key == 'hr': entry.insert(0, "75")
            if key == 'temp': entry.insert(0, "98.6")
            if key == 'resp': entry.insert(0, "16")
            if key == 'spo2': entry.insert(0, "98")


        # Save Button
        ttk.Button(self.frame, text="Register Visit & Save Vitals", command=self.save_visit, style='Success.TButton').grid(row=row_idx, column=0, columnspan=2, pady=20)

    def save_visit(self):
        service = self.service_entry.get().strip()
        doctor_name = self.doctor_var.get()

        if not service:
            messagebox.showerror("Input Error", "Service name is required.")
            return

        # Get Doctor ID
        assigned_doctor_id = next((d['id'] for d in self.doctors if d['name'] == doctor_name), None)
        if assigned_doctor_id is None:
            messagebox.showerror("Error", "Selected doctor not found.")
            return

        # Gather Vitals
        vitals = {}
        try:
            vitals['bp'] = self.vitals_entries['bp'].get().strip()
            vitals['hr'] = float(self.vitals_entries['hr'].get().strip())
            vitals['temp'] = float(self.vitals_entries['temp'].get().strip())
            vitals['resp'] = int(self.vitals_entries['resp'].get().strip())
            vitals['spo2'] = int(self.vitals_entries['spo2'].get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "Vitals (HR, Temp, Resp, SpO2) must be valid numbers.")
            return
        except Exception:
            # Handle potential empty string errors for BP which is kept as text
            pass

        try:
            visit_id = self.controller.db.add_visit(
                patient_id=self.patient_data['id'],
                assigned_doctor_id=assigned_doctor_id,
                visit_date=date.today().isoformat(),
                time_in=datetime.now().strftime("%H:%M"),
                time_out=None,
                service=service,
                status="Pending",
                vitals_dict=vitals,
                doctor_notes=""
            )

            messagebox.showinfo("Success", f"New visit registered successfully! Visit ID: {visit_id}")
            self.parent_frame.load_visit_history() # Update the history list
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to register visit: {e}")

class ViewVisitWindow(tk.Toplevel):
    def __init__(self, controller, parent_frame, visit_data):
        super().__init__(controller)
        self.title(f"Visit Details: ID {visit_data['visit_id']}")
        self.geometry("500x550")
        self.controller = controller
        self.parent_frame = parent_frame
        self.visit_data = visit_data
        self.transient(controller)
        self.grab_set()

        self.frame = ttk.Frame(self, padding="15", style='TFrame')
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(1, weight=1)

        v = self.visit_data

        ttk.Label(self.frame, text=f"Visit ID: {v['visit_id']} | Patient: {v['patient_name']}", style='SubHeader.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')

        # Visit Info
        info_data = [
            ("Date/Time:", f"{v['date']} ({v['time_in']} - {v['time_out'] or 'N/A'})"),
            ("Service:", v['service']),
            ("Doctor:", v['doctor_name'] or 'Unassigned'),
            ("Status:", v['status']),
            ("Pharmacy Status:", v['pharmacy_status'] or 'N/A')
        ]

        for i, (label, value) in enumerate(info_data, 1):
            ttk.Label(self.frame, text=label).grid(row=i, column=0, sticky='w', padx=5)
            ttk.Label(self.frame, text=value, font=('Helvetica', 10, 'bold')).grid(row=i, column=1, sticky='w', padx=5)

        # Vitals
        ttk.Label(self.frame, text="Vital Signs:", style='SubHeader.TLabel', foreground=COLORS['accent']).grid(row=len(info_data)+1, column=0, columnspan=2, pady=(15, 5), sticky='w')
        vitals = v.get('vitals', {})
        vitals_data = [
            ("BP:", vitals.get('bp', 'N/A')), ("HR:", f"{vitals.get('hr', 'N/A')} bpm"),
            ("Temp:", f"{vitals.get('temp', 'N/A')} °F"), ("Resp:", f"{vitals.get('resp', 'N/A')} min"),
            ("SpO2:", f"{vitals.get('spo2', 'N/A')} %")
        ]
        v_frame = ttk.Frame(self.frame, style='TFrame')
        v_frame.grid(row=len(info_data)+2, column=0, columnspan=2, sticky='ew')

        for i, (label, value) in enumerate(vitals_data):
            r, c = divmod(i, 2)
            ttk.Label(v_frame, text=label).grid(row=r, column=c*2, sticky='w', padx=5, pady=2)
            ttk.Label(v_frame, text=value, font=('Helvetica', 10)).grid(row=r, column=c*2+1, sticky='w', padx=5, pady=2)


        # Doctor Notes
        ttk.Label(self.frame, text="Doctor's Notes:", style='SubHeader.TLabel', foreground=COLORS['secondary']).grid(row=len(info_data)+3, column=0, columnspan=2, pady=(15, 5), sticky='w')
        notes_text = tk.Text(self.frame, height=5, wrap=tk.WORD, state=tk.DISABLED, font=('Helvetica', 10))
        notes_text.insert(tk.END, v.get('notes', 'No notes recorded.'))
        notes_text.grid(row=len(info_data)+4, column=0, columnspan=2, sticky='ew')

        # Pharmacy Instructions
        ttk.Label(self.frame, text="Pharmacy Instructions:", style='SubHeader.TLabel', foreground=COLORS['success']).grid(row=len(info_data)+5, column=0, columnspan=2, pady=(15, 5), sticky='w')
        pharma_text = tk.Text(self.frame, height=5, wrap=tk.WORD, state=tk.DISABLED, font=('Helvetica', 10))
        pharma_text.insert(tk.END, v.get('pharmacy_instructions', 'No instructions provided.'))
        pharma_text.grid(row=len(info_data)+6, column=0, columnspan=2, sticky='ew')

# --- Main Execution ---

if __name__ == "__main__":
    ensure_db()
    app = App()
    app.mainloop()