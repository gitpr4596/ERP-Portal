
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseDownload
from datetime import datetime
import pytz
import json
from sqlalchemy import inspect, text
from flask import send_file # Add this to your existing imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import tempfile # Add this to your existing imports
import firebase_admin
from firebase_admin import credentials, firestore


# === Flask App Initialization ===
indian_tz = pytz.timezone("Asia/Kolkata")
app = Flask(__name__)
app.secret_key = 'supersecretkey'

# === File Upload Configuration ===
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# === SQLite DB Setup ===
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# === Helper Functions ===
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_float_convert(value, default=None):
    """Safely convert a string to float, handling empty strings"""
    if not value or value.strip() == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int_convert(value, default=None):
    """Safely convert a string to int, handling empty strings"""
    if not value or value.strip() == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

# === File Serving Route ===
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === Firebase Initialization ===
try:
    # Check if Firebase is already initialized
    if not firebase_admin._apps:
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate('firebase-service-account.json')
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully")
    else:
        print("Firebase Admin SDK already initialized")
    
    # Get Firestore client
    db_firestore = firestore.client()
    print("Firestore client initialized successfully")
    
except Exception as e:
    print(f"Firebase initialization failed: {e}")
    print("Using Firebase REST API fallback")
    db_firestore = None

# === Association Table for Many-to-Many User <-> Role ===
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)



#leave model

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_lead_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    spv_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    emp_no = db.Column(db.String(50))
    contact_details = db.Column(db.String(100))
    applicant_name = db.Column(db.String(100))
    total_leaves = db.Column(db.Integer)
    leave_availed = db.Column(db.Integer)
    balance_leaves = db.Column(db.Integer)
    from_date = db.Column(db.String(20))
    from_time = db.Column(db.String(20))
    to_date = db.Column(db.String(20))
    to_time = db.Column(db.String(20))
    reason = db.Column(db.Text)
    applicant_sign = db.Column(db.String(100))
    applicant_sign_date = db.Column(db.String(20))
    status = db.Column(db.String(50), default='Pending')
    # Add these back in
    reporting_authority_sign = db.Column(db.String(100))
    reporting_authority_date = db.Column(db.String(20))
    hr_sign = db.Column(db.String(100)) # ADD THIS LINE
    hr_date = db.Column(db.String(20)) # ADD THIS LINE
    director_sign = db.Column(db.String(100))
    director_date = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    status = db.Column(db.String(50), default='Pending')
    
    user = db.relationship('User', foreign_keys=[user_id])
    team_lead = db.relationship('User', foreign_keys=[team_lead_id])

class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(20), nullable=False)  # Format: YYYY-MM-DD
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    creator = db.relationship('User', foreign_keys=[created_by])


# === PermissionRequest Model (NEW) ===
class PermissionRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_lead_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    spv_name = db.Column(db.String(100))
    date = db.Column(db.String(20))
    applicant_name = db.Column(db.String(100))
    reason = db.Column(db.Text)
    time_out = db.Column(db.String(20))
    time_in = db.Column(db.String(20))
    going_to = db.Column(db.String(200))
    applicant_sign = db.Column(db.String(100))
    approver_sign = db.Column(db.String(100))
    team_lead_sign = db.Column(db.String(100))
    hr_sign = db.Column(db.String(100)) # ADD THIS LINE
    director_sign = db.Column(db.String(100)) # ADD THIS LINE
    status = db.Column(db.String(50), default='Pending')

    user = db.relationship('User', foreign_keys=[user_id])
    team_lead = db.relationship('User', foreign_keys=[team_lead_id])

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.Time)
    check_out_time = db.Column(db.Time)
    status = db.Column(db.String(20), default='Present')  # Present, Absent, Late, Half Day
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz))
    
    # Ensure one record per user per date
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='unique_user_date'),)
    
    user = db.relationship('User', foreign_keys=[user_id])

# === User Model ===
# === User Model ===
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(100))
    created_by_admin = db.Column(db.Boolean, default=False)
    pf_no = db.Column(db.String(50))  # PF Number field
    # 👇 ADD THIS LINE
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))

# === Role Model ===
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
# === TravelRequest Model (MODIFIED) ===
class TravelRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company = db.Column(db.String(100))
    date = db.Column(db.String(20))
    purpose = db.Column(db.Text)
    applicant_sign = db.Column(db.String(100))
    director_sign = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Pending Director Approval')
    
    # Storing journey details as a JSON string
    journey_details = db.Column(db.Text) 
    
    user = db.relationship('User', foreign_keys=[user_id])

# === Role Permissions Model ===
class RolePermissions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), db.ForeignKey('role.name'), unique=True)
    permissions = db.Column(db.Text)

# === Task Model ===
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200), nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz))
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id], backref='tasks_assigned')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='tasks_received')

# === ProjectTask Model (for personal project tasks) ===
class ProjectTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200), nullable=False)
    deadline = db.Column(db.String(50), nullable=True)  # Store as string for simplicity
    is_completed = db.Column(db.Boolean, default=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz))
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    project = db.relationship('Project', backref='project_tasks')
    user = db.relationship('User', backref='personal_project_tasks')

# === Project Model (Integrated Version) ===
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100))
    group_name = db.Column(db.String(100)) # This will be used for display, actual groups are in Group model
    members = db.Column(db.Text)  # This will be used for display, actual members are in Group model
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    deadline = db.Column(db.String(20)) 
    budget_head = db.Column(db.String(100))
    created_by = db.Column(db.String(120))  # Email or username of team lead

# === Association Table for Many-to-Many Team <-> User ===
team_members = db.Table('team_members',
    db.Column('team_id', db.Integer, db.ForeignKey('team.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

# === Association Table for Many-to-Many Group <-> User ===
group_members = db.Table('group_members',
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

# === Announcement Model ===
class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz), onupdate=lambda: datetime.now(indian_tz))
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.String(20), default='Normal')  # Low, Normal, High, Urgent
    target_roles = db.Column(db.Text)  # JSON string of target role names
    target_users = db.Column(db.Text)  # JSON string of target user emails
    expires_at = db.Column(db.DateTime, nullable=True)
    
    author = db.relationship('User', backref=db.backref('announcements', lazy=True))

# === Team Model ===
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    members = db.relationship('User', secondary=team_members, backref=db.backref('teams', lazy='dynamic'))

# === Group Model (for project-specific groups) ===
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_type = db.Column(db.String(50))  # development, design, marketing, etc.
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    deadline = db.Column(db.String(20))  # Store deadline information
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    members = db.relationship('User', secondary=group_members, backref=db.backref('groups', lazy='dynamic'))
    
    # Relationship to Project
    project = db.relationship('Project', backref=db.backref('groups', lazy='dynamic'))

# ADD THESE NEW MODELS TO YOUR app.py FILE

# === Personal To-Do Models (For Multi-Dashboard) ===
class PersonalProject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('personal_projects', lazy=True))

class PersonalTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.String(50))
    completed = db.Column(db.Boolean, default=False, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('personal_project.id'), nullable=False)
    project = db.relationship('PersonalProject', backref=db.backref('tasks', lazy=True, cascade="all, delete-orphan"))
# new model for employee info
class EmployeeInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    dob = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    father_name = db.Column(db.String(100))
    father_contact = db.Column(db.String(20))
    mother_name = db.Column(db.String(100))
    mother_contact = db.Column(db.String(20))
    emergency_contact_name = db.Column(db.String(100))
    emergency_phone_number = db.Column(db.String(20))
    spouse_name = db.Column(db.String(100))
    spouse_contact_number = db.Column(db.String(20))
    phone_no = db.Column(db.String(20))
    address = db.Column(db.Text)

    
    # NEW FIELDS: These replace the old fields from the previous error.
    # I'll add all fields present in your new schema for completeness.
    office_branch = db.Column(db.String(50))
    employee_id = db.Column(db.String(50))  # Custom Employee ID field
    pdc = db.Column(db.String(255))
    aadhaar_card = db.Column(db.String(255))
    pan_card = db.Column(db.String(255))
    resume = db.Column(db.String(255))
    passport_photo = db.Column(db.String(255))
    tenth_certificate = db.Column(db.String(255))
    twelfth_certificate = db.Column(db.String(255))
    marital_status = db.Column(db.String(20))
    designation = db.Column(db.String(100))
    probation_from = db.Column(db.Date)
    probation_to = db.Column(db.Date)
    date_of_joining = db.Column(db.Date)
    confirmation_date = db.Column(db.Date)
    date_of_anniversary = db.Column(db.Date)
    probation_salary = db.Column(db.String(20))
    confirmation_salary = db.Column(db.String(20))
    post_graduation_marks = db.Column(db.String(10))
    post_graduation_certificate = db.Column(db.String(255))

    account_number = db.Column(db.String(50))
    actual_gross_salary = db.Column(db.Float)
    basic = db.Column(db.Float)
    hra = db.Column(db.Float)
    conveyance = db.Column(db.Float)
    vehicle_maintenance = db.Column(db.Float)
    special_allowance = db.Column(db.Float)
    provident_fund = db.Column(db.Float)
    esi = db.Column(db.Float)
    professional_tax = db.Column(db.Float)
    income_tax = db.Column(db.Float)
    advance = db.Column(db.Float)
    add_others = db.Column(db.Float)
    other_deductions = db.Column(db.Float)
    loss_of_pay = db.Column(db.Float)
    leave_availed = db.Column(db.Integer)
    balance_leaves = db.Column(db.Integer)
    no_of_lop_days = db.Column(db.Integer)
    total_days = db.Column(db.Integer)
    ndp = db.Column(db.Integer)
    total_leaves = db.Column(db.Integer)
    designation = db.Column(db.String(100))  # Custom designation field
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    # Separate Earnings fields (can be different from Actuals)
    earnings_basic = db.Column(db.Float)
    earnings_hra = db.Column(db.Float)
    earnings_conveyance = db.Column(db.Float)
    earnings_vehicle_maintenance = db.Column(db.Float)
    earnings_special_allowance = db.Column(db.Float)
    earnings_add_others = db.Column(db.Float)

    user = db.relationship('User', backref=db.backref('employee_info', uselist=False))

# === ConveyanceRequest Model (NEW) ===
class ConveyanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    claim_details = db.Column(db.Text)  # JSON string of claim details
    status_hr = db.Column(db.String(50), default='Pending') # Tracks HR view status
    status_accounts = db.Column(db.String(50), default='Pending') # Tracks Accounts view status
    request_date = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz))

    user = db.relationship('User', backref=db.backref('conveyance_requests', lazy=True))

# === Helper Functions ===
def is_managing_director(user_roles):
    """Check if user has Managing Director role (handles all variations)"""
    md_variations = ['Managing Director', 'managing director', 'MD', 'md', 'Managing director']
    return any(role in user_roles for role in md_variations)

# === Evaluation Models ===
class EvaluationReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_lead_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='Draft')  # Draft, Employee has Submitted, Team Lead has Reviewed, HR has Reviewed, Director has Reviewed, Completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz), onupdate=lambda: datetime.now(indian_tz))
    
    # Employee basic details (Page 1)
    name = db.Column(db.String(100))
    position = db.Column(db.String(100))
    contact_number = db.Column(db.String(20))
    email_id = db.Column(db.String(100))
    office_branch = db.Column(db.String(100))
    employee_id_str = db.Column(db.String(50))
    employment_status = db.Column(db.String(50))  # Internship, Probation, Confirmation
    status_duration = db.Column(db.String(100))  # Duration or date based on status
    salary = db.Column(db.Float)
    
    # Relationships
    employee = db.relationship('User', foreign_keys=[employee_id], backref='evaluation_reports_as_employee')
    team_lead = db.relationship('User', foreign_keys=[team_lead_id], backref='evaluation_reports_as_team_lead')

class EvaluationResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evaluation_report_id = db.Column(db.Integer, db.ForeignKey('evaluation_report.id'), nullable=False)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    evaluator_role = db.Column(db.String(50))  # Employee, Team Lead, HR, Director, Managing Director
    page_number = db.Column(db.Integer)  # 2, 3, 4, 5, 6
    
    # Self Evaluation (Page 2) - Employee fills
    attendance_score = db.Column(db.Integer)
    attendance_comments = db.Column(db.Text)
    discipline_score = db.Column(db.Integer)
    discipline_comments = db.Column(db.Text)
    knowledge_skills_score = db.Column(db.Integer)
    knowledge_skills_comments = db.Column(db.Text)
    quality_work_score = db.Column(db.Integer)
    quality_work_comments = db.Column(db.Text)
    teamwork_score = db.Column(db.Integer)
    teamwork_comments = db.Column(db.Text)
    work_consistency_score = db.Column(db.Integer)
    work_consistency_comments = db.Column(db.Text)
    thinking_process_score = db.Column(db.Integer)
    thinking_process_comments = db.Column(db.Text)
    communication_score = db.Column(db.Integer)
    communication_comments = db.Column(db.Text)
    initiative_score = db.Column(db.Integer)
    initiative_comments = db.Column(db.Text)
    motivation_score = db.Column(db.Integer)
    motivation_comments = db.Column(db.Text)
    creativity_score = db.Column(db.Integer)
    creativity_comments = db.Column(db.Text)
    honesty_score = db.Column(db.Integer)
    honesty_comments = db.Column(db.Text)
    overall_rating_score = db.Column(db.Integer)
    overall_rating_comments = db.Column(db.Text)
    
    # HR Evaluation (Page 4) - HR fills
    commitment_work_score = db.Column(db.Integer)
    commitment_work_comments = db.Column(db.Text)
    work_attitude_score = db.Column(db.Integer)
    work_attitude_comments = db.Column(db.Text)
    team_orientation_score = db.Column(db.Integer)
    team_orientation_comments = db.Column(db.Text)
    integrity_honesty_score = db.Column(db.Integer)
    integrity_honesty_comments = db.Column(db.Text)
    productivity_score = db.Column(db.Integer)
    productivity_comments = db.Column(db.Text)
    punctuality_score = db.Column(db.Integer)
    punctuality_comments = db.Column(db.Text)
    physical_disposition_score = db.Column(db.Integer)
    physical_disposition_comments = db.Column(db.Text)
    overall_hr_score = db.Column(db.Integer)
    overall_hr_comments = db.Column(db.Text)
    
    # Director/MD Evaluation (Pages 5 & 6) - Director/MD fills
    stability_score = db.Column(db.Integer)
    stability_comments = db.Column(db.Text)
    
    # MD Additional Fields (Page 6)
    further_action_hold = db.Column(db.Boolean, default=False)
    further_action_next_round = db.Column(db.Boolean, default=False)
    suitable_yes = db.Column(db.Boolean, default=False)
    suitable_no = db.Column(db.Boolean, default=False)
    project_assignment = db.Column(db.String(200))
    area_assignment = db.Column(db.String(100))  # SSEV, SSEV NATURO FARMS, etc.
    
    # Signature fields
    signature = db.Column(db.Text)
    evaluator_name = db.Column(db.String(100))
    evaluation_date = db.Column(db.Date)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz), onupdate=lambda: datetime.now(indian_tz))
    
    # Relationships
    evaluation_report = db.relationship('EvaluationReport', backref='evaluation_responses')
    evaluator = db.relationship('User', backref='evaluation_responses')

# ADD THIS DATABASE MODEL TO YOUR app.py

class AssetRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Indenter's section
    indenter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    indenter_name = db.Column(db.String(100))
    office_project_type = db.Column(db.String(50))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    team_lead_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reference_file_no = db.Column(db.String(100))
    purchase_type = db.Column(db.String(50))
    budget_head = db.Column(db.String(50))
    nature_of_expenditure = db.Column(db.String(50))
    gst_applicable = db.Column(db.String(50))
    item_details = db.Column(db.Text)  # Will store a JSON string of items
    request_date = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz))

    # Team Lead's section
    justification = db.Column(db.Text)
    
    # Procurement's section
    procurement_items = db.Column(db.Text) # JSON field for procurement table
    
    # Team Lead - final approval
    finalized_vendor = db.Column(db.String(100))
    approval_procurement = db.Column(db.String(100))
    
    # Director's section
    director_pi_approval = db.Column(db.Boolean, default=False)
    director_pd_approval = db.Column(db.Boolean, default=False)
    director_chairman_approval = db.Column(db.Boolean, default=False)
    director_comments = db.Column(db.Text)
    
    # MD's section
    pi_approval = db.Column(db.Boolean, default=False)
    pd_approval = db.Column(db.Boolean, default=False)
    chairman_approval = db.Column(db.Boolean, default=False)
    chairman_comments = db.Column(db.Text)
    md_approval = db.Column(db.Boolean, default=False)
    md_comments = db.Column(db.Text)
    
    # Accounts approval fields
    accounts_approval = db.Column(db.Boolean, default=False)
    accounts_comments = db.Column(db.Text)
    
    # Final delivery fields
    final_delivery_status = db.Column(db.String(100))
    final_delivery_comments = db.Column(db.Text)

    # Accounts Section
    budget_allocation = db.Column(db.String(100))
    budget_utilized = db.Column(db.String(100))
    available_balance = db.Column(db.String(100))
    funds_available = db.Column(db.Boolean)

    # Procurement Payment Section
    procurement_type = db.Column(db.String(50))
    account_no = db.Column(db.String(100))
    ifsc_code = db.Column(db.String(100))
    branch_name = db.Column(db.String(100))
    account_holder_name = db.Column(db.String(100))
    
    # Final Delivery
    handed_over_to = db.Column(db.String(100))
    received_on = db.Column(db.String(50))
    
    # Discount field
    discount_amount = db.Column(db.Float, default=0.0)
    
    # Accounts remarks
    accounts_remarks = db.Column(db.Text)

    # Workflow status
    status = db.Column(db.String(50), default='Pending TL Approval')

# === Vendor Model ===
class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    contact_no = db.Column(db.String(20))
    email = db.Column(db.String(100))
    gst_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(indian_tz))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    creator = db.relationship('User', backref='created_vendors')
# At the end of the file, inside `if __name__ == '__main__':`
# you might want to create the new table.
with app.app_context():
    db.create_all()
# === DB Initialization ===
with app.app_context():
    db.create_all()
    default_roles = ['Admin', 'CEO', 'CTO', 'CFO', 'Director', 'Manager', 'Employee', 'Accounts', 'Finance', 'Procurement']
    for role_name in default_roles:
        if not Role.query.filter_by(name=role_name).first():
            db.session.add(Role(name=role_name))
    db.session.commit()

# === Routes ===

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if User.query.filter_by(email=email).first():
            flash('❌ Email already registered.', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('❌ Passwords do not match.', 'error')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email, password=generate_password_hash(password), created_by_admin=False)
        db.session.add(new_user)
        db.session.commit()
        flash('✅ Registered successfully. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')
#leave routes
# app.py
#permissions routes



# === New Permission Endpoints ===
@app.route('/api/submit_permission_request', methods=['POST'])
def submit_permission_request():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

        user = User.query.filter_by(email=user_email).first()
        data = request.get_json()

        required_fields = ['spv_name', 'date', 'reason', 'time_out', 'time_in', 'going_to', 'applicant_sign', 'team_lead_id']
        if not all(key in data and data[key] for key in required_fields):
            return jsonify({'status': 'error', 'message': 'Missing required form data'}), 400

        new_permission_request = PermissionRequest(
            user_id=user.id,
            team_lead_id=data.get('team_lead_id'),
            spv_name=data.get('spv_name'),
            date=data.get('date'),
            applicant_name=user.name,
            reason=data.get('reason'),
            time_out=data.get('time_out'),
            time_in=data.get('time_in'),
            going_to=data.get('going_to'),
            applicant_sign=data.get('applicant_sign'),
            team_lead_sign=None, # Set to None initially
            hr_sign=None, # Set to None initially
            director_sign=None, # Set to None initially
            status='Pending'
        )

        db.session.add(new_permission_request)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Permission request submitted successfully!'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting permission request: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
# In app.py

@app.route('/api/submit_travel_request', methods=['POST'])
def submit_travel_request():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

        user = User.query.filter_by(email=user_email).first()
        data = request.get_json()

        # Gather form data
        company = data.get('company')
        date = data.get('date')
        purpose = data.get('purpose')
        applicant_sign = data.get('applicant_sign')
        journey_details = json.dumps(data.get('journey_details'))

        new_travel_request = TravelRequest(
            user_id=user.id,
            company=company,
            date=date,
            purpose=purpose,
            applicant_sign=applicant_sign,
            journey_details=journey_details,
            # Update the status to indicate it's also pending HR for information
            status='Pending Director Approval' 
        )

        db.session.add(new_travel_request)
        db.session.commit()

        # --- NEW LOGIC: Log or notify HR that a request has been submitted ---
        # Find all users with the 'HR' role
        hr_role = Role.query.filter_by(name='HR').first()
        if hr_role:
            hr_users = hr_role.users
            for hr_user in hr_users:
                # In a real app, you would send an email here.
                # For now, let's just print a message for demonstration.
                print(f"Notification: Travel request #{new_travel_request.id} has been submitted by {user.name}. Awaiting Director's approval.")
                print(f"This notification is for HR user: {hr_user.name} ({hr_user.email})")

        return jsonify({'status': 'success', 'message': 'Travel request submitted successfully!'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting travel request: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# In app.py

# In app.py

# In app.py

# In app.py

# In app.py


    

@app.route('/api/travel_request/<int:request_id>')
def get_travel_request(request_id):
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

    travel_request = TravelRequest.query.get(request_id)
    if not travel_request:
        return jsonify({'status': 'error', 'message': 'Travel request not found'}), 404

    user_roles = [r.name for r in user.roles]
    # Security check: Allow applicant, assigned director, or admin to access
    if travel_request.user_id != user.id and 'Director' not in user_roles and 'Admin' not in user_roles:
        return jsonify({'status': 'error', 'message': 'Unauthorized access to this request'}), 403

    request_data = {
        'id': travel_request.id,
        'request_type': 'Travel',
        'company': travel_request.company,
        'date': travel_request.date,
        'purpose': travel_request.purpose,
        'applicant_sign': travel_request.applicant_sign,
        'director_sign': travel_request.director_sign,
        'status': travel_request.status,
        'user_id': travel_request.user_id,
        'journey_details': json.loads(travel_request.journey_details) if travel_request.journey_details else []
    }
    return jsonify({'status': 'success', 'request': request_data})

# ... (existing code) ...

# In app.py

@app.route('/api/director/requests')
def get_director_requests():
    user_email = session.get('user')
    director_user = User.query.filter_by(email=user_email).first()
    if not director_user or 'Director' not in [r.name for r in director_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    # Check if user also has Team Lead role
    user_roles = [r.name for r in director_user.roles]
    is_team_lead = 'Team Lead' in user_roles

    # Fetch all leave requests that are pending Director Approval
    leave_requests = LeaveRequest.query.filter_by(status='Pending Director Approval').all()
    
    # Fetch all travel requests that are pending Director Approval
    travel_requests = TravelRequest.query.filter_by(status='Pending Director Approval').all()

    # 🟢 Corrected Logic: Fetch all permission requests that are pending Director Approval
    permission_requests = PermissionRequest.query.filter_by(status='Pending Director Approval').all()
    
    # If user is also a Team Lead, include requests assigned to them as Team Lead
    if is_team_lead:
        team_lead_leave_requests = LeaveRequest.query.filter_by(team_lead_id=director_user.id, status='Pending').all()
        team_lead_permission_requests = PermissionRequest.query.filter_by(team_lead_id=director_user.id, status='Pending').all()
        
        # Add team lead requests to the lists (avoid duplicates)
        leave_requests.extend([req for req in team_lead_leave_requests if req not in leave_requests])
        permission_requests.extend([req for req in team_lead_permission_requests if req not in permission_requests])
        
        # Also include requests that are pending HR approval (in case they need to track the full workflow)
        hr_team_lead_leave_requests = LeaveRequest.query.filter_by(team_lead_id=director_user.id, status='Pending HR Approval').all()
        hr_team_lead_permission_requests = PermissionRequest.query.filter_by(team_lead_id=director_user.id, status='Pending HR Approval').all()
        
        # Add HR team lead requests to the lists (avoid duplicates)
        leave_requests.extend([req for req in hr_team_lead_leave_requests if req not in leave_requests])
        permission_requests.extend([req for req in hr_team_lead_permission_requests if req not in permission_requests])
    
    requests_list = []
    
    for req in leave_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Leave',
            'applicant_name': req.applicant_name,
            'from_date': req.from_date,
            'to_date': req.to_date,
            'reason': req.reason,
            'status': req.status
        })

    for req in travel_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Travel',
            'applicant_name': req.user.name,
            'from_date': req.date,
            'to_date': req.date,
            'reason': req.purpose,
            'status': req.status
        })

    # 🟢 Corrected Logic: Append the permission requests to the list
    for req in permission_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Permission',
            'applicant_name': req.applicant_name,
            'from_date': req.date,
            'to_date': req.date,  # Use the same date for consistency
            'reason': req.reason,
            'status': req.status
        })
    
    # Sort requests by date for a cleaner view
    requests_list.sort(key=lambda x: x.get('from_date', ''), reverse=True)
    
    return jsonify({'status': 'success', 'requests': requests_list})

# ... (rest of the code) ...


@app.route('/api/approve_travel_request_director/<int:request_id>', methods=['POST'])
def approve_travel_request_director(request_id):
    user_email = session.get('user')
    director = User.query.filter_by(email=user_email).first()
    if not director or 'Director' not in [r.name for r in director.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    travel_request = TravelRequest.query.get(request_id)
    if not travel_request or travel_request.status != 'Pending Director Approval':
        return jsonify({'status': 'error', 'message': 'Not authorized to approve this request'}), 403

    try:
        data = request.get_json()
        action = data.get('action')
        travel_request.director_sign = data.get('director_sign')
        
        if action == 'approve':
            travel_request.status = 'Approved'
            message = 'Travel request approved successfully!'
        elif action == 'reject':
            travel_request.status = 'Rejected'
            message = 'Travel request has been rejected.'
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


# In app.py

@app.route('/api/permission_request/<int:request_id>')
def get_permission_request(request_id):
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

    permission_request = PermissionRequest.query.get(request_id)
    if not permission_request:
        return jsonify({'status': 'error', 'message': 'Permission request not found'}), 404

    user_roles = [r.name for r in user.roles]
    # Correct Security Check: Allow applicant, assigned team lead, HR, or Admin to access
    if (permission_request.user_id != user.id and 
        permission_request.team_lead_id != user.id and 
        'HR' not in user_roles and 
        'Admin' not in user_roles and
        'Director' not in user_roles):
        return jsonify({'status': 'error', 'message': 'Unauthorized access to this request'}), 403

    team_lead_name = "Not Assigned"
    if permission_request.team_lead:
        team_lead_name = permission_request.team_lead.name

    request_data = {
        'id': permission_request.id,
        'request_type': 'Permission',
        'spv_name': permission_request.spv_name,
        'date': permission_request.date,
        'applicant_name': permission_request.applicant_name,
        'reason': permission_request.reason,
        'time_out': permission_request.time_out,
        'time_in': permission_request.time_in,
        'going_to': permission_request.going_to,
        'applicant_sign': permission_request.applicant_sign,
        'team_lead_sign': permission_request.team_lead_sign,
        'hr_sign': permission_request.hr_sign,
        'director_sign': permission_request.director_sign,
        'status': permission_request.status,
        'user_id': permission_request.user_id,
        'team_lead_id': permission_request.team_lead_id,
        'team_lead_name': team_lead_name,
    }
    return jsonify({'status': 'success', 'request': request_data})
# In app.py
# In app.py
# In app.py
# In app.py, add this new endpoint.
# It's a good practice to name endpoints clearly to avoid confusion.

# In app.py

@app.route('/api/hr/finalized_all_requests')
def get_hr_finalized_all_requests():
    user_email = session.get('user')
    hr_user = User.query.filter_by(email=user_email).first()
    if not hr_user or 'HR' not in [r.name for r in hr_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    requests_list = []
    
    # Fetch all Leave Requests
    leave_requests = LeaveRequest.query.all()
    for req in leave_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Leave',
            'applicant_name': req.applicant_name,
            'from_date': req.from_date,
            'to_date': req.to_date,
            'reason': req.reason,
            'status': req.status
        })

    # Fetch all Permission Requests
    permission_requests = PermissionRequest.query.all()
    for req in permission_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Permission',
            'applicant_name': req.applicant_name,
            'from_date': req.date,
            'to_date': req.date,
            'reason': req.reason,
            'status': req.status
        })
    
    # 🟢 FIXED: Fetch all Travel Requests and append them to the list.
    travel_requests = TravelRequest.query.all()
    for req in travel_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Travel',
            'applicant_name': req.user.name,
            'from_date': req.date,
            'to_date': req.date,
            'reason': req.purpose,
            'status': req.status
        })

    # Sort the combined list by date
    requests_list.sort(key=lambda x: x.get('from_date', ''), reverse=True)
    
    return jsonify({'status': 'success', 'requests': requests_list})

# Next, update the old 'finalizedRequests' handler to point to this new endpoint.
# Replace the `handleHRView` function in your frontend with this:

# In app.py
@app.route('/api/hr/finalized_requests')
def get_hr_finalized_requests():
    user_email = session.get('user')
    hr_user = User.query.filter_by(email=user_email).first()
    if not hr_user or 'HR' not in [r.name for r in hr_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    # Fetch all finalized leave requests (Approved or Rejected)
    leave_requests = LeaveRequest.query.filter(
        LeaveRequest.status.in_(['Approved', 'Rejected'])
    ).all()

    # Fetch all finalized permission requests (Approved or Rejected)
    permission_requests = PermissionRequest.query.filter(
        PermissionRequest.status.in_(['Approved', 'Rejected'])
    ).all()

    requests_list = []
    
    # Add leave requests to the list
    for req in leave_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Leave',
            'applicant_name': req.applicant_name,
            'from_date': req.from_date,
            'to_date': req.to_date,
            'reason': req.reason,
            'status': req.status,
            'remarks': req.remarks
        })
    
    # 🟢 Add permission requests to the list
    for req in permission_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Permission',
            'applicant_name': req.applicant_name,
            'from_date': req.date,  # Permission forms use a single 'date' field
            'to_date': req.date,    # For consistency, use the same date for 'to_date'
            'reason': req.reason,
            'status': req.status
        })

    # You can sort the combined list by date if desired
    requests_list.sort(key=lambda x: x.get('from_date', ''), reverse=True)
        
    return jsonify({'status': 'success', 'requests': requests_list})
# def get_hr_finalized_requests():
#     # ... (remove this function as it's now redundant) ...
@app.route('/api/approve_permission_request_teamlead/<int:request_id>', methods=['POST'])
def approve_permission_request_teamlead(request_id):
    user_email = session.get('user')
    team_lead = User.query.filter_by(email=user_email).first()
    if not team_lead or 'Team Lead' not in [r.name for r in team_lead.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    permission_request = PermissionRequest.query.get(request_id)
    if not permission_request or permission_request.team_lead_id != team_lead.id:
        return jsonify({'status': 'error', 'message': 'Not authorized to approve this request'}), 403
    
    # Check if user also has Director role and request is pending Director approval
    user_roles = [r.name for r in team_lead.roles]
    is_director = 'Director' in user_roles
    
    # Allow approval if request is pending (Team Lead role) or pending Director approval (Director role)
    if permission_request.status not in ['Pending', 'Pending Director Approval']:
        return jsonify({'status': 'error', 'message': 'Request is not in a state that can be approved by Team Lead'}), 403
    
    # If request is pending Director approval and user is not a Director, deny access
    if permission_request.status == 'Pending Director Approval' and not is_director:
        return jsonify({'status': 'error', 'message': 'Request requires Director approval'}), 403

    try:
        data = request.get_json()
        action = data.get('action')
        permission_request.team_lead_sign = data.get('approver_sign')

        if action == 'approve':
            if permission_request.status == 'Pending':
                permission_request.status = 'Pending HR Approval'
                message = 'Permission request approved and forwarded to HR!'
            elif permission_request.status == 'Pending Director Approval':
                permission_request.status = 'Approved'
                message = 'Permission request approved by Director.'
            else:
                return jsonify({'status': 'error', 'message': 'Invalid request status for approval'}), 400
        elif action == 'reject':
            permission_request.status = 'Rejected'
            message = 'Permission request has been rejected.'
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
# ... (other code) ...
@app.route('/api/approve_permission_request_hr/<int:request_id>', methods=['POST'])
def approve_permission_request_hr(request_id):
    user_email = session.get('user')
    hr_user = User.query.filter_by(email=user_email).first()
    if not hr_user or 'HR' not in [r.name for r in hr_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    permission_request = PermissionRequest.query.get(request_id)
    if not permission_request or permission_request.status != 'Pending HR Approval':
        return jsonify({'status': 'error', 'message': 'Not authorized to approve this request'}), 403

    try:
        data = request.get_json()
        action = data.get('action')
        permission_request.hr_sign = data.get('approver_sign')
        
        if action == 'approve':
            permission_request.status = 'Pending Director Approval' # MODIFIED
            message = 'Permission request approved by HR and forwarded to Director!'
        elif action == 'reject':
            permission_request.status = 'Rejected'
            message = 'Permission request has been rejected.'
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/approve_permission_request_director/<int:request_id>', methods=['POST'])
def approve_permission_request_director(request_id):
    user_email = session.get('user')
    director_user = User.query.filter_by(email=user_email).first()
    if not director_user or 'Director' not in [r.name for r in director_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    permission_request = PermissionRequest.query.get(request_id)
    if not permission_request or permission_request.status != 'Pending Director Approval':
        return jsonify({'status': 'error', 'message': 'Not authorized to approve this request'}), 403

    try:
        data = request.get_json()
        action = data.get('action')
        permission_request.director_sign = data.get('approver_sign')
        
        if action == 'approve':
            permission_request.status = 'Approved'
            message = 'Permission request approved successfully!'
        elif action == 'reject':
            permission_request.status = 'Rejected'
            message = 'Permission request has been rejected.'
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/submit_leave_request', methods=['POST'])
def submit_leave_request():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        data = request.get_json()
        
        # Only require the most essential fields
        required_fields = ['from_date', 'to_date', 'reason', 'team_lead_id']

        # Check for missing required fields
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return jsonify({'status': 'error', 'message': f'Missing required form data: {", ".join(missing_fields)}'}), 400

        employee_info = EmployeeInfo.query.filter_by(user_id=user.id).first()
        
        new_leave_request = LeaveRequest(
            user_id=user.id,
            team_lead_id=data.get('team_lead_id'),
            spv_name=data.get('spv_name', ''),
            department=data.get('department', ''),
            emp_no=data.get('emp_no', ''),
            contact_details=data.get('contact_details', ''),
            applicant_name=user.name,
            total_leaves=data.get('total_leaves', 0),
            leave_availed=data.get('leave_availed', 0),
            balance_leaves=data.get('balance_leaves', 0),
            from_date=data.get('from_date'),
            from_time=data.get('from_time', ''),
            to_date=data.get('to_date'),
            to_time=data.get('to_time', ''),
            reason=data.get('reason'),
            applicant_sign=data.get('applicant_sign', ''),
            applicant_sign_date=data.get('applicant_sign_date', ''),
            status='Pending'
        )
        
        db.session.add(new_leave_request)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Leave request submitted successfully!', 'request_id': new_leave_request.id}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error submitting leave request: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/user_leave_info')
def api_user_leave_info():
    """Get leave information for the current logged-in user from EmployeeInfo database"""
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        # Get employee info from EmployeeInfo table (same as salary section)
        employee_info = EmployeeInfo.query.filter_by(user_id=user.id).first()
        if employee_info:
            # Get leave data from EmployeeInfo table (same as salary section)
            total_leaves = employee_info.total_leaves or 0

            # Calculate leaves availed from leave requests
            leave_requests = LeaveRequest.query.filter_by(user_id=user.id).all()
            leaves_availed = 0
            pending_requests = 0
            approved_requests = 0

            for leave in leave_requests:
                if leave.status == 'Approved':
                    # Calculate days between from_date and to_date
                    try:
                        from datetime import datetime
                        from_date = datetime.strptime(leave.from_date, "%Y-%m-%d")
                        to_date = datetime.strptime(leave.to_date, "%Y-%m-%d")
                        days_diff = (to_date - from_date).days + 1
                        leaves_availed += days_diff
                        approved_requests += 1
                    except:
                        leaves_availed += 1  # Default to 1 day if date parsing fails
                        approved_requests += 1

            leaves_balance = total_leaves - leaves_availed

            return jsonify({
                'status': 'success',
                'leaves': {
                    'total_leaves': total_leaves,
                    'leaves_availed': leaves_availed,
                    'leaves_balance': leaves_balance,
                    'pending_requests': pending_requests,
                    'approved_requests': approved_requests
                }
            })
        else:
            # Fallback if no employee info found
            return jsonify({
                'status': 'success',
                'leaves': {
                    'total_leaves': 0,
                    'leaves_availed': 0,
                    'leaves_balance': 0,
                    'pending_requests': 0,
                    'approved_requests': 0
                }
            })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/user_permissions_count')
def api_user_permissions_count():
    """Get approved permissions count for the current logged-in user"""
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        # Count approved permissions for the current year
        from datetime import datetime
        current_year = datetime.now().year
        
        # Count approved permissions from permission_request table
        approved_permissions = PermissionRequest.query.filter(
            PermissionRequest.user_id == user.id,
            PermissionRequest.status == 'Approved',
            db.extract('year', PermissionRequest.date) == current_year
        ).count()

        return jsonify({
            'status': 'success',
            'approved_permissions': approved_permissions
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ===== DATABASE MIGRATIONS =====
@app.route('/api/migrate_database', methods=['POST'])
def migrate_database():
    """Consolidated database migration endpoint"""
    try:
        migration_results = []
        
        # Migration 1: Add is_deleted column
        try:
            db.session.execute(db.text('ALTER TABLE employee_info ADD COLUMN is_deleted BOOLEAN DEFAULT 0 NOT NULL'))
            db.session.execute(db.text('UPDATE employee_info SET is_deleted = 0 WHERE is_deleted IS NULL'))
            migration_results.append("✓ Added is_deleted column")
        except Exception as e:
            if "duplicate column name" in str(e) or "already exists" in str(e):
                migration_results.append("✓ is_deleted column already exists")
            else:
                migration_results.append(f"❌ Error adding is_deleted: {e}")
        
        # Migration 2: Add vehicle maintenance and related fields
        vehicle_fields = [
            'vehicle_maintenance REAL',
            'add_others REAL', 
            'other_deductions REAL',
            'loss_of_pay REAL',
            'leave_availed INTEGER',
            'balance_leaves INTEGER',
            'no_of_lop_days INTEGER',
            'ndp INTEGER'
        ]
        
        for field in vehicle_fields:
            field_name = field.split()[0]
            try:
                db.session.execute(db.text(f'ALTER TABLE employee_info ADD COLUMN {field}'))
                migration_results.append(f"✓ Added {field_name} column")
            except Exception as e:
                if "duplicate column name" in str(e) or "already exists" in str(e):
                    migration_results.append(f"✓ {field_name} column already exists")
                else:
                    migration_results.append(f"❌ Error adding {field_name}: {e}")
        
        # Migration 3: Add Earnings fields
        earnings_fields = [
            'earnings_basic FLOAT',
            'earnings_hra FLOAT',
            'earnings_conveyance FLOAT',
            'earnings_vehicle_maintenance FLOAT',
            'earnings_special_allowance FLOAT',
            'earnings_add_others FLOAT'
        ]
        
        for field in earnings_fields:
            field_name = field.split()[0]
            try:
                db.session.execute(db.text(f'ALTER TABLE employee_info ADD COLUMN {field}'))
                migration_results.append(f"✓ Added {field_name} field")
            except Exception as e:
                if "duplicate column name" in str(e) or "already exists" in str(e):
                    migration_results.append(f"✓ {field_name} field already exists")
                else:
                    migration_results.append(f"❌ Error adding {field_name}: {e}")
        
        # Initialize Earnings fields with current values
        try:
            employees = EmployeeInfo.query.all()
            for emp in employees:
                if hasattr(emp, 'earnings_basic') and emp.earnings_basic is None:
                    emp.earnings_basic = emp.basic or 0
                if hasattr(emp, 'earnings_hra') and emp.earnings_hra is None:
                    emp.earnings_hra = emp.hra or 0
                if hasattr(emp, 'earnings_conveyance') and emp.earnings_conveyance is None:
                    emp.earnings_conveyance = emp.conveyance or 0
                if hasattr(emp, 'earnings_vehicle_maintenance') and emp.earnings_vehicle_maintenance is None:
                    emp.earnings_vehicle_maintenance = emp.vehicle_maintenance or 0
                if hasattr(emp, 'earnings_special_allowance') and emp.earnings_special_allowance is None:
                    emp.earnings_special_allowance = emp.special_allowance or 0
                if hasattr(emp, 'earnings_add_others') and emp.earnings_add_others is None:
                    emp.earnings_add_others = emp.add_others or 0
            
            db.session.commit()
            migration_results.append(f"✓ Initialized Earnings fields for {len(employees)} employees")
        except Exception as e:
            migration_results.append(f"❌ Error initializing Earnings fields: {e}")
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Database migration completed',
            'results': migration_results
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error', 
            'message': f'Migration failed: {str(e)}',
            'results': migration_results if 'migration_results' in locals() else []
        }), 500

@app.route('/api/migration_status')
def migration_status():
    """Check the status of database migrations"""
    try:
        status_info = []
        
        # Check if is_deleted column exists
        try:
            result = db.session.execute(db.text("PRAGMA table_info(employee_info)"))
            columns = [row[1] for row in result.fetchall()]
            status_info.append({
                'column': 'is_deleted',
                'exists': 'is_deleted' in columns,
                'description': 'Soft delete functionality'
            })
        except Exception as e:
            status_info.append({
                'column': 'is_deleted',
                'exists': False,
                'error': str(e)
            })
        
        # Check vehicle maintenance fields
        vehicle_fields = ['vehicle_maintenance', 'add_others', 'other_deductions', 'loss_of_pay', 'leave_availed', 'balance_leaves', 'no_of_lop_days', 'ndp']
        for field in vehicle_fields:
            try:
                result = db.session.execute(db.text("PRAGMA table_info(employee_info)"))
                columns = [row[1] for row in result.fetchall()]
                status_info.append({
                    'column': field,
                    'exists': field in columns,
                    'description': 'Vehicle maintenance and related fields'
                })
            except Exception as e:
                status_info.append({
                    'column': field,
                    'exists': False,
                    'error': str(e)
                })
        
        # Check earnings fields
        earnings_fields = ['earnings_basic', 'earnings_hra', 'earnings_conveyance', 'earnings_vehicle_maintenance', 'earnings_special_allowance', 'earnings_add_others']
        for field in earnings_fields:
            try:
                result = db.session.execute(db.text("PRAGMA table_info(employee_info)"))
                columns = [row[1] for row in result.fetchall()]
                status_info.append({
                    'column': field,
                    'exists': field in columns,
                    'description': 'Earnings fields for salary management'
                })
            except Exception as e:
                status_info.append({
                    'column': field,
                    'exists': False,
                    'error': str(e)
                })
        
        return jsonify({
            'status': 'success',
            'migration_status': status_info,
            'total_columns': len(status_info),
            'existing_columns': len([col for col in status_info if col.get('exists', False)])
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to check migration status: {str(e)}'
        }), 500

# ... (rest of the code) ...
# In app.py
@app.route('/api/leave_request/<int:request_id>')
def get_leave_request(request_id):
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

    leave_request = LeaveRequest.query.get(request_id)
    if not leave_request:
        return jsonify({'status': 'error', 'message': 'Leave request not found'}), 404

    # Correct Security check: Allow the applicant, the assigned team lead, HR, or Director to access the request.
    user_roles = [r.name for r in user.roles]
    if leave_request.user_id != user.id and leave_request.team_lead_id != user.id and 'HR' not in user_roles and 'Director' not in user_roles:
        return jsonify({'status': 'error', 'message': 'Unauthorized access to this request'}), 403

    # New code to get the team lead's name
    team_lead_name = "Not Assigned"
    if leave_request.team_lead:
        team_lead_name = leave_request.team_lead.name

    # Prepare data for JSON response
    request_data = {
        'id': leave_request.id,
        'spv_name': leave_request.spv_name,
        'department': leave_request.department,
        'emp_no': leave_request.emp_no,
        'contact_details': leave_request.contact_details,
        'applicant_name': leave_request.applicant_name,
        'total_leaves': leave_request.total_leaves,
        'leave_availed': leave_request.leave_availed,
        'balance_leaves': leave_request.balance_leaves,
        'from_date': leave_request.from_date,
        'from_time': leave_request.from_time,
        'to_date': leave_request.to_date,
        'to_time': leave_request.to_time,
        'reason': leave_request.reason,
        'applicant_sign': leave_request.applicant_sign,
        'applicant_sign_date': leave_request.applicant_sign_date,
        'reporting_authority_sign': leave_request.reporting_authority_sign,
        'reporting_authority_date': leave_request.reporting_authority_date,
        'hr_sign': leave_request.hr_sign,
        'hr_date': leave_request.hr_date,
        'director_sign': leave_request.director_sign,
        'director_date': leave_request.director_date,
        'remarks': leave_request.remarks,
        'status': leave_request.status,
        'user_id': leave_request.user_id,
        'team_lead_id': leave_request.team_lead_id,
        'team_lead_name': team_lead_name
    }
    return jsonify({'status': 'success', 'request': request_data})
   # In app.py

# In app.py

@app.route('/api/approve_leave_request_teamlead/<int:request_id>', methods=['POST'])
def approve_leave_request_teamlead(request_id):
    user_email = session.get('user')
    team_lead = User.query.filter_by(email=user_email).first()
    if not team_lead or 'Team Lead' not in [r.name for r in team_lead.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    leave_request = LeaveRequest.query.get(request_id)
    if not leave_request or leave_request.team_lead_id != team_lead.id:
        return jsonify({'status': 'error', 'message': 'Not authorized to approve this request'}), 403
    
    # Check if user also has Director role and request is pending Director approval
    user_roles = [r.name for r in team_lead.roles]
    is_director = 'Director' in user_roles
    
    # Allow approval if request is pending (Team Lead role) or pending Director approval (Director role)
    if leave_request.status not in ['Pending', 'Pending Director Approval']:
        return jsonify({'status': 'error', 'message': 'Request is not in a state that can be approved by Team Lead'}), 403
    
    # If request is pending Director approval and user is not a Director, deny access
    if leave_request.status == 'Pending Director Approval' and not is_director:
        return jsonify({'status': 'error', 'message': 'Request requires Director approval'}), 403

    try:
        data = request.get_json()
        action = data.get('action')
        leave_request.reporting_authority_sign = data.get('reporting_authority_sign')
        leave_request.reporting_authority_date = data.get('reporting_authority_date')
        leave_request.remarks = data.get('remarks')
        
        if action == 'approve':
            if leave_request.status == 'Pending':
                leave_request.status = 'Pending HR Approval'
                message = 'Leave request approved and forwarded to HR.'
            elif leave_request.status == 'Pending Director Approval':
                leave_request.status = 'Approved'
                message = 'Leave request approved by Director.'
            else:
                return jsonify({'status': 'error', 'message': 'Invalid request status for approval'}), 400
        elif action == 'reject':
            leave_request.status = 'Rejected'
            message = 'Leave request has been rejected.'
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/approve_leave_request_hr/<int:request_id>', methods=['POST'])
def approve_leave_request_hr(request_id):
    user_email = session.get('user')
    hr_user = User.query.filter_by(email=user_email).first()
    
    if not hr_user or 'HR' not in [r.name for r in hr_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    leave_request = LeaveRequest.query.get(request_id)
    
    if not leave_request or leave_request.status != 'Pending HR Approval':
        return jsonify({'status': 'error', 'message': 'Not authorized to approve this request'}), 403

    try:
        data = request.get_json()
        action = data.get('action')
        leave_request.hr_sign = data.get('hr_sign')
        leave_request.hr_date = data.get('hr_date')
        
        if action == 'approve':
            leave_request.status = 'Pending Director Approval'
            message = 'Leave request approved by HR and forwarded to Director.'
        elif action == 'reject':
            leave_request.status = 'Rejected'
            message = 'Leave request has been rejected.'
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
# ... (Existing code) ...
@app.route('/api/approve_leave_request_director/<int:request_id>', methods=['POST'])
def approve_leave_request_director(request_id):
    user_email = session.get('user')
    director_user = User.query.filter_by(email=user_email).first()
    
    if not director_user or 'Director' not in [r.name for r in director_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    leave_request = LeaveRequest.query.get(request_id)
    
    if not leave_request or leave_request.status != 'Pending Director Approval':
        return jsonify({'status': 'error', 'message': 'Not authorized to approve this request'}), 403

    try:
        data = request.get_json()
        action = data.get('action')
        leave_request.director_sign = data.get('director_sign')
        leave_request.director_date = data.get('director_date')
        leave_request.remarks = data.get('remarks')

        if action == 'approve':
            leave_request.status = 'Approved'
            message = 'Leave request finalized and approved.'
        elif action == 'reject':
            leave_request.status = 'Rejected'
            message = 'Leave request has been rejected.'
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
            
        db.session.commit()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/approve_leave_request/<int:request_id>', methods=['POST'])
def approve_leave_request(request_id):
    user_email = session.get('user')
    team_lead = User.query.filter_by(email=user_email).first()

    # Security check: Make sure the user is a team lead
    if not team_lead or 'Team Lead' not in [r.name for r in team_lead.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    leave_request = LeaveRequest.query.get(request_id)
    if not leave_request:
        return jsonify({'status': 'error', 'message': 'Leave request not found'}), 404

    # Security check: Ensure the team lead is assigned to this request
    if leave_request.team_lead_id != team_lead.id:
        return jsonify({'status': 'error', 'message': 'Not authorized to approve this request'}), 403

    try:
        data = request.get_json()
        leave_request.reporting_authority_sign = data.get('reporting_authority_sign')
        leave_request.reporting_authority_date = data.get('reporting_authority_date')
        leave_request.status = 'Approved by Team Lead' # Update status
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Leave request approved and forwarded to Director'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/teamlead/requests')
def get_teamlead_requests():
    user_email = session.get('user')
    team_lead = User.query.filter_by(email=user_email).first()
    if not team_lead or 'Team Lead' not in [r.name for r in team_lead.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    # Check if user also has Director role
    user_roles = [r.name for r in team_lead.roles]
    is_director = 'Director' in user_roles

    # Get requests assigned to this team lead
    leave_requests = LeaveRequest.query.filter_by(team_lead_id=team_lead.id, status='Pending').all()
    permission_requests = PermissionRequest.query.filter_by(team_lead_id=team_lead.id, status='Pending').all()
    
    # If user is also a Director, include requests pending Director approval
    if is_director:
        director_leave_requests = LeaveRequest.query.filter_by(status='Pending Director Approval').all()
        director_permission_requests = PermissionRequest.query.filter_by(status='Pending Director Approval').all()
        
        # Add director requests to the lists (avoid duplicates)
        leave_requests.extend([req for req in director_leave_requests if req not in leave_requests])
        permission_requests.extend([req for req in director_permission_requests if req not in permission_requests])
        
        # Also include requests that are pending HR approval (in case they need to track the full workflow)
        hr_leave_requests = LeaveRequest.query.filter_by(status='Pending HR Approval').all()
        hr_permission_requests = PermissionRequest.query.filter_by(status='Pending HR Approval').all()
        
        # Add HR requests to the lists (avoid duplicates)
        leave_requests.extend([req for req in hr_leave_requests if req not in leave_requests])
        permission_requests.extend([req for req in hr_permission_requests if req not in permission_requests])

    requests_list = []
    for req in leave_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Leave',
            'applicant_name': req.applicant_name,
            'from_date': req.from_date,
            'to_date': req.to_date,
            'reason': req.reason,
            'status': req.status
        })
    for req in permission_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Permission',
            'applicant_name': req.applicant_name,
            'from_date': req.date,
            'to_date': req.date,
            'reason': req.reason,
            'status': req.status
        })
    return jsonify({'status': 'success', 'requests': requests_list})
# A new endpoint for 'View your requests' to avoid confusion with the old one
# MODIFIED function in app.py

# MODIFIED function in app.py
# MODIFIED function in app.py
@app.route('/api/my_requests')
def get_my_requests():
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
    leave_requests = LeaveRequest.query.filter_by(user_id=user.id).all()
    permission_requests = PermissionRequest.query.filter_by(user_id=user.id).all()
    travel_requests = TravelRequest.query.filter_by(user_id=user.id).all()
    conveyance_requests = ConveyanceRequest.query.filter_by(user_id=user.id).all() # NEW
    
    requests_list = []
    for req in leave_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Leave',
            'applicant_name': req.applicant_name,
            'from_date': req.from_date,
            'to_date': req.to_date,
            'reason': req.reason,
            'status': req.status
        })
    for req in permission_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Permission',
            'applicant_name': req.applicant_name,
            'from_date': req.date,
            'to_date': req.date,
            'reason': req.reason,
            'status': req.status
        })
    for req in travel_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Travel',
            'applicant_name': req.user.name,
            'from_date': req.date,
            'to_date': req.date,
            'reason': req.purpose,
            'status': req.status
        })
    for req in conveyance_requests: # NEW
        requests_list.append({
            'id': req.id,
            'request_type': 'Conveyance',
            'applicant_name': req.user.name,
            'from_date': req.request_date.strftime('%Y-%m-%d'),
            'to_date': req.request_date.strftime('%Y-%m-%d'),
            'reason': 'Local Conveyance Claim',
            'status': f"HR: {req.status_hr} / Accounts: {req.status_accounts}" # Custom status for display
        })
        
    requests_list.sort(key=lambda x: x.get('from_date', ''), reverse=True)
    
    return jsonify({'status': 'success', 'requests': requests_list})

@app.route('/api/director/all_requests')
def get_director_all_requests():
    user_email = session.get('user')
    director_user = User.query.filter_by(email=user_email).first()
    if not director_user or 'Director' not in [r.name for r in director_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    # Fetch all leave requests with the status 'Approved' or 'Rejected'
    leave_requests = LeaveRequest.query.filter(LeaveRequest.status.in_(['Approved', 'Rejected'])).all()
    # Fetch all travel requests with the status 'Approved' or 'Rejected'
    travel_requests = TravelRequest.query.filter(TravelRequest.status.in_(['Approved', 'Rejected'])).all()
    
    requests_list = []
    
    for req in leave_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Leave',
            'applicant_name': req.applicant_name,
            'from_date': req.from_date,
            'to_date': req.to_date,
            'reason': req.reason,
            'status': req.status
        })

    for req in travel_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Travel',
            'applicant_name': req.user.name,
            'from_date': req.date,
            'to_date': req.date,
            'reason': req.purpose,
            'status': req.status
        })
    
    # Sort requests by date for a cleaner view
    requests_list.sort(key=lambda x: x.get('from_date', ''), reverse=True)
    
    return jsonify({'status': 'success', 'requests': requests_list})
# In app.py

@app.route('/api/hr/requests')
def get_hr_requests():
    user_email = session.get('user')
    hr_user = User.query.filter_by(email=user_email).first()
    if not hr_user or 'HR' not in [r.name for r in hr_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    # Fetch all leave requests with the status 'Pending HR Approval'
    leave_requests = LeaveRequest.query.filter_by(status='Pending HR Approval').all()
    # Fetch all permission requests with the status 'Pending HR Approval'
    permission_requests = PermissionRequest.query.filter_by(status='Pending HR Approval').all()

    requests_list = []
    for req in leave_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Leave',
            'applicant_name': req.applicant_name,
            'from_date': req.from_date,
            'to_date': req.to_date,
            'reason': req.reason,
            'status': req.status
        })

    # 🟢 Corrected Logic: Add permission requests to the list
    for req in permission_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Permission',
            'applicant_name': req.applicant_name,
            'from_date': req.date,
            'to_date': req.date,  # Permission slips are for a single day, so use the same date
            'reason': req.reason,
            'status': req.status
        })
        
    return jsonify({'status': 'success', 'requests': requests_list})



# === New Conveyance Endpoints ===

@app.route('/api/submit_conveyance_claim', methods=['POST'])
def submit_conveyance_claim():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

        user = User.query.filter_by(email=user_email).first()
        data = request.get_json()

        claim_details = json.dumps(data.get('claim_details'))

        new_conveyance_request = ConveyanceRequest(
            user_id=user.id,
            claim_details=claim_details,
            status_hr='Pending',
            status_accounts='Pending'
        )

        db.session.add(new_conveyance_request)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Conveyance claim submitted successfully!'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting conveyance claim: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/conveyance_request/<int:request_id>')
def get_conveyance_request(request_id):
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

    conveyance_request = ConveyanceRequest.query.get(request_id)
    if not conveyance_request:
        return jsonify({'status': 'error', 'message': 'Conveyance request not found'}), 404

    user_roles = [r.name for r in user.roles]
    # Security check: Allow applicant, HR, Accounts or Admin to access
    if conveyance_request.user_id != user.id and 'HR' not in user_roles and 'Accounts' not in user_roles and 'Admin' not in user_roles:
        return jsonify({'status': 'error', 'message': 'Unauthorized access to this request'}), 403

    request_data = {
        'id': conveyance_request.id,
        'request_type': 'Conveyance',
        'applicant_name': conveyance_request.user.name,
        'request_date': conveyance_request.request_date.strftime('%Y-%m-%d'),
        'claim_details': json.loads(conveyance_request.claim_details) if conveyance_request.claim_details else [],
        'status_hr': conveyance_request.status_hr,
        'status_accounts': conveyance_request.status_accounts
    }
    return jsonify({'status': 'success', 'request': request_data})

@app.route('/api/mark_conveyance_claim_seen/<int:request_id>', methods=['POST'])
def mark_conveyance_claim_seen(request_id):
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
    
    conveyance_request = ConveyanceRequest.query.get(request_id)
    if not conveyance_request:
        return jsonify({'status': 'error', 'message': 'Conveyance request not found'}), 404

    roles = [r.name for r in user.roles]
    if 'HR' in roles:
        conveyance_request.status_hr = 'Seen'
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Claim marked as seen by HR.'})
    elif 'Accounts' in roles:
        conveyance_request.status_accounts = 'Seen'
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Claim marked as seen by Accounts.'})
    else:
        return jsonify({'status': 'error', 'message': 'Unauthorized to mark as seen.'}), 403

# New endpoint for HR to view conveyance claims
@app.route('/api/hr/conveyance_requests')
def get_hr_conveyance_requests():
    user_email = session.get('user')
    hr_user = User.query.filter_by(email=user_email).first()
    if not hr_user or 'HR' not in [r.name for r in hr_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    requests = ConveyanceRequest.query.filter_by(status_hr='Pending').all()
    requests_list = []
    for req in requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Conveyance',
            'applicant_name': req.user.name,
            'from_date': req.request_date.strftime('%Y-%m-%d'),
            'to_date': req.request_date.strftime('%Y-%m-%d'),
            'reason': 'Local Conveyance Claim',
            'status': req.status_hr
        })
    return jsonify({'status': 'success', 'requests': requests_list})

# New endpoint for HR to view seen conveyance claims
@app.route('/api/hr/seen_conveyance_requests')
def get_hr_seen_conveyance_requests():
    user_email = session.get('user')
    hr_user = User.query.filter_by(email=user_email).first()
    if not hr_user or 'HR' not in [r.name for r in hr_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    requests = ConveyanceRequest.query.filter_by(status_hr='Seen').all()
    requests_list = []
    for req in requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Conveyance',
            'applicant_name': req.user.name,
            'from_date': req.request_date.strftime('%Y-%m-%d'),
            'to_date': req.request_date.strftime('%Y-%m-%d'),
            'reason': 'Local Conveyance Claim',
            'status': req.status_hr
        })
    return jsonify({'status': 'success', 'requests': requests_list})

# New endpoint for Accounts to view conveyance claims
@app.route('/api/accounts/conveyance_requests')
def get_accounts_conveyance_requests():
    user_email = session.get('user')
    accounts_user = User.query.filter_by(email=user_email).first()
    if not accounts_user or 'Accounts' not in [r.name for r in accounts_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    requests = ConveyanceRequest.query.filter_by(status_accounts='Pending').all()
    requests_list = []
    for req in requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Conveyance',
            'applicant_name': req.user.name,
            'from_date': req.request_date.strftime('%Y-%m-%d'),
            'to_date': req.request_date.strftime('%Y-%m-%d'),
            'reason': 'Local Conveyance Claim',
            'status': req.status_accounts
        })
    return jsonify({'status': 'success', 'requests': requests_list})
@app.route('/api/teamlead/all_requests')
def get_teamlead_all_requests():
    user_email = session.get('user')
    team_lead = User.query.filter_by(email=user_email).first()
    if not team_lead or 'Team Lead' not in [r.name for r in team_lead.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    # Fetch all leave requests for this team lead, regardless of status
    leave_requests = LeaveRequest.query.filter_by(team_lead_id=team_lead.id).all()
    # Fetch all permission requests for this team lead, regardless of status
    permission_requests = PermissionRequest.query.filter_by(team_lead_id=team_lead.id).all()
    # Fetch all conveyance requests for this team lead, regardless of status
    conveyance_requests = ConveyanceRequest.query.filter_by(user_id=team_lead.id).all() # Note: Conveyance doesn't have a team_lead_id directly, assuming team leads manage their own claims

    requests_list = []
    
    for req in leave_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Leave',
            'applicant_name': req.applicant_name,
            'from_date': req.from_date,
            'to_date': req.to_date,
            'reason': req.reason,
            'status': req.status
        })

    for req in permission_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Permission',
            'applicant_name': req.applicant_name,
            'from_date': req.date,
            'to_date': req.date,
            'reason': req.reason,
            'status': req.status
        })

    # Assuming team leads can also view their own conveyance claims
    for req in conveyance_requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Conveyance',
            'applicant_name': req.user.name,
            'from_date': req.request_date.strftime('%Y-%m-%d'),
            'to_date': req.request_date.strftime('%Y-%m-%d'),
            'reason': 'Local Conveyance Claim',
            'status': f"HR: {req.status_hr} / Accounts: {req.status_accounts}"
        })
    
    # Sort requests by date for a cleaner view
    requests_list.sort(key=lambda x: x.get('from_date', ''), reverse=True)
    
    return jsonify({'status': 'success', 'requests': requests_list})
# New endpoint for Accounts to view seen conveyance claims
@app.route('/api/accounts/seen_conveyance_requests')
def get_accounts_seen_conveyance_requests():
    user_email = session.get('user')
    accounts_user = User.query.filter_by(email=user_email).first()
    if not accounts_user or 'Accounts' not in [r.name for r in accounts_user.roles]:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

    requests = ConveyanceRequest.query.filter_by(status_accounts='Seen').all()
    requests_list = []
    for req in requests:
        requests_list.append({
            'id': req.id,
            'request_type': 'Conveyance',
            'applicant_name': req.user.name,
            'from_date': req.request_date.strftime('%Y-%m-%d'),
            'to_date': req.request_date.strftime('%Y-%m-%d'),
            'reason': 'Local Conveyance Claim',
            'status': req.status_accounts
        })
    return jsonify({'status': 'success', 'requests': requests_list})

# ... (rest of your app.py code) ...
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user'] = user.email
            session['roles'] = [role.name for role in user.roles]
            flash(f"✅ Welcome back, {user.name}!", 'success')

            # Correct logic:
            # Check if 'Admin' role is present in the session roles list
            if 'Admin' in session.get('roles', []):
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('multi_dashboard'))

        flash('❌ Invalid email or password.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        flash('❌ Session expired. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    # Correct logic:
    # Only allow 'Admin' to view this page. Redirect others.
    if 'Admin' not in session.get('roles', []):
        return redirect(url_for('multi_dashboard'))
    
    return render_template('dashboard.html', name=user.name)

@app.route('/multi_dashboard')
def multi_dashboard():
    roles = session.get('roles', [])
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    
    if not user:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for('login'))
    
    # Correct logic:
    # Admins should not see this page. Redirect them to the main dashboard.
    if 'Admin' in session.get('roles', []):
        return redirect(url_for('dashboard'))

    return render_template('multi_dashboard.html', roles=roles, username=user.username)

@app.route('/project/<int:project_id>')
def project_page(project_id):
    project = Project.query.get(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('project_page.html', project=project, user=session.get('user'))

@app.route('/logout')
def logout():
    session.clear()
    flash('🚪 Logged out successfully.', 'success')
    return redirect(url_for('login'))

# === API Endpoints ===

@app.route('/api/user_modules')
def get_user_modules():
    user_email = session.get('user')
    if not user_email:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
    
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
    modules = set()
    for role in user.roles:
        role_perms = RolePermissions.query.filter_by(role_name=role.name).first()
        if role_perms and role_perms.permissions:
            for perm in role_perms.permissions.split(','):
                # Remove empty strings
                if perm:
                    modules.add(perm)
    
    # Get user roles for frontend
    user_roles = [role.name for role in user.roles]
    
    return jsonify({
        'status': 'success', 
        'modules': list(modules),
        'roles': user_roles
    })


@app.route('/api/add_user', methods=['POST'])
def api_add_user():
    try:
        data = request.get_json()
        full_name = data.get('full_name')
        username = data.get('username')
        email = data.get('email')
        roles = data.get('roles')
        password = data.get('password')

        if not all([full_name, username, email, roles, password]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'})

        if User.query.filter_by(email=email).first():
            return jsonify({'status': 'error', 'message': 'Email already exists'})

        user = User(name=full_name, username=username, email=email, password=generate_password_hash(password), created_by_admin=True)
        for role_name in roles:
            role = Role.query.filter_by(name=role_name).first()
            if role:
                user.roles.append(role)

        db.session.add(user)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'User added successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/users')
def get_users():
    # Only return users that are NOT deleted
    users = User.query.filter_by(is_deleted=False).all()
    user_list = []
    for user in users:
        user_list.append({
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'email': user.email,
            'roles': [r.name for r in user.roles]
        })
    return {'status': 'success', 'users': user_list}

@app.route('/api/get_user')
def api_get_user():
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'})
    return jsonify({'status': 'success', 'user': {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'name': user.name,
        'roles': [r.name for r in user.roles]
    }})

@app.route('/api/update_user', methods=['POST'])
def api_update_user():
    try:
        data = request.get_json()
        email = data.get('old_email')
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'})

        user.username = data.get('new_username')
        user.email = data.get('new_email')

        if data.get('new_password'):
            user.password = generate_password_hash(data['new_password'])

        new_roles = data.get('roles', [])
        user.roles = []
        for role_name in new_roles:
            role = Role.query.filter_by(name=role_name).first()
            if role:
                user.roles.append(role)

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'User updated', 'updated_roles': [r.name for r in user.roles]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/team_leads')
def get_team_leads():
    try:
        team_lead_role = Role.query.filter_by(name='Team Lead').first()
        if not team_lead_role:
            return jsonify({'status': 'error', 'message': 'Team Lead role not found'}), 404
            
        team_leads = team_lead_role.users
        team_leads_list = [{'id': user.id, 'name': user.name} for user in team_leads if not user.is_deleted]

        return jsonify({'status': 'success', 'team_leads': team_leads_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/delete_user', methods=['POST'])
def api_delete_user():
    # This now performs a SOFT delete
    try:
        data = request.get_json()
        email = data.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'})

        # Mark user as deleted instead of removing
        user.is_deleted = True
        
        # Also mark associated employee info as deleted
        employee_info = EmployeeInfo.query.filter_by(user_id=user.id).first()
        if employee_info:
            employee_info.is_deleted = True

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'User moved to Deleted Users'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
@app.route('/api/add_project', methods=['POST'])
def add_project():
    try:
        data = request.get_json()
        project = Project(
            project_name=data['project_name'],
            group_name=data.get('group_name', ''),
            members=data.get('members', ''),
            start_date=data['start_date'],
            end_date=data['end_date'],
            deadline=data.get('deadline'),  # Add deadline field
            budget_head=data['budget_head'],
            created_by=session.get('user', 'Unknown')
        )
        db.session.add(project)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Project created successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
# 👇 ADD THIS NEW ENDPOINT
@app.route('/api/deleted_users')
def get_deleted_users():
    # Get ONLY the deleted users
    users = User.query.filter_by(is_deleted=True).all()
    user_list = [{'name': u.name, 'email': u.email, 'roles': [r.name for r in u.roles]} for u in users]
    return jsonify({'status': 'success', 'users': user_list})

@app.route('/api/permanent_delete_user', methods=['POST'])
def permanent_delete_user():
    """Permanently delete a user from the database"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'status': 'error', 'message': 'Email is required'}), 400
        
        # Find the user
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Check if user is already soft deleted
        if not user.is_deleted:
            return jsonify({'status': 'error', 'message': 'User is not in deleted state. Please soft delete first.'}), 400
        
        # Get user's name for confirmation message
        user_name = user.name
        
        # Delete associated employee info if exists
        employee_info = EmployeeInfo.query.filter_by(user_id=user.id).first()
        if employee_info:
            db.session.delete(employee_info)
        
        # Delete user roles associations
        user.roles.clear()
        
        # Delete the user
        db.session.delete(user)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': f'User {user_name} ({email}) permanently deleted from database'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 👇 ADD THIS NEW ENDPOINT
@app.route('/api/restore_user', methods=['POST'])
def api_restore_user():
    try:
        data = request.get_json()
        email = data.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'})

        # Mark user as NOT deleted
        user.is_deleted = False

        # Also restore associated employee info
        employee_info = EmployeeInfo.query.filter_by(user_id=user.id).first()
        if employee_info:
            employee_info.is_deleted = False
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'User restored successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
@app.route('/api/projects', methods=['GET'])
def get_projects():
    projects = Project.query.all()
    project_list = []
    for project in projects:
        project_list.append({
            'id': project.id,
            'project_name': project.project_name,
            'group_name': project.group_name or '',
            'members': project.members or '',
            'start_date': project.start_date,
            'end_date': project.end_date,
            'deadline': project.deadline,  # Include deadline field
            'budget_head': project.budget_head,
            'created_by': project.created_by or 'Unknown'
        })
    return jsonify({'status': 'success', 'projects': project_list})

@app.route('/api/delete_project/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'status': 'error', 'message': 'Project not found'})
        
        groups = Group.query.filter_by(project_id=project_id).all()
        for group in groups:
            db.session.delete(group)
        
        db.session.delete(project)
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'Project "{project.project_name}" and all its groups deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
# === NEW API ENDPOINT FOR MULTI DASHBOARD ===

@app.route('/api/my_tasks')
def get_my_tasks():
    # 1. Check if a user is logged in
    user_email = session.get('user')
    if not user_email:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

    # 2. Find the user in the database
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    try:
        # 3. The 'user.groups' relationship automatically finds all groups the user is a member of
        assigned_groups = user.groups
        
        task_list = []
        for group in assigned_groups:
            task_list.append({
    'project_name': group.project.project_name,
    'group_name': group.name,
    'group_type': group.group_type,  # <-- ADD THIS LINE
    'deadline': group.deadline,
    'description': group.description
})
            
        # 4. Return the data in the format the frontend expects
        return jsonify({'status': 'success', 'tasks': task_list})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    
@app.route('/api/my_projects')
def get_my_projects():
    user_email = session.get('user')
    if not user_email:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    try:
        # Find all unique projects the user is a part of by looking at their group memberships
        projects = db.session.query(Project).join(Group).join(group_members).filter(group_members.c.user_id == user.id).distinct().all()

        project_list = []
        for project in projects:
            project_list.append({
                'id': project.id,
                'project_name': project.project_name,
                'start_date': project.start_date,
                'end_date': project.end_date,
                'budget_head': project.budget_head
            })
        
        return jsonify({'status': 'success', 'projects': project_list})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
# === API ENDPOINTS FOR TEAMS & GROUPS ===
@app.route('/api/teams', methods=['GET'])
def get_teams():
    teams = Team.query.all()
    team_list = []
    for team in teams:
        members_names = [member.name for member in team.members]
        team_list.append({
            'id': team.id,
            'name': team.name,
            'description': team.description,
            'members': members_names
        })
    return jsonify({'status': 'success', 'teams': team_list})

@app.route('/api/teams', methods=['POST'])
def create_team():
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        member_ids = data.get('members', [])

        if not name:
            return jsonify({'status': 'error', 'message': 'Team name is required'})

        if Team.query.filter_by(name=name).first():
            return jsonify({'status': 'error', 'message': 'Team with this name already exists'})

        new_team = Team(name=name, description=description)

        for user_id in member_ids:
            user = User.query.get(user_id)
            if user:
                new_team.members.append(user)

        db.session.add(new_team)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Team created successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
# app.py

# In your app.py file

# ... (other Flask endpoints) ...

@app.route('/api/get_current_user')
def get_current_user():
    user_email = session.get('user')
    if not user_email:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
    
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
    return jsonify({
        'status': 'success', 
        'user': {
            'id': user.id, 
            'name': user.name, 
            'email': user.email,
            'roles': [role.name for role in user.roles]
        }
    })

# ... (rest of the Flask code) ...

@app.route('/api/user_id')
def get_current_user_id():
    user_email = session.get('user')
    if not user_email:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
    
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
    return jsonify({'status': 'success', 'user_id': user.id})

# ... (rest of the code) ...
@app.route('/api/teams/<int:team_id>', methods=['PUT'])
def update_team(team_id):
    try:
        data = request.get_json()
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'status': 'error', 'message': 'Team not found'})

        team.name = data.get('name', team.name)
        team.description = data.get('description', team.description)
        
        new_member_ids = data.get('members', None)
        if new_member_ids is not None:
            team.members = []
            for user_id in new_member_ids:
                user = User.query.get(user_id)
                if user:
                    team.members.append(user)

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Team updated successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/teams/<int:team_id>', methods=['DELETE'])
def delete_team(team_id):
    try:
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'status': 'error', 'message': 'Team not found'})
        
        db.session.delete(team)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Team deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

# === Group API Endpoints ===
@app.route('/api/groups/<int:project_id>', methods=['GET'])
def get_project_groups(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'status': 'error', 'message': 'Project not found'})
        
        groups = Group.query.filter_by(project_id=project_id).all()
        
        group_list = []
        for group in groups:
            members_names = [member.name for member in group.members]
            group_list.append({
                'id': group.id,
                'name': group.name,
                'group_type': group.group_type,
                'description': group.description,
                'project_id': group.project_id,
                'deadline': group.deadline,  # Include deadline field
                'created_at': group.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'members': members_names
            })
        
        return jsonify({'status': 'success', 'groups': group_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/groups', methods=['POST'])
def create_group():
    try:
        data = request.get_json()
        name = data.get('name')
        group_type = data.get('group_type', 'other')
        description = data.get('description', '')
        project_id = data.get('project_id')
        member_ids = data.get('member_ids', [])
        deadline = data.get('deadline', '')  # Extract deadline from request data

        if not name or not project_id:
            return jsonify({'status': 'error', 'message': 'Group name and project ID are required'})

        project = Project.query.get(project_id)
        if not project:
            return jsonify({'status': 'error', 'message': 'Project not found'})

        existing_group = Group.query.filter_by(name=name, project_id=project_id).first()
        if existing_group:
            return jsonify({'status': 'error', 'message': 'Group with this name already exists in this project'})

        new_group = Group(
            name=name,
            group_type=group_type,
            description=description,
            project_id=project_id,
            deadline=deadline  # Store the deadline in the new group
        )

        for user_id in member_ids:
            user = User.query.get(user_id)
            if user:
                new_group.members.append(user)

        db.session.add(new_group)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Group created successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    try:
        group = Group.query.get(group_id)
        if not group:
            return jsonify({'status': 'error', 'message': 'Group not found'})
        
        db.session.delete(group)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Group deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    
@app.route('/api/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    try:
        group = Group.query.get(group_id)
        if not group:
            return jsonify({'status': 'error', 'message': 'Group not found'})
        
        group_data = {
            'id': group.id,
            'name': group.name,
            'group_type': group.group_type,
            'description': group.description,
            'project_id': group.project_id,
            'deadline': group.deadline,
            'created_at': group.created_at.isoformat() if group.created_at else None,
            'members': [{'id': user.id, 'name': user.name, 'email': user.email} for user in group.members]
        }
        
        return jsonify({'status': 'success', 'group': group_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
@app.route('/api/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    try:
        group = Group.query.get(group_id)
        if not group:
            return jsonify({'status': 'error', 'message': 'Group not found'})
        
        data = request.get_json()
        
        # Update fields if provided
        if 'name' in data:
            group.name = data['name']
        if 'group_type' in data:
            group.group_type = data['group_type']
        if 'description' in data:
            group.description = data['description']
        if 'deadline' in data:
            group.deadline = data['deadline']
        
        # Update members if provided
        if 'member_ids' in data:
            group.members.clear()
            for user_id in data['member_ids']:
                user = User.query.get(user_id)
                if user:
                    group.members.append(user)
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Group updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
        
# === Attendance API Endpoints ===

# Helper function to fetch attendance from Google Drive
def fetch_from_drive(prefix, date_str=None):
    try:
        # NOTE: Make sure to place your 'credentials.json' file in the root directory
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)

        if not date_str:
            date_str = datetime.now(indian_tz).strftime("%Y-%m-%d")

        filename = f"{prefix}_attendance_{date_str}.csv"
        folder_id = "1IK_7O_k5zAdgLEYyRZLDrQSzniAUuava"
        query = f"name='{filename}' and '{folder_id}' in parents and mimeType='text/csv'"
        results = service.files().list(q=query, pageSize=1, fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            return None

        file_id = items[0]['id']
        file_request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, file_request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        df = pd.read_csv(fh)
        df = df.fillna('')
        df['Date'] = date_str.strip()

        return df

    except Exception as e:
        print(f"⚠️ fetch_from_drive({prefix}) error: {e}")
        return None

@app.route('/api/attendance/today')
def api_attendance_today():
    try:
        today = datetime.now(indian_tz).strftime("%Y-%m-%d")

        df_ssev = fetch_from_drive("ssev", today)
        df_softsols = fetch_from_drive("softsols", today)

        employees = []

        for df in [df_ssev, df_softsols]:
            if df is not None:
                for _, row in df.iterrows():
                    employees.append({
                        "name": row.get("Name", "—"),
                        "branch": row.get("Branch", "—"),
                        "designation": row.get("Designation", "—"),
                        "checkin": row.get("Check-In", ""),
                        "checkout": row.get("Check-Out", ""),
                        "status": row.get("Status", "—")
                    })

        return jsonify({"status": "success", "employees": employees})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/attendance/both/<date>')
def get_both_attendance(date):
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    SERVICE_ACCOUNT_FILE = 'credentials.json'
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=creds)

    filenames = [
        f"ssev_attendance_{date}.csv",
        f"softsols_attendance_{date}.csv"
    ]

    folder_id = "1IK_7O_k5zAdgLEYyRZLDrQSzniAUuava" 
    combined_data = {}

    for filename in filenames:
        results = service.files().list(
            q=f"name = '{filename}' and '{folder_id}' in parents and trashed = false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        items = results.get('files', [])

        if not items:
            combined_data[filename] = {"status": "not_found"}
            continue

        file_id = items[0]['id']

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        try:
            df = pd.read_csv(fh)
            combined_data[filename] = {
                "status": "success",
                "data": df.to_dict(orient="records")
            }
        except Exception as e:
            combined_data[filename] = {
                "status": "error",
                "message": str(e)
            }

    return jsonify({
        "status": "success",
        "date": date,
        "attendance": combined_data
    })
# Roles
@app.route('/api/add_role', methods=['POST'])
def add_role():
    try:
        data = request.get_json()
        role_name = data.get('role_name', '').strip()

        if not role_name:
            return jsonify({'status': 'error', 'message': 'Role name cannot be empty'}), 400

        existing_role = Role.query.filter_by(name=role_name).first()
        if existing_role:
            return jsonify({'status': 'error', 'message': 'Role already exists'}), 409

        new_role = Role(name=role_name)
        # Instantiate a RolePermissions entry with a default empty permission string
        new_perms = RolePermissions(role_name=role_name, permissions='')

        db.session.add(new_role)
        db.session.add(new_perms)  # Add the new permissions object to the session
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Role added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/roles', methods=['GET'])
def get_roles():
    try:
        roles = Role.query.all()
        role_list = [role.name for role in roles]
        return jsonify({'status': 'success', 'roles': role_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/get_role_permissions/<string:role_name>', methods=['GET'])
def get_role_permissions(role_name):
    try:
        perms = RolePermissions.query.filter_by(role_name=role_name).first()
        if perms:
            return jsonify({'status': 'success', 'permissions': perms.permissions.split(',')})
        
        # If no permissions entry exists, create a new one on the fly
        role_exists = Role.query.filter_by(name=role_name).first()
        if role_exists:
            new_perms = RolePermissions(role_name=role_name, permissions='')
            db.session.add(new_perms)
            db.session.commit()
            return jsonify({'status': 'success', 'permissions': []})

        # If the role itself doesn't exist
        return jsonify({'status': 'error', 'message': 'Role not found'}), 404
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/delete_role/<string:role_name>', methods=['DELETE'])
def api_delete_role(role_name):
    # Prevent deletion of critical system roles
    protected_roles = ['Admin', 'CEO', 'CTO', 'CFO', 'Director', 'Manager', 'Employee', 'Accounts', 'Finance', 'Procurement']
    if role_name in protected_roles:
        return jsonify({'status': 'error', 'message': f'Cannot delete the protected role: {role_name}'}), 403

    try:
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            return jsonify({'status': 'error', 'message': 'Role not found.'}), 404
        
        # Check if any users are still assigned to this role
        if role.users.count() > 0:
            return jsonify({'status': 'error', 'message': f'Cannot delete role "{role_name}" because it is still assigned to {role.users.count()} user(s).'}), 409

        # Delete the role permissions first
        role_perms = RolePermissions.query.filter_by(role_name=role_name).first()
        if role_perms:
            db.session.delete(role_perms)
        
        # Now delete the role itself
        db.session.delete(role)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': f'Role "{role_name}" deleted successfully.'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/save_role_permissions', methods=['POST'])
def save_role_permissions():
    try:
        data = request.get_json()
        role_name = data.get('role_name')
        permissions = data.get('permissions', [])
        
        perms = RolePermissions.query.filter_by(role_name=role_name).first()
        if perms:
            perms.permissions = ','.join(permissions)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Permissions saved successfully'})
        
        return jsonify({'status': 'error', 'message': 'Role not found'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})




# In app.py
# Helper functions for safe type conversion
def safe_float_convert(value, default=None):
    """Safely convert string to float, return default if empty or invalid"""
    if not value or value.strip() == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int_convert(value, default=None):
    """Safely convert string to int, return default if empty or invalid"""
    if not value or value.strip() == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def calculate_provident_fund(basic_salary):
    """Calculate Provident Fund based on basic salary"""
    if basic_salary is None:
        return 0.0
    
    if basic_salary >= 15000:
        # If basic is 15000 or above, PF is 12% of 15000 only
        return 15000 * 0.12
    else:
        # If basic is below 15000, PF is 12% of basic amount
        return basic_salary * 0.12

def calculate_professional_tax(gross_salary):
    """Calculate Professional Tax based on gross salary"""
    if gross_salary is None:
        return 0.0
    
    if 15001 <= gross_salary <= 20000:
        return 150.0
    elif gross_salary > 20000:
        return 200.0
    else:
        return 0.0

def safe_date_convert(value, default=None):
    """Safely convert string to date object, return default if empty or invalid"""
    if not value or value.strip() == '':
        return default
    try:
        from datetime import datetime
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return default

@app.route('/api/add_employee_info', methods=['POST'])
def add_employee_info():
    try:
        # Handle form data and file uploads
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        
        print(f"Attempting to add employee info for: {full_name} ({email})")
        
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"User not found for email: {email}")
            return jsonify({'status': 'error', 'message': f'User not found for email: {email}. Please create the user first in the User Management section.'})
        
        print(f"Found user: {user.name} (ID: {user.id})")

        if not user.id:
            print(f"User ID is None for user: {user}")
            return jsonify({'status': 'error', 'message': 'Invalid user data. Please try again.'})
            
        if EmployeeInfo.query.filter_by(user_id=user.id).first():
            return jsonify({'status': 'error', 'message': 'Employee info for this user already exists.'})

        # Handle file uploads
        pdc_filename = None
        aadhaar_filename = None
        pan_filename = None
        resume_filename = None

        if 'pdc' in request.files and request.files['pdc'].filename:
            file = request.files['pdc']
            if file and allowed_file(file.filename):
                pdc_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], pdc_filename))

        if 'aadhaar_card' in request.files and request.files['aadhaar_card'].filename:
            file = request.files['aadhaar_card']
            if file and allowed_file(file.filename):
                aadhaar_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_filename))

        if 'pan_card' in request.files and request.files['pan_card'].filename:
            file = request.files['pan_card']
            if file and allowed_file(file.filename):
                pan_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], pan_filename))

        if 'resume' in request.files and request.files['resume'].filename:
            file = request.files['resume']
            if file and allowed_file(file.filename):
                resume_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_filename))

        passport_photo_filename = None
        if 'passport_photo' in request.files and request.files['passport_photo'].filename:
            file = request.files['passport_photo']
            if file and allowed_file(file.filename):
                passport_photo_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], passport_photo_filename))

        tenth_certificate_filename = None
        twelfth_certificate_filename = None

        if 'tenth_certificate' in request.files and request.files['tenth_certificate'].filename:
            file = request.files['tenth_certificate']
            if file and allowed_file(file.filename):
                tenth_certificate_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], tenth_certificate_filename))

        if 'twelfth_certificate' in request.files and request.files['twelfth_certificate'].filename:
            file = request.files['twelfth_certificate']
            if file and allowed_file(file.filename):
                twelfth_certificate_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], twelfth_certificate_filename))

        post_graduation_certificate_filename = None

        if 'post_graduation_certificate' in request.files and request.files['post_graduation_certificate'].filename:
            file = request.files['post_graduation_certificate']
            if file and allowed_file(file.filename):
                post_graduation_certificate_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], post_graduation_certificate_filename))

        print(f"Creating EmployeeInfo with user_id: {user.id}")
        new_employee_info = EmployeeInfo(
            user_id=user.id,
            full_name=full_name,
            email=email,
            dob=safe_date_convert(request.form.get('dob')),
            gender=request.form.get('gender'),
            father_name=request.form.get('father_name'),
            father_contact=request.form.get('father_contact'),
            mother_name=request.form.get('mother_name'),
            mother_contact=request.form.get('mother_contact'),
            emergency_contact_name=request.form.get('emergency_contact_name'),
            emergency_phone_number=request.form.get('emergency_phone_number'),
            spouse_name=request.form.get('spouse_name'),
            spouse_contact_number=request.form.get('spouse_contact_number'),
            phone_no=request.form.get('phone_no'),
            address=request.form.get('address'),
            office_branch=request.form.get('office_branch'),
            employee_id=request.form.get('employee_id'),
            pdc=pdc_filename,
            aadhaar_card=aadhaar_filename,
            pan_card=pan_filename,
            resume=resume_filename,
            passport_photo=passport_photo_filename,
            tenth_certificate=tenth_certificate_filename,
            twelfth_certificate=twelfth_certificate_filename,
            marital_status=request.form.get('marital_status'),
            designation=request.form.get('designation'),
            probation_from=safe_date_convert(request.form.get('probation_from')),
            probation_to=safe_date_convert(request.form.get('probation_to')),
            date_of_joining=safe_date_convert(request.form.get('date_of_joining')),
            confirmation_date=safe_date_convert(request.form.get('confirmation_date')),
            date_of_anniversary=safe_date_convert(request.form.get('date_of_anniversary')),
            probation_salary=request.form.get('probation_salary'),
            confirmation_salary=request.form.get('confirmation_salary'),
            post_graduation_marks=request.form.get('post_graduation_marks'),
            post_graduation_certificate=post_graduation_certificate_filename,
            account_number=request.form.get('account_number'),
            actual_gross_salary=safe_float_convert(request.form.get('actual_gross_salary')),
            basic=safe_float_convert(request.form.get('basic')),
            hra=safe_float_convert(request.form.get('hra')),
            conveyance=safe_float_convert(request.form.get('conveyance')),
            special_allowance=safe_float_convert(request.form.get('special_allowance')),
            provident_fund=calculate_provident_fund(safe_float_convert(request.form.get('basic'))),
            esi=safe_float_convert(request.form.get('esi')),
            professional_tax=calculate_professional_tax(safe_float_convert(request.form.get('actual_gross_salary'))),
            income_tax=safe_float_convert(request.form.get('income_tax')),
            advance=safe_float_convert(request.form.get('advance')),
            total_leaves=safe_int_convert(request.form.get('total_leaves'))
        )
        try:
            db.session.add(new_employee_info)
            db.session.flush()  # Flush to get the ID before commit
            print(f"Employee created with ID: {new_employee_info.id}")
            
            # Update PF No in User model
            user.pf_no = request.form.get('pf_no')
            
            db.session.commit()
            print(f"Employee info committed successfully with ID: {new_employee_info.id}")
            return jsonify({'status': 'success', 'message': 'Employee info added successfully.'})
        except Exception as commit_error:
            db.session.rollback()
            print(f"Error during commit: {commit_error}")
            raise commit_error
    except Exception as e:
        db.session.rollback()
        print(f"Error saving employee info: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get_all_employee_info')
def get_all_employee_info():
    try:
        # Only get employees that are NOT deleted
        employees = EmployeeInfo.query.filter_by(is_deleted=False).all()
        print(f"Found {len(employees)} employees")
        employee_list = []
        for emp in employees:
            print(f"Processing employee: {emp.full_name} (ID: {emp.id})")
            if emp is None or emp.id is None or emp.full_name is None:
                print(f"Skipping employee with NULL data: {emp}")
                continue
            employee_list.append({
                'id': emp.id,
                'full_name': emp.full_name,
                'email': emp.email,
                'dob': emp.dob,
                'gender': emp.gender,
                'phone_no': emp.phone_no,
                'address': emp.address,
                'office_branch': emp.office_branch,
                'designation': emp.designation,
                'actual_gross_salary': emp.actual_gross_salary,
                'basic': emp.basic,
                'hra': emp.hra,
                'conveyance': emp.conveyance,
                'vehicle_maintenance': emp.vehicle_maintenance,
                'special_allowance': emp.special_allowance,
                'add_others': emp.add_others,
                'provident_fund': emp.provident_fund,
                'esi': emp.esi,
                'professional_tax': emp.professional_tax,
                'income_tax': emp.income_tax,
                'advance': emp.advance,
                'other_deductions': emp.other_deductions,
                'loss_of_pay': emp.loss_of_pay,
                'total_leaves': emp.total_leaves,
                'leave_availed': emp.leave_availed,
                'balance_leaves': emp.balance_leaves,
                'no_of_lop_days': emp.no_of_lop_days,
                'ndp': emp.ndp,
                'earnings_basic': emp.earnings_basic,
                'earnings_hra': emp.earnings_hra,
                'earnings_conveyance': emp.earnings_conveyance,
                'earnings_vehicle_maintenance': emp.earnings_vehicle_maintenance,
                'earnings_special_allowance': emp.earnings_special_allowance,
                'earnings_add_others': emp.earnings_add_others
            })
        print(f"Returning {len(employee_list)} employees")
        return jsonify({'status': 'success', 'employees': employee_list})
    except Exception as e:
        print(f"Error in get_all_employee_info: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/get_employee_info/<int:employee_id>')
def get_employee_info(employee_id):
    try:
        employee = EmployeeInfo.query.get(employee_id)
        if not employee:
            return jsonify({'status': 'error', 'message': 'Employee not found.'})
        
        user_roles = [r.name for r in employee.user.roles] if employee.user else []

        info = {
            'id': employee.id,
            'user_id': employee.user_id,
            'full_name': employee.full_name,
            'email': employee.email,
            'dob': employee.dob,
            'gender': employee.gender,
            'office_branch': employee.office_branch, # New field added
            'employee_id': employee.employee_id,  # Custom Employee ID field
            'father_name': employee.father_name,
            'father_contact': employee.father_contact,
            'mother_name': employee.mother_name,
            'mother_contact': employee.mother_contact,
            'emergency_contact_name': employee.emergency_contact_name,
            'emergency_phone_number': employee.emergency_phone_number,
            'spouse_name': employee.spouse_name,
            'spouse_contact_number': employee.spouse_contact_number,
            'phone_no': employee.phone_no,
            'address': employee.address,
            
            # --- RETURN NEW FILE FIELD DATA ---
            'pdc': employee.pdc,
            'aadhaar_card': employee.aadhaar_card,
            'pan_card': employee.pan_card,
            'resume': employee.resume,
            'passport_photo': employee.passport_photo,
            'tenth_certificate': employee.tenth_certificate,
            'twelfth_certificate': employee.twelfth_certificate,
            'marital_status': employee.marital_status,
            'designation': employee.designation,
            'probation_from': employee.probation_from.strftime('%Y-%m-%d') if employee.probation_from else None,
            'probation_to': employee.probation_to.strftime('%Y-%m-%d') if employee.probation_to else None,
            'date_of_joining': employee.date_of_joining.strftime('%Y-%m-%d') if employee.date_of_joining else None,
            'confirmation_date': employee.confirmation_date.strftime('%Y-%m-%d') if employee.confirmation_date else None,
            'date_of_anniversary': employee.date_of_anniversary.strftime('%Y-%m-%d') if employee.date_of_anniversary else None,
            'probation_salary': employee.probation_salary,
            'confirmation_salary': employee.confirmation_salary,
            'post_graduation_marks': employee.post_graduation_marks,
            'post_graduation_certificate': employee.post_graduation_certificate,
            # ----------------------------------
            
            'account_number': employee.account_number,
            'actual_gross_salary': employee.actual_gross_salary,
            'basic': employee.basic,
            'hra': employee.hra,
            'conveyance': employee.conveyance,
            'vehicle_maintenance': employee.vehicle_maintenance,
            'special_allowance': employee.special_allowance,
            'add_others': employee.add_others,
            'provident_fund': employee.provident_fund,
            'esi': employee.esi,
            'professional_tax': employee.professional_tax,
            'income_tax': employee.income_tax,
            'advance': employee.advance,
            'other_deductions': employee.other_deductions,
            'loss_of_pay': employee.loss_of_pay,
            'leave_availed': employee.leave_availed,
            'balance_leaves': employee.balance_leaves,
            'no_of_lop_days': employee.no_of_lop_days,
            'ndp': employee.ndp,
            'total_leaves': employee.total_leaves,
            'designation': employee.designation,
            'pf_no': employee.user.pf_no if employee.user else None,
            'roles': user_roles
        }
        return jsonify({'status': 'success', 'employee': info})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/get_employee_report_data', methods=['POST'])
def get_employee_report_data():
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        
        if not employee_id or not from_date or not to_date:
            return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400
        
        # Get employee info
        employee = EmployeeInfo.query.get(employee_id)
        if not employee:
            return jsonify({'status': 'error', 'message': 'Employee not found'}), 404
        
        # Convert dates
        from datetime import datetime, timedelta
        start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        
        # Count working days (NDP) - For now, calculate weekdays as fallback
        # TODO: Integrate with Firebase attendance data
        working_days = 0
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                working_days += 1
            current_date = current_date + timedelta(days=1)
        
        # Count leaves from leave_request table - count approved leaves that overlap with the date range
        leave_count = db.session.query(LeaveRequest).filter(
            LeaveRequest.user_id == employee.user_id,
            LeaveRequest.status == 'Approved',
            # Check if the leave period overlaps with the selected date range
            LeaveRequest.from_date <= to_date,
            LeaveRequest.to_date >= from_date
        ).count()
        
        # Count permissions from permission_request table - count approved permissions within the date range
        permission_count = db.session.query(PermissionRequest).filter(
            PermissionRequest.user_id == employee.user_id,
            PermissionRequest.status == 'Approved',
            PermissionRequest.date >= from_date,
            PermissionRequest.date <= to_date
        ).count()
        
        # Get salary from employee info
        salary = float(employee.actual_gross_salary) if employee.actual_gross_salary else 0
        
        # Get advances from employee account info (from accounts section)
        advances = float(employee.advance) if employee.advance else 0
        
        report_data = {
            'ndp': working_days,
            'no_of_leaves': leave_count,
            'no_of_permissions': permission_count,
            'advances': advances,
            'salary': salary,
            'employee_name': employee.full_name,
            'period': f"{from_date} to {to_date}"
        }
        
        return jsonify({'status': 'success', 'data': report_data})
        
    except Exception as e:
        print(f"Error getting employee report data: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to get employee report data'}), 500

@app.route('/api/get_attendance_from_firebase', methods=['POST'])
def get_attendance_from_firebase():
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        
        if not employee_id or not from_date or not to_date:
            return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400
        
        # Get employee info to get the user's name for Firebase lookup
        employee = EmployeeInfo.query.get(employee_id)
        if not employee:
            return jsonify({'status': 'error', 'message': 'Employee not found'}), 404
        
        # Convert dates
        from datetime import datetime, timedelta
        start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        
        # Calculate working days by checking each date in the range
        working_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                # For now, assume present if it's a weekday
                # TODO: Integrate with actual Firebase attendance data
                working_days += 1
            current_date = current_date + timedelta(days=1)
        
        return jsonify({
            'status': 'success', 
            'working_days': working_days,
            'message': 'Attendance data calculated (Firebase integration pending)'
        })
        
    except Exception as e:
        print(f"Error getting attendance from Firebase: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to get attendance data'}), 500

@app.route('/api/update_employee_designation/<int:employee_id>', methods=['POST'])
def update_employee_designation(employee_id):
    try:
        # Get the designation from form data
        designation = request.form.get('designation')
        
        if not designation:
            return jsonify({'status': 'error', 'message': 'Designation is required'}), 400
        
        # Find the employee
        employee = EmployeeInfo.query.get(employee_id)
        if not employee:
            return jsonify({'status': 'error', 'message': 'Employee not found'}), 404
        
        # Update the designation
        employee.designation = designation
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Designation updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/update_employee_info', methods=['POST'])
def update_employee_info():
    try:
        # Handle form data and file uploads
        employee_id = request.form.get('id')
        employee = EmployeeInfo.query.get(employee_id)
        if not employee:
            return jsonify({'status': 'error', 'message': 'Employee not found.'})

        # Update basic fields
        employee.full_name = request.form.get('full_name', employee.full_name)
        employee.email = request.form.get('email', employee.email)
        employee.dob = safe_date_convert(request.form.get('dob'), employee.dob)
        employee.gender = request.form.get('gender', employee.gender)
        employee.office_branch = request.form.get('office_branch', employee.office_branch)
        employee.employee_id = request.form.get('employee_id', employee.employee_id)
        employee.marital_status = request.form.get('marital_status', employee.marital_status)
        employee.designation = request.form.get('designation', employee.designation)
        employee.probation_from = safe_date_convert(request.form.get('probation_from'), employee.probation_from)
        employee.probation_to = safe_date_convert(request.form.get('probation_to'), employee.probation_to)
        employee.date_of_joining = safe_date_convert(request.form.get('date_of_joining'), employee.date_of_joining)
        employee.confirmation_date = safe_date_convert(request.form.get('confirmation_date'), employee.confirmation_date)
        employee.date_of_anniversary = safe_date_convert(request.form.get('date_of_anniversary'), employee.date_of_anniversary)
        employee.probation_salary = request.form.get('probation_salary', employee.probation_salary)
        employee.confirmation_salary = request.form.get('confirmation_salary', employee.confirmation_salary)
        employee.post_graduation_marks = request.form.get('post_graduation_marks', employee.post_graduation_marks)
        employee.father_name = request.form.get('father_name', employee.father_name)
        employee.father_contact = request.form.get('father_contact', employee.father_contact)
        employee.mother_name = request.form.get('mother_name', employee.mother_name)
        employee.mother_contact = request.form.get('mother_contact', employee.mother_contact)
        employee.emergency_contact_name = request.form.get('emergency_contact_name', employee.emergency_contact_name)
        employee.emergency_phone_number = request.form.get('emergency_phone_number', employee.emergency_phone_number)
        employee.spouse_name = request.form.get('spouse_name', employee.spouse_name)
        employee.spouse_contact_number = request.form.get('spouse_contact_number', employee.spouse_contact_number)
        employee.phone_no = request.form.get('phone_no', employee.phone_no)
        employee.address = request.form.get('address', employee.address)
        
        # Accounts fields
        employee.account_number = request.form.get('account_number', employee.account_number)
        employee.actual_gross_salary = safe_float_convert(request.form.get('actual_gross_salary'), employee.actual_gross_salary)
        employee.basic = safe_float_convert(request.form.get('basic'), employee.basic)
        employee.hra = safe_float_convert(request.form.get('hra'), employee.hra)
        employee.conveyance = safe_float_convert(request.form.get('conveyance'), employee.conveyance)
        employee.special_allowance = safe_float_convert(request.form.get('special_allowance'), employee.special_allowance)
        employee.provident_fund = calculate_provident_fund(safe_float_convert(request.form.get('basic'), employee.basic))
        employee.esi = safe_float_convert(request.form.get('esi'), employee.esi)
        employee.professional_tax = calculate_professional_tax(safe_float_convert(request.form.get('actual_gross_salary'), employee.actual_gross_salary))
        employee.income_tax = safe_float_convert(request.form.get('income_tax'), employee.income_tax)
        employee.advance = safe_float_convert(request.form.get('advance'), employee.advance)
        employee.total_leaves = safe_int_convert(request.form.get('total_leaves'), employee.total_leaves)
        employee.designation = request.form.get('designation', employee.designation)
        
        # Update PF No in User model
        if employee.user:
            employee.user.pf_no = request.form.get('pf_no', employee.user.pf_no)

        # Handle file uploads - only update if new files are provided
        if 'pdc' in request.files and request.files['pdc'].filename:
            file = request.files['pdc']
            if file and allowed_file(file.filename):
                pdc_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], pdc_filename))
                employee.pdc = pdc_filename

        if 'aadhaar_card' in request.files and request.files['aadhaar_card'].filename:
            file = request.files['aadhaar_card']
            if file and allowed_file(file.filename):
                aadhaar_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_filename))
                employee.aadhaar_card = aadhaar_filename

        if 'pan_card' in request.files and request.files['pan_card'].filename:
            file = request.files['pan_card']
            if file and allowed_file(file.filename):
                pan_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], pan_filename))
                employee.pan_card = pan_filename

        if 'resume' in request.files and request.files['resume'].filename:
            file = request.files['resume']
            if file and allowed_file(file.filename):
                resume_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_filename))
                employee.resume = resume_filename

        if 'passport_photo' in request.files and request.files['passport_photo'].filename:
            file = request.files['passport_photo']
            if file and allowed_file(file.filename):
                passport_photo_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], passport_photo_filename))
                employee.passport_photo = passport_photo_filename

        if 'tenth_certificate' in request.files and request.files['tenth_certificate'].filename:
            file = request.files['tenth_certificate']
            if file and allowed_file(file.filename):
                tenth_certificate_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], tenth_certificate_filename))
                employee.tenth_certificate = tenth_certificate_filename

        if 'twelfth_certificate' in request.files and request.files['twelfth_certificate'].filename:
            file = request.files['twelfth_certificate']
            if file and allowed_file(file.filename):
                twelfth_certificate_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], twelfth_certificate_filename))
                employee.twelfth_certificate = twelfth_certificate_filename

        if 'post_graduation_certificate' in request.files and request.files['post_graduation_certificate'].filename:
            file = request.files['post_graduation_certificate']
            if file and allowed_file(file.filename):
                post_graduation_certificate_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], post_graduation_certificate_filename))
                employee.post_graduation_certificate = post_graduation_certificate_filename

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Employee info updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/delete_employee_info/<int:employee_id>', methods=['DELETE'])
def delete_employee_info(employee_id):
    try:
        employee = EmployeeInfo.query.get(employee_id)
        if not employee:
            return jsonify({'status': 'error', 'message': 'Employee not found.'})
        
        # Soft delete the employee info
        employee.is_deleted = True
        
        # Also soft delete the associated user account
        user = User.query.get(employee.user_id)
        if user:
            user.is_deleted = True

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Employee info moved to Deleted Users.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    
# ADD THIS ENTIRE BLOCK OF API ROUTES TO app.py

# === API ENDPOINTS FOR PERSONAL "MY PROJECTS" FEATURE ===

# --- Get all personal projects for the logged-in user ---
@app.route('/api/user/projects', methods=['GET'])
def get_user_projects():
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

    projects = PersonalProject.query.filter_by(user_id=user.id).all()
    project_list = [{'id': p.id, 'name': p.name} for p in projects]
    return jsonify({'status': 'success', 'projects': project_list})

# --- Create a new personal project ---
@app.route('/api/user/projects', methods=['POST'])
def create_user_project():
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    new_project = PersonalProject(name=data['project_name'], user_id=user.id)
    db.session.add(new_project)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Project created'})

# --- Get all tasks for a specific personal project ---
@app.route('/api/project/<int:project_id>/tasks', methods=['GET'])
def get_project_tasks(project_id):
    # Security Check: Ensure the project belongs to the current user
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    project = PersonalProject.query.filter_by(id=project_id, user_id=user.id).first()
    if not project:
        return jsonify({'status': 'error', 'message': 'Project not found or access denied'}), 404

    tasks = PersonalTask.query.filter_by(project_id=project_id).all()
    task_list = [{
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'deadline': t.deadline,
        'completed': t.completed
    } for t in tasks]
    return jsonify({'status': 'success', 'tasks': task_list})


# ADD ALL OF THESE API ROUTES TO YOUR app.py

@app.route('/api/asset_form_options', methods=['GET'])
def get_asset_form_options():
    try:
        projects = Project.query.all()
        project_list = [{'id': p.id, 'project_name': p.project_name} for p in projects]
        
        team_lead_role = Role.query.filter_by(name='Team Lead').first()
        team_leads = []
        if team_lead_role:
            team_leads = [{'id': u.id, 'name': u.name} for u in team_lead_role.users if not u.is_deleted]

        return jsonify({
            'status': 'success',
            'projects': project_list,
            'team_leads': team_leads
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/asset_requests', methods=['POST'])
def create_asset_request():
    try:
        data = request.get_json()
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

        team_lead_id = data.get('teamLeadId')
        print(f"Creating new asset request for user {user.name} (ID: {user.id})")
        print(f"Team Lead ID: {team_lead_id}")
        print(f"Team Lead ID type: {type(team_lead_id)}")
        
        new_request = AssetRequest(
            indenter_id=user.id,
            indenter_name=data.get('indenterName'),
            office_project_type=data.get('officeProjectType'),
            project_id=data.get('projectId'),
            team_lead_id=team_lead_id,
            reference_file_no=data.get('referenceFileNo'),
            purchase_type=data.get('purchaseType'),
            budget_head=data.get('budgetHead'),
            nature_of_expenditure=data.get('natureOfExpenditure'),
            gst_applicable=data.get('gstApplicable'),
            item_details=json.dumps(data.get('itemDetails', [])),
            discount_amount=float(data.get('discountAmount', 0)),
            status='Pending TL Approval'
        )
        db.session.add(new_request)
        db.session.commit()
        
        print(f"Asset request created with ID: {new_request.id}, Status: {new_request.status}, Team Lead ID: {new_request.team_lead_id}")
        
        return jsonify({'status': 'success', 'message': 'Indent request submitted successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})




# === Announcement API Endpoints ===
@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    try:
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        # Get user's roles
        user_roles = [role.name for role in user.roles]
        
        # Get all active announcements
        announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.created_at.desc()).all()
        
        # Get current time for expiry check
        current_time = datetime.now(indian_tz)
        
        announcement_list = []
        for announcement in announcements:
            # Check if announcement has expired
            if announcement.expires_at and announcement.expires_at < current_time:
                continue  # Skip expired announcements
            
            # Check if announcement is targeted to user's roles, specific users, or is general
            target_roles = json.loads(announcement.target_roles) if announcement.target_roles else []
            target_users = json.loads(announcement.target_users) if announcement.target_users else []
            
            # Show announcement if:
            # 1. No target roles and no target users (general announcement)
            # 2. User's role matches target roles
            # 3. User's email matches target users
            should_show = (
                (not target_roles and not target_users) or
                any(role in user_roles for role in target_roles) or
                user_email in target_users
            )
            
            if should_show:
                announcement_list.append({
                    'id': announcement.id,
                    'title': announcement.title,
                    'content': announcement.content,
                    'author_name': announcement.author.name,
                    'created_at': announcement.created_at.strftime('%Y-%m-%d %H:%M'),
                    'priority': announcement.priority,
                    'expires_at': announcement.expires_at.strftime('%Y-%m-%d %H:%M') if announcement.expires_at else None
                })
        
        return jsonify({'status': 'success', 'announcements': announcement_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/announcements', methods=['POST'])
def create_announcement():
    try:
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        # Check if user has admin or manager role
        user_roles = [role.name for role in user.roles]
        if not any(role in ['Admin', 'Manager', 'Team Lead'] for role in user_roles):
            return jsonify({'status': 'error', 'message': 'Insufficient permissions to create announcements'}), 403
        
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        priority = data.get('priority', 'Normal')
        target_roles = data.get('target_roles', [])
        target_users = data.get('target_users', [])
        expires_at_str = data.get('expires_at')
        
        if not title or not content:
            return jsonify({'status': 'error', 'message': 'Title and content are required'}), 400
        
        expires_at = None
        if expires_at_str:
            try:
                expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M')
            except ValueError:
                return jsonify({'status': 'error', 'message': 'Invalid date format for expires_at'}), 400
        
        new_announcement = Announcement(
            title=title,
            content=content,
            author_id=user.id,
            priority=priority,
            target_roles=json.dumps(target_roles),
            target_users=json.dumps(target_users),
            expires_at=expires_at
        )
        
        db.session.add(new_announcement)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Announcement created successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/announcements/<int:announcement_id>', methods=['PUT'])
def update_announcement(announcement_id):
    try:
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        announcement = Announcement.query.get(announcement_id)
        if not announcement:
            return jsonify({'status': 'error', 'message': 'Announcement not found'}), 404
        
        # Check if user is the author or has admin role
        user_roles = [role.name for role in user.roles]
        if announcement.author_id != user.id and 'Admin' not in user_roles:
            return jsonify({'status': 'error', 'message': 'Insufficient permissions to edit this announcement'}), 403
        
        data = request.get_json()
        
        if 'title' in data:
            announcement.title = data['title']
        if 'content' in data:
            announcement.content = data['content']
        if 'priority' in data:
            announcement.priority = data['priority']
        if 'target_roles' in data:
            announcement.target_roles = json.dumps(data['target_roles'])
        if 'target_users' in data:
            announcement.target_users = json.dumps(data['target_users'])
        if 'expires_at' in data:
            expires_at_str = data['expires_at']
            if expires_at_str:
                try:
                    announcement.expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M')
                except ValueError:
                    return jsonify({'status': 'error', 'message': 'Invalid date format for expires_at'}), 400
            else:
                announcement.expires_at = None
        
        announcement.updated_at = datetime.now(indian_tz)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Announcement updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/announcements/<int:announcement_id>', methods=['DELETE'])
def delete_announcement(announcement_id):
    try:
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        announcement = Announcement.query.get(announcement_id)
        if not announcement:
            return jsonify({'status': 'error', 'message': 'Announcement not found'}), 404
        
        # Check if user is the author or has admin role
        user_roles = [role.name for role in user.roles]
        if announcement.author_id != user.id and 'Admin' not in user_roles:
            return jsonify({'status': 'error', 'message': 'Insufficient permissions to delete this announcement'}), 403
        
        # Soft delete by setting is_active to False
        announcement.is_active = False
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Announcement deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/announcements/all', methods=['GET'])
def get_all_announcements():
    try:
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        # Check if user has admin or manager role
        user_roles = [role.name for role in user.roles]
        if not any(role in ['Admin', 'Manager', 'Team Lead'] for role in user_roles):
            return jsonify({'status': 'error', 'message': 'Insufficient permissions to view all announcements'}), 403
        
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
        
        announcement_list = []
        for announcement in announcements:
            target_users = json.loads(announcement.target_users) if announcement.target_users else []
                
            announcement_list.append({
                'id': announcement.id,
                'title': announcement.title,
                'content': announcement.content,
                'author_name': announcement.author.name,
                'created_at': announcement.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': announcement.updated_at.strftime('%Y-%m-%d %H:%M'),
                'priority': announcement.priority,
                'is_active': announcement.is_active,
                'target_roles': json.loads(announcement.target_roles) if announcement.target_roles else [],
                'target_users': target_users,
                'expires_at': announcement.expires_at.strftime('%Y-%m-%d %H:%M') if announcement.expires_at else None
            })
        
        return jsonify({'status': 'success', 'announcements': announcement_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === Birthday Alerts API ===
@app.route('/api/birthday_alerts', methods=['GET'])
def get_birthday_alerts():
    try:
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        # Get current date in Indian timezone
        current_date = datetime.now(indian_tz).date()
        
        # Get all employee info records with DOB
        all_employees = EmployeeInfo.query.filter(EmployeeInfo.dob.isnot(None)).all()
        
        birthday_alerts = []
        
        for emp in all_employees:
            if emp.dob:
                try:
                    # Parse DOB string (format might be YYYY-MM-DD or DD-MM-YYYY)
                    dob = None
                    for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y']:
                        try:
                            dob = datetime.strptime(emp.dob, fmt).date()
                            break
                        except ValueError:
                            continue
                    
                    if not dob:
                        continue
                    
                    # Calculate birthday for this year
                    birthday_this_year = dob.replace(year=current_date.year)
                    
                    # Calculate days difference
                    days_diff = (birthday_this_year - current_date).days
                    
                    # Show alert 2 days before (days_diff = 2 or 1) or on the day (days_diff = 0)
                    if days_diff == 0:
                        # Today is the birthday!
                        birthday_alerts.append({
                            'name': emp.full_name,
                            'email': emp.email,
                            'date': dob.strftime('%d %B'),
                            'is_today': True,
                            'message': f"Today is {emp.full_name}'s Birthday! Let's wish them! 🎉🎂"
                        })
                    elif days_diff == 1:
                        # Birthday is tomorrow
                        birthday_alerts.append({
                            'name': emp.full_name,
                            'email': emp.email,
                            'date': dob.strftime('%d %B'),
                            'is_today': False,
                            'message': f"{emp.full_name}'s Birthday is tomorrow ({birthday_this_year.strftime('%d %B')})! 🎈"
                        })
                    elif days_diff == 2:
                        # Birthday is in 2 days
                        birthday_alerts.append({
                            'name': emp.full_name,
                            'email': emp.email,
                            'date': dob.strftime('%d %B'),
                            'is_today': False,
                            'message': f"{emp.full_name}'s Birthday on {birthday_this_year.strftime('%d %B')}! 🎁"
                        })
                except Exception as e:
                    # Skip this employee if date parsing fails
                    continue
        
        return jsonify({'status': 'success', 'birthday_alerts': birthday_alerts})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- Create a new task in a personal project ---




@app.route('/api/change_password', methods=['POST'])
def change_password():
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        user_email = session.get('user')

        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not authenticated.'})

        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found.'})

        if not check_password_hash(user.password, current_password):
            return jsonify({'status': 'error', 'message': 'Incorrect current password.'})

        if len(new_password) < 6:
            return jsonify({'status': 'error', 'message': 'New password must be at least 6 characters long.'})

        user.password = generate_password_hash(new_password)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Password changed successfully.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    
@app.route('/api/asset_requests', methods=['GET'])
def get_user_asset_requests():
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
    
    requests = AssetRequest.query.filter_by(indenter_id=user.id).order_by(AssetRequest.request_date.desc()).all()
    requests_list = [{
        'id': req.id,
        'request_date': req.request_date.strftime('%Y-%m-%d'),
        'status': req.status
    } for req in requests]
    return jsonify({'status': 'success', 'requests': requests_list})

# app.py

@app.route('/api/my_pending_indents')
def get_my_pending_indents():
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
    
    user_roles = [r.name for r in user.roles]
    print(f"User: {user.name}, Email: {user_email}, Roles: {user_roles}")
    requests = []
    
    if 'Team Lead' in user_roles:
        team_lead_requests = AssetRequest.query.filter(AssetRequest.team_lead_id == user.id, AssetRequest.status.in_(['Pending TL Approval', 'Pending TL Final Approval'])).all()
        print(f"Team Lead requests found: {len(team_lead_requests)}")
        for req in team_lead_requests:
            print(f"  - Request {req.id}: Status={req.status}, Team Lead ID={req.team_lead_id}, User ID={user.id}")
        requests.extend(team_lead_requests)
        
    # --- MODIFIED: Include 'Pending Final Delivery' status for Procurement role ---
    if 'Procurement' in user_roles:
        procurement_requests = AssetRequest.query.filter(AssetRequest.status.in_(['Pending Procurement Approval', 'Pending Final Delivery', 'Pending Procurement Final Approval'])).all()
        print(f"Procurement requests found: {len(procurement_requests)}")
        requests.extend(procurement_requests)
    
    if 'Director' in user_roles:
        director_requests = AssetRequest.query.filter_by(status='Pending Director Approval').all()
        print(f"Director requests found: {len(director_requests)}")
        requests.extend(director_requests)
    
    if 'Managing Director' in user_roles:
        md_requests = AssetRequest.query.filter_by(status='Pending Managing Director Approval').all()
        print(f"MD requests found: {len(md_requests)}")
        requests.extend(md_requests)

    if 'Accounts' in user_roles:
        accounts_requests = AssetRequest.query.filter(AssetRequest.status.in_(['Pending Accounts Approval', 'Pending Accounts Final Approval'])).all()
        print(f"Accounts requests found: {len(accounts_requests)}")
        requests.extend(accounts_requests)
    
    unique_requests = {req.id: req for req in requests}.values()

    print(f"Total unique requests found: {len(unique_requests)}")
    for req in unique_requests:
        print(f"  - Request {req.id}: Status={req.status}, Team Lead ID={req.team_lead_id}")

    requests_list = [{
        'id': req.id,
        'request_date': req.request_date.strftime('%Y-%m-%d'),
        'indenter_name': req.indenter_name,
        'status': req.status
    } for req in unique_requests]
    
    return jsonify({'status': 'success', 'requests': requests_list})

@app.route('/api/my_approved_requests')
def get_my_approved_requests():
    """Get all requests that the current user has approved/reviewed based on their role"""
    try:
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'Please log in first'}), 401
            
        user = User.query.filter_by(email=session['user']).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        user_roles = [role.name for role in user.roles]
        print(f"User roles: {user_roles}")
        
        approved_requests = []
        
        # Get requests based on user's role and what they've approved
        if 'Team Lead' in user_roles:
            # Team Lead has approved requests that are no longer pending their approval
            team_lead_approved = AssetRequest.query.filter(
                AssetRequest.team_lead_id == user.id,
                ~AssetRequest.status.in_(['Pending TL Approval', 'Pending TL Final Approval'])
            ).all()
            approved_requests.extend(team_lead_approved)
        
        if 'Procurement' in user_roles:
            # Procurement has approved requests that have moved past procurement stages
            procurement_approved = AssetRequest.query.filter(
                ~AssetRequest.status.in_(['Pending Procurement Approval', 'Pending Final Delivery', 'Pending Procurement Final Approval'])
            ).all()
            approved_requests.extend(procurement_approved)
        
        if 'Director' in user_roles:
            # Director has approved requests that have moved past director approval
            director_approved = AssetRequest.query.filter(
                ~AssetRequest.status.in_(['Pending Director Approval'])
            ).all()
            approved_requests.extend(director_approved)
        
        if 'Managing Director' in user_roles:
            # Managing Director has approved requests that have moved past MD approval
            md_approved = AssetRequest.query.filter(
                ~AssetRequest.status.in_(['Pending Managing Director Approval'])
            ).all()
            approved_requests.extend(md_approved)
        
        if 'Accounts' in user_roles:
            # Accounts has approved requests that have moved past accounts approval
            accounts_approved = AssetRequest.query.filter(
                ~AssetRequest.status.in_(['Pending Accounts Approval', 'Pending Accounts Final Approval'])
            ).all()
            approved_requests.extend(accounts_approved)
        
        # Remove duplicates and sort by request date
        unique_requests = {req.id: req for req in approved_requests}.values()
        sorted_requests = sorted(unique_requests, key=lambda x: x.request_date, reverse=True)
        
        requests_list = []
        for req in sorted_requests:
            # Get indenter name
            indenter_name = req.indenter_name or "Unknown"
            
            # Get team lead name
            team_lead_name = "Unknown"
            if req.team_lead_id:
                team_lead = User.query.get(req.team_lead_id)
                if team_lead:
                    team_lead_name = team_lead.name
            
            # Get item details
            item_details = []
            if req.item_details:
                try:
                    item_details = json.loads(req.item_details) if isinstance(req.item_details, str) else req.item_details
                except:
                    item_details = []
            
            requests_list.append({
                'id': req.id,
                'request_date': req.request_date.strftime('%Y-%m-%d') if req.request_date else 'Unknown',
                'indenter_name': indenter_name,
                'team_lead_name': team_lead_name,
                'status': req.status,
                'item_details': item_details,
                'justification': req.justification or '',
                'procurement_type': req.procurement_type or '',
                'md_approval': getattr(req, 'md_approval', False),
                'md_comments': getattr(req, 'md_comments', '') or '',
                'accounts_approval': getattr(req, 'accounts_approval', False),
                'accounts_comments': getattr(req, 'accounts_comments', '') or '',
                'final_delivery_status': getattr(req, 'final_delivery_status', '') or '',
                'final_delivery_comments': getattr(req, 'final_delivery_comments', '') or ''
            })
        
        return jsonify({'status': 'success', 'requests': requests_list})
        
    except Exception as e:
        print(f"Error in get_my_approved_requests: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/debug_all_indents')
def debug_all_indents():
    """Debug endpoint to check all indents in database"""
    try:
        all_indents = AssetRequest.query.all()
        print(f"=== DEBUG: All indents in database ===")
        print(f"Total indents: {len(all_indents)}")
        
        indent_data = []
        for indent in all_indents:
            print(f"Indent {indent.id}: Status='{indent.status}', Team Lead ID={indent.team_lead_id}, Indenter='{indent.indenter_name}'")
            indent_data.append({
                'id': indent.id,
                'status': indent.status,
                'team_lead_id': indent.team_lead_id,
                'indenter_name': indent.indenter_name,
                'request_date': indent.request_date.strftime('%Y-%m-%d') if indent.request_date else 'N/A'
            })
        
        return jsonify({'status': 'success', 'indents': indent_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/debug_user_info')
def debug_user_info():
    """Debug endpoint to check current user info and roles"""
    try:
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        user_roles = [r.name for r in user.roles]
        print(f"=== DEBUG: Current User Info ===")
        print(f"User ID: {user.id}")
        print(f"User Name: {user.name}")
        print(f"User Email: {user.email}")
        print(f"User Roles: {user_roles}")
        
        return jsonify({
            'status': 'success', 
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'roles': user_roles
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/asset_requests/<int:request_id>', methods=['GET'])
def get_asset_request(request_id):
    req = AssetRequest.query.get(request_id)
    if not req:
        return jsonify({'status': 'error', 'message': 'Request not found'}), 404

    # The json.loads needs to be handled gracefully for empty/None values
    item_details = json.loads(req.item_details) if req.item_details else []
    procurement_items = json.loads(req.procurement_items) if req.procurement_items else []
    
    # Get team lead name if team lead ID exists
    team_lead_name = None
    if req.team_lead_id:
        team_lead = User.query.get(req.team_lead_id)
        if team_lead:
            team_lead_name = team_lead.name
    
    # Get project name if project ID exists
    project_name = None
    if req.project_id:
        project = Project.query.get(req.project_id)
        if project:
            project_name = project.project_name
    
    request_data = {
        'id': req.id,
        'indenter_id': req.indenter_id,
        'indenter_name': req.indenter_name,
        'office_project_type': req.office_project_type,
        'project_id': req.project_id,
        'team_lead_id': req.team_lead_id,
        'team_lead_name': team_lead_name,
        'project_name': project_name,
        'reference_file_no': req.reference_file_no,
        'purchase_type': req.purchase_type,
        'budget_head': req.budget_head,
        'nature_of_expenditure': req.nature_of_expenditure,
        'gst_applicable': req.gst_applicable,
        'item_details': item_details,
        'justification': req.justification,
        'procurement_items': procurement_items,
        'finalized_vendor': req.finalized_vendor,
        'approval_procurement': req.approval_procurement,
        'director_pi_approval': req.director_pi_approval,
        'director_pd_approval': req.director_pd_approval,
        'director_chairman_approval': req.director_chairman_approval,
        'director_comments': req.director_comments,
        'pi_approval': req.pi_approval,
        'pd_approval': req.pd_approval,
        'chairman_approval': req.chairman_approval,
        'chairman_comments': req.chairman_comments,
        'budget_allocation': req.budget_allocation,
        'budget_utilized': req.budget_utilized,
        'available_balance': req.available_balance,
        'funds_available': req.funds_available,
        'procurement_type': req.procurement_type,
        'account_no': req.account_no,
        'ifsc_code': req.ifsc_code,
        'branch_name': req.branch_name,
        'account_holder_name': req.account_holder_name,
        'handed_over_to': req.handed_over_to,
        'received_on': req.received_on,
        'discount_amount': req.discount_amount,
        'accounts_remarks': req.accounts_remarks,
        'request_date': req.request_date.strftime('%Y-%m-%d') if req.request_date else None,
        'status': req.status,
    }
    return jsonify({'status': 'success', 'request': request_data})

@app.route('/api/asset_requests/<int:request_id>/download', methods=['GET'])
def download_asset_request(request_id):
    """Download request details as PDF"""
    try:
        req = AssetRequest.query.get(request_id)
        if not req:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404

        # Check if user has permission to download
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

        user_roles = [role.name for role in user.roles]
        if 'Procurement' not in user_roles:
            return jsonify({'status': 'error', 'message': 'Access denied. Procurement role required.'}), 403

        # Parse item details
        item_details = json.loads(req.item_details) if req.item_details else []
        procurement_items = json.loads(req.procurement_items) if req.procurement_items else []

        # Create PDF content (simplified version - you can enhance this)
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("PURCHASE INDENT FORM", title_style))
        story.append(Spacer(1, 12))

        # Request details
        story.append(Paragraph(f"<b>Request ID:</b> {req.id}", styles['Normal']))
        story.append(Paragraph(f"<b>Indenter:</b> {req.indenter_name}", styles['Normal']))
        story.append(Paragraph(f"<b>Status:</b> {req.status}", styles['Normal']))
        story.append(Paragraph(f"<b>Created Date:</b> {req.request_date.strftime('%Y-%m-%d') if req.request_date else 'N/A'}", styles['Normal']))
        story.append(Spacer(1, 12))

        # Item details table
        if item_details:
            story.append(Paragraph("<b>Item Details:</b>", styles['Heading2']))
            story.append(Spacer(1, 6))
            
            # Create table data
            table_data = [['S.No', 'Item Name', 'Brand', 'Vendor', 'Cost', 'Qty', 'Tax', 'Total', 'Required By', 'Warranty', 'Remarks']]
            for i, item in enumerate(item_details, 1):
                table_data.append([
                    str(i),
                    item.get('name', 'N/A'),
                    item.get('brand', 'N/A'),
                    item.get('vendor', 'N/A'),
                    str(item.get('tentativeCost', 0)),
                    str(item.get('qty', 0)),
                    str(item.get('tax', 0)) + '%',
                    str(item.get('total', 0)),
                    item.get('requiredBy', 'N/A'),
                    item.get('warranty', 'N/A'),
                    item.get('remarks', 'N/A')
                ])
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

        # Discount and totals
        if req.discount_amount:
            story.append(Paragraph(f"<b>Discount Amount:</b> ₹{req.discount_amount}", styles['Normal']))
        
        # Calculate grand total
        grand_total = sum(float(item.get('total', 0)) for item in item_details)
        if req.discount_amount:
            grand_total -= float(req.discount_amount)
        story.append(Paragraph(f"<b>Grand Total:</b> ₹{grand_total:.2f}", styles['Normal']))

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        # Return PDF as response
        from flask import Response
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=request_{req.id}_{req.request_date.strftime("%Y%m%d") if req.request_date else "unknown"}.pdf'
            }
        )

    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/user/roles')
def api_get_user_roles():
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
    roles = [role.name for role in user.roles]
    return jsonify({'status': 'success', 'roles': roles})

@app.route('/api/project/<int:project_id>/tasks', methods=['POST'])
def create_project_task(project_id):
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    project = PersonalProject.query.filter_by(id=project_id, user_id=user.id).first()
    if not project:
        return jsonify({'status': 'error', 'message': 'Project not found or access denied'}), 404

    data = request.get_json()
    new_task = PersonalTask(
        name=data['name'],
        description=data.get('description'),
        deadline=data.get('deadline'),
        project_id=project_id
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Task created'})

# app.py

@app.route('/api/asset_requests/<int:request_id>/update', methods=['POST'])
def update_asset_request_status(request_id):
    try:
        req = AssetRequest.query.get(request_id)
        if not req:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
        
        data = request.get_json()
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
            
        user_roles = [role.name for role in user.roles]
        role = data.get('role')
        update_data = data.get('data')

        # --- Stage 1: Team Lead Justification ---
        if req.status == 'Pending TL Approval' and 'Team Lead' in user_roles and role == 'Team Lead':
            req.justification = update_data.get('justification')
            req.status = 'Pending Procurement Approval'
            # (Email notification logic for Procurement team here)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Request approved by Team Lead and sent to Procurement.'})

        # --- Stage 2: Procurement Details ---
        elif req.status == 'Pending Procurement Approval' and 'Procurement' in user_roles and role == 'Procurement':
            req.procurement_items = json.dumps(update_data.get('procurement_items'))
            req.status = 'Pending TL Final Approval'
            # (Email notification logic for Team Lead for final approval here)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Procurement details added and sent to Team Lead for final approval.'})

        # --- Stage 3: Team Lead Final Approval ---
        elif req.status == 'Pending TL Final Approval' and 'Team Lead' in user_roles and role == 'Team Lead':
            req.finalized_vendor = update_data.get('finalized_vendor')
            req.approval_procurement = update_data.get('approval_procurement')
            req.status = 'Pending Director Approval'
            # (Email notification logic for Director here)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Final approval by Team Lead received. Request is sent to Director.'})
            
        # --- Stage 4: Director Approval ---
        elif req.status == 'Pending Director Approval' and 'Director' in user_roles and role == 'Director':
            req.director_pi_approval = update_data.get('director_pi_approval', False)
            req.director_pd_approval = update_data.get('director_pd_approval', False)
            req.director_chairman_approval = update_data.get('director_chairman_approval', False)
            req.director_comments = update_data.get('director_comments')
            req.status = 'Pending Managing Director Approval'
            # (Email notification logic for managing director here)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Request approved by Director and sent to Managing Director.'})
            
        # --- Stage 5: MD Approval ---
        elif req.status == 'Pending Managing Director Approval' and 'Managing Director' in user_roles and role == 'Managing Director':
            req.pi_approval = update_data.get('pi_approval', False)
            req.pd_approval = update_data.get('pd_approval', False)
            req.chairman_approval = update_data.get('chairman_approval', False)
            req.chairman_comments = update_data.get('chairman_comments')
            req.status = 'Pending Procurement Final Approval'
            # (Email notification logic for Procurement team here)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Request approved by MD and sent to Procurement for final processing.'})

        # --- Stage 6: Procurement Final Processing ---
        elif req.status == 'Pending Procurement Final Approval' and 'Procurement' in user_roles and role == 'Procurement':
            req.procurement_type = update_data.get('procurementType') or update_data.get('procurement_type')
            req.account_no = update_data.get('accountNo') or update_data.get('account_no')
            req.ifsc_code = update_data.get('ifscCode') or update_data.get('ifsc_code')
            req.branch_name = update_data.get('branchName') or update_data.get('branch_name')
            req.account_holder_name = update_data.get('accountHolderName') or update_data.get('account_holder_name')
            req.status = 'Pending Accounts Approval'
            # (Email notification logic for Accounts team here)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Procurement details finalized and sent to Accounts.'})

        # --- Stage 7: Accounts Details (New Status Transition) ---
        elif req.status == 'Pending Accounts Approval' and 'Accounts' in user_roles and role == 'Accounts':
            req.budget_allocation = update_data.get('budgetAllocation')
            req.budget_utilized = update_data.get('budgetUtilized')
            req.available_balance = update_data.get('availableBalance')
            req.funds_available = update_data.get('fundsAvailable')
            req.procurement_type = update_data.get('procurementType')
            req.account_no = update_data.get('accountNo')
            req.ifsc_code = update_data.get('ifscCode')
            req.branch_name = update_data.get('branchName')
            req.account_holder_name = update_data.get('accountHolderName')
            req.status = 'Pending Final Delivery'
            db.session.commit()
            procurement_users = User.query.join(User.roles).filter(Role.name == 'Procurement').all()
            for proc_user in procurement_users:
                try:
                    msg = Message(
                        f"Asset Request {req.id} - Pending Final Delivery",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[proc_user.email]
                    )
                    msg.body = f"Hi {proc_user.name},\n\nAsset request (ID: {req.id}) has been approved by Accounts and is now ready for final delivery details. Please log in to the ERP dashboard to complete the process.\n\nThank you."
                    mail.send(msg)
                except Exception as e:
                    print(f"Error sending email to procurement for final delivery: {e}")

            return jsonify({'status': 'success', 'message': 'Accounts details finalized. Request is sent to Procurement for final delivery.'})

        # --- Stage 8: Final Delivery (Procurement) ---
        elif req.status == 'Pending Final Delivery' and 'Procurement' in user_roles and role == 'Procurement':
            req.handed_over_to = update_data.get('handed_over_to')
            req.received_on = update_data.get('received_on')
            req.status = 'Completed'
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Final delivery details recorded. Request is complete.'})
        
        return jsonify({'status': 'error', 'message': 'Invalid status, role, or action for this request.'}), 403
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

    
@app.route('/api/asset_requests/<int:request_id>/reject', methods=['POST'])
def reject_asset_request(request_id):
    try:
        req = AssetRequest.query.get(request_id)
        if not req:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
        
        data = request.get_json()
        role = data.get('role')
        comments = data.get('comments')
        
        user_email = session.get('user')
        user = User.query.filter_by(email=user_email).first()
        user_roles = [r.name for r in user.roles]

        # Check if the user has the correct role and the request is at the right stage for rejection
        if (role == 'Team Lead' and req.status == 'Pending TL Approval' and 'Team Lead' in user_roles) or \
           (role == 'Procurement' and req.status == 'Pending Procurement Approval' and 'Procurement' in user_roles) or \
           (role == 'Team Lead' and req.status == 'Pending TL Final Approval' and 'Team Lead' in user_roles) or \
           (role == 'Managing Director' and req.status == 'Pending Managing Director Approval' and 'Managing Director' in user_roles) or \
           (role == 'Accounts' and req.status == 'Pending Accounts Approval' and 'Accounts' in user_roles):
            req.status = f'Rejected by {role}'
            req.chairman_comments = comments
            db.session.commit()
            return jsonify({'status': 'success', 'message': f'Request rejected by {role}'})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid role or status for rejection'}), 403

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/task/<int:task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    user_email = session.get('user')
    user = User.query.filter_by(email=user_email).first()
    task = PersonalTask.query.join(PersonalProject).filter(PersonalTask.id == task_id, PersonalProject.user_id == user.id).first()
    
    if task:
        task.completed = not task.completed
        db.session.commit()
        return jsonify({'status': 'success', 'completed': task.completed})
    return jsonify({'status': 'error', 'message': 'Task not found or access denied'}), 404




##------salaries endpoints------
def _fetch_attendance_data_from_firestore(month_year_str, company):
    records = []
    try:
        docs = db_firestore.collection(month_year_str).stream()

        for doc in docs:
            # We assume your attendance data is in a subcollection named 'door_access'
            subcollection_ref = doc.reference.collection('door_access')
            sub_docs = subcollection_ref.stream()
            for sub_doc in sub_docs:
                sub_doc_data = sub_doc.to_dict()
                
                # Check for an exact match of the normalized branch name.
                if sub_doc_data.get('Branch', '').lower() == company.lower():
                    records.append(sub_doc_data)
        
        return records
    except Exception as e:
        print(f"Error fetching from Firestore for {month_year_str}: {e}")
        return None

@app.route('/api/download_attendance_report', methods=['GET'])
def download_attendance_report():
    try:
        report_type = request.args.get('report_type')
        date_str = request.args.get('date') # This will be in 'YYYY-MM-DD' format
        company = request.args.get('company')
        
        if not all([report_type, date_str, company]):
            return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400

        records = []
        if report_type == 'day':
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            month_year_str = date_obj.strftime("%B_%Y").lower()
            all_records = _fetch_attendance_data_from_firestore(month_year_str, company)
            if all_records:
                # Filter for the specific date after fetching all records for the month
                records = [r for r in all_records if r.get('date_key') == date_str]

        elif report_type == 'month':
            date_obj = datetime.strptime(date_str, "%Y-%m")
            month_year_str = date_obj.strftime("%B_%Y").lower()
            records = _fetch_attendance_data_from_firestore(month_year_str, company)

        elif report_type == 'year':
            year = date_str
            month_names = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
            for month in month_names:
                month_year_str = f"{month}_{year}"
                monthly_records = _fetch_attendance_data_from_firestore(month_year_str, company)
                if monthly_records:
                    records.extend(monthly_records)

        if not records:
            return jsonify({'status': 'error', 'message': f'No attendance data found for {company.upper()} on the selected date range.'}), 404
        
        df = pd.DataFrame(records)
        df = df.fillna('')
        
        # Format the DataFrame for the report
        desired_columns = ['Name', 'Branch', 'Designation', 'open_time_ist', 'close_time_ist', 'status', 'date_key']
        df = df.reindex(columns=desired_columns, fill_value='')
        df.rename(columns={
            'open_time_ist': 'Check-In Time',
            'close_time_ist': 'Check-Out Time',
            'status': 'Status',
            'date_key': 'Date'
        }, inplace=True)
        
        # Create PDF using reportlab
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name
        
        # Create PDF document
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.HexColor('#007bff')
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=1,  # Center alignment
        )
        
        # Add title and subtitle
        story.append(Paragraph(f"{company.upper()} Attendance Report", title_style))
        story.append(Paragraph(f"Report for: {date_str}", subtitle_style))
        story.append(Spacer(1, 20))
        
        # Prepare table data
        table_data = [df.columns.tolist()]  # Header row
        for _, row in df.iterrows():
            table_data.append(row.tolist())
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
        
        # Build PDF
        doc.build(story)

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"{company.upper()}_Attendance_Report_{date_str}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({'status': 'error', 'message': f'Failed to generate report: {str(e)}'}), 500

















@app.route('/api/get_employee_salary_info/<int:employee_id>', methods=['GET'])
def get_employee_salary_info(employee_id):
    # Change 'Employee' to 'EmployeeInfo'
    employee_info = EmployeeInfo.query.filter_by(user_id=employee_id).first()
    
    if employee_info:
        # Assuming salary details are stored as a JSON string
        salary_info = json.loads(employee_info.salary_details) if employee_info.salary_details else {}

        # You also need to get the designation from the User's roles
        user = User.query.get(employee_id)
        designation = user.roles[0].name if user and user.roles else "N/A"

        return jsonify({
            "status": "success",
            "employee": {
                "id": employee_info.user_id,
                "name": employee_info.full_name,
                "email": employee_info.email,
                "designation": designation,
                "account_number": employee_info.account_number,
                "salary_details": salary_info
            }
        })
    # If no EmployeeInfo record is found, still provide a response for the user
    user = User.query.get(employee_id)
    if user:
        return jsonify({
            "status": "success",
            "employee": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "designation": user.roles[0].name if user.roles else "N/A",
                "account_number": "N/A",
                "salary_details": {}
            }
        })
    
    return jsonify({"status": "error", "message": "Employee not found"}), 404

@app.route('/api/update_employee_salary', methods=['POST'])
def update_employee_salary():
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        salary_data = data.get('salary_data', {})
        
        
        if not employee_id:
            return jsonify({"status": "error", "message": "Employee ID is required"}), 400
        
        # Find the employee info record
        # The frontend sends the EmployeeInfo.id, not user_id
        employee_info = EmployeeInfo.query.get(employee_id)
        
        if not employee_info:
            return jsonify({"status": "error", "message": "Employee not found"}), 404
        
        # Update salary fields (Actuals - keep original values)
        employee_info.actual_gross_salary = salary_data.get('actual_gross_salary', employee_info.actual_gross_salary)
        
        # Update Earnings fields (what's actually being paid)
        employee_info.earnings_basic = salary_data.get('basic', employee_info.earnings_basic)
        employee_info.earnings_hra = salary_data.get('hra', employee_info.earnings_hra)
        employee_info.earnings_conveyance = salary_data.get('conveyance', employee_info.earnings_conveyance)
        employee_info.earnings_vehicle_maintenance = salary_data.get('vehicle_maintenance', employee_info.earnings_vehicle_maintenance)
        employee_info.earnings_special_allowance = salary_data.get('special_allowance', employee_info.earnings_special_allowance)
        employee_info.earnings_add_others = salary_data.get('add_others', employee_info.earnings_add_others)
        
        employee_info.provident_fund = salary_data.get('provident_fund', employee_info.provident_fund)
        employee_info.esi = salary_data.get('esi', employee_info.esi)
        employee_info.professional_tax = salary_data.get('professional_tax', employee_info.professional_tax)
        employee_info.income_tax = salary_data.get('income_tax', employee_info.income_tax)
        employee_info.advance = salary_data.get('advance', employee_info.advance)
        employee_info.other_deductions = salary_data.get('other_deductions', employee_info.other_deductions)
        employee_info.loss_of_pay = salary_data.get('loss_of_pay', employee_info.loss_of_pay)
        employee_info.total_leaves = salary_data.get('total_leaves', employee_info.total_leaves)
        employee_info.leave_availed = salary_data.get('leave_availed', employee_info.leave_availed)
        employee_info.balance_leaves = salary_data.get('balance_leaves', employee_info.balance_leaves)
        employee_info.no_of_lop_days = salary_data.get('no_of_lop_days', employee_info.no_of_lop_days)
        employee_info.total_days = salary_data.get('total_days', employee_info.total_days)
        employee_info.ndp = salary_data.get('ndp', employee_info.ndp)
        
        # Save to database
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Salary data updated successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Error updating salary data: {str(e)}"
        }), 500






# === Task Management API Endpoints ===

@app.route('/api/assign_task', methods=['POST'])
def assign_task():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Check if user is a Team Lead
        user_roles = [r.name for r in user.roles]
        if 'Team Lead' not in user_roles:
            return jsonify({'status': 'error', 'message': 'Only Team Leads can assign tasks'}), 403
        
        data = request.get_json()
        task_name = data.get('task_name')
        assigned_to_id = data.get('assigned_to_id')
        
        if not task_name or not assigned_to_id:
            return jsonify({'status': 'error', 'message': 'Task name and assigned user are required'}), 400
        
        # Verify assigned user exists
        assigned_user = User.query.get(assigned_to_id)
        if not assigned_user:
            return jsonify({'status': 'error', 'message': 'Assigned user not found'}), 404
        
        # Create new task
        new_task = Task(
            task_name=task_name,
            assigned_by_id=user.id,
            assigned_to_id=assigned_to_id,
            status='Pending'
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Task assigned successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/assigned_tasks')
def get_assigned_tasks():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Check if user is a Team Lead
        user_roles = [r.name for r in user.roles]
        if 'Team Lead' not in user_roles:
            return jsonify({'status': 'error', 'message': 'Only Team Leads can view assigned tasks'}), 403
        
        # Get tasks assigned by this user
        tasks = Task.query.filter_by(assigned_by_id=user.id).all()
        
        task_list = []
        for task in tasks:
            task_list.append({
                'id': task.id,
                'task_name': task.task_name,
                'assigned_to_name': task.assigned_to.name,
                'assigned_to_email': task.assigned_to.email,
                'status': task.status,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M'),
                'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else None
            })
        
        return jsonify({'status': 'success', 'tasks': task_list})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/my_assigned_tasks')
def get_my_assigned_tasks():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Get tasks assigned to this user
        tasks = Task.query.filter_by(assigned_to_id=user.id).all()
        
        task_list = []
        for task in tasks:
            task_list.append({
                'id': task.id,
                'task_name': task.task_name,
                'assigned_by_name': task.assigned_by.name,
                'assigned_by_email': task.assigned_by.email,
                'status': task.status,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M'),
                'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else None
            })
        
        return jsonify({'status': 'success', 'tasks': task_list})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'status': 'error', 'message': 'Task not found'}), 404
        
        # Check if user is assigned to this task
        if task.assigned_to_id != user.id:
            return jsonify({'status': 'error', 'message': 'You can only complete tasks assigned to you'}), 403
        
        # Update task status
        task.status = 'Completed'
        task.completed_at = datetime.now(indian_tz)
        
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Task completed successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/active_users_for_tasks')
def get_active_users_for_tasks():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Check if user is a Team Lead
        user_roles = [r.name for r in user.roles]
        if 'Team Lead' not in user_roles:
            return jsonify({'status': 'error', 'message': 'Only Team Leads can view user list'}), 403
        
        # Get all active users except the current user
        users = User.query.filter(User.id != user.id, User.is_deleted == False).all()
        
        user_list = []
        for u in users:
            user_list.append({
                'id': u.id,
                'name': u.name,
                'email': u.email,
                'roles': [r.name for r in u.roles]
            })
        
        return jsonify({'status': 'success', 'users': user_list})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === Dashboard API Endpoints ===

@app.route('/api/dashboard/task_counts')
def get_dashboard_task_counts():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        user_roles = [r.name for r in user.roles]
        
        if 'Team Lead' in user_roles:
            # For Team Leads: count tasks they assigned to others
            total_tasks = Task.query.filter_by(assigned_by_id=user.id).count()
            pending_tasks = Task.query.filter_by(assigned_by_id=user.id, status='Pending').count()
        else:
            # For Employees: count tasks assigned to them
            total_tasks = Task.query.filter_by(assigned_to_id=user.id).count()
            pending_tasks = Task.query.filter_by(assigned_to_id=user.id, status='Pending').count()
        
        return jsonify({
            'status': 'success',
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/dashboard/project_counts')
def get_dashboard_project_counts():
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Get unique projects from user's groups (this matches what "My Tasks" shows)
        user_groups = user.groups
        unique_projects = set()
        
        for group in user_groups:
            unique_projects.add(group.project.id)
        
        total_projects = len(unique_projects)
        
        return jsonify({
            'status': 'success',
            'total_projects': total_projects
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === Project Task Management API Endpoints ===

@app.route('/api/project/<int:project_id>/personal_tasks')
def get_project_personal_tasks(project_id):
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Verify project exists and belongs to user
        project = PersonalProject.query.filter_by(id=project_id, user_id=user.id).first()
        if not project:
            return jsonify({'status': 'error', 'message': 'Project not found'}), 404
        
        # Get personal tasks for this project
        tasks = PersonalTask.query.filter_by(project_id=project_id).all()
        
        task_list = []
        for task in tasks:
            task_list.append({
                'id': task.id,
                'task_name': task.name,
                'deadline': task.deadline,
                'is_completed': task.completed,
                'created_at': None,  # PersonalTask doesn't have created_at
                'completed_at': None  # PersonalTask doesn't have completed_at
            })
        
        return jsonify({'status': 'success', 'tasks': task_list})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/project/<int:project_id>/add_personal_task', methods=['POST'])
def add_project_personal_task(project_id):
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        data = request.get_json()
        task_name = data.get('task_name')
        deadline = data.get('deadline')
        
        if not task_name:
            return jsonify({'status': 'error', 'message': 'Task name is required'}), 400
        
        # Verify project exists and belongs to user
        project = PersonalProject.query.filter_by(id=project_id, user_id=user.id).first()
        if not project:
            return jsonify({'status': 'error', 'message': 'Project not found'}), 404
        
        # Create new personal task
        new_task = PersonalTask(
            name=task_name,
            deadline=deadline,
            project_id=project_id,
            completed=False
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Task added successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/personal_project_task/<int:task_id>/toggle', methods=['POST'])
def toggle_personal_project_task(task_id):
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        task = ProjectTask.query.get(task_id)
        if not task:
            return jsonify({'status': 'error', 'message': 'Task not found'}), 404
        
        # Check if user owns this task
        if task.user_id != user.id:
            return jsonify({'status': 'error', 'message': 'You can only modify your own tasks'}), 403
        
        # Toggle completion status
        task.is_completed = not task.is_completed
        if task.is_completed:
            task.completed_at = datetime.now(indian_tz)
        else:
            task.completed_at = None
        
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Task status updated'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === Database Migration Function ===
def migrate_database():
    """Safely migrate database by adding missing columns"""
    with app.app_context():
        # Check if total_days column exists in employee_info table
        inspector = inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('employee_info')]
        
        if 'total_days' not in columns:
            print("Adding total_days column to employee_info table...")
            try:
                # Add the new column with a default value using text() for raw SQL
                db.session.execute(text('ALTER TABLE employee_info ADD COLUMN total_days INTEGER DEFAULT 30'))
                db.session.commit()
                print("✅ Successfully added total_days column!")
            except Exception as e:
                print(f"❌ Error adding total_days column: {e}")
                db.session.rollback()
        else:
            print("✅ total_days column already exists!")

if __name__ == '__main__':
    with app.app_context():
        # Run migration first
        migrate_database()
        db.create_all()

        # Add default roles if they don't exist
        default_roles = ['Admin', 'CEO', 'CTO', 'CFO', 'Director', 'Manager', 'Employee', 'Accounts', 'Finance', 'Procurement', 'Team Lead', 'HR', 'Managing Director']
        for role_name in default_roles:
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name))
        db.session.commit()
        
        # Add Evaluation permission to appropriate roles
        evaluation_roles = ['Employee', 'Team Lead', 'HR', 'Director', 'Managing Director', 'Admin']
        for role_name in evaluation_roles:
            role_perms = RolePermissions.query.filter_by(role_name=role_name).first()
            if role_perms:
                # Add Evaluation to existing permissions
                existing_perms = role_perms.permissions.split(',') if role_perms.permissions else []
                if 'Evaluation' not in existing_perms:
                    existing_perms.append('Evaluation')
                    role_perms.permissions = ','.join(filter(None, existing_perms))
            else:
                # Create new role permissions with Evaluation
                db.session.add(RolePermissions(role_name=role_name, permissions='Evaluation'))
        db.session.commit()

        # Check for and create the default admin user
        admin_email = 'admin@ssev.co.in'
        admin_password = 'admin@1234'
        admin_user = User.query.filter_by(email=admin_email).first()

        if not admin_user:
            # Hash the password before saving it to the database
            hashed_password = generate_password_hash(admin_password)
            new_admin = User(
                name='Admin User',
                username='admin',
                email=admin_email,
                password=hashed_password,
                created_by_admin=True
            )
            
            # Assign the 'Admin' role to the new user
            admin_role = Role.query.filter_by(name='Admin').first()
            if admin_role:
                new_admin.roles.append(admin_role)
            
            db.session.add(new_admin)
            db.session.commit()
            print('Default admin user created with email: admin@ssev.co.in and password: admin@1234')
        else:
            print('Default admin user already exists.')

# === Holiday Management Routes ===
@app.route('/api/holidays', methods=['GET'])
def get_holidays():
    try:
        holidays = Holiday.query.order_by(Holiday.date.asc()).all()
        holidays_data = []
        for holiday in holidays:
            holidays_data.append({
                'id': holiday.id,
                'name': holiday.name,
                'date': holiday.date,
                'created_by': holiday.creator.name if holiday.creator else 'Unknown',
                'created_at': holiday.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        return jsonify({'status': 'success', 'holidays': holidays_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/holidays', methods=['POST'])
def add_holiday():
    try:
        data = request.get_json()
        name = data.get('name')
        date = data.get('date')
        
        if not name or not date:
            return jsonify({'status': 'error', 'message': 'Name and date are required'}), 400
        
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        # Check if user has permission (Admin or HR)
        user = User.query.filter_by(email=session['user']).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        user_roles = [role.name for role in user.roles]
        if 'Admin' not in user_roles and 'HR' not in user_roles:
            return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
        
        # Allow multiple holidays on the same date
        
        # Create new holiday
        holiday = Holiday(
            name=name,
            date=date,
            created_by=user.id
        )
        
        db.session.add(holiday)
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': 'Holiday added successfully',
            'holiday': {
                'id': holiday.id,
                'name': holiday.name,
                'date': holiday.date,
                'created_by': user.name,
                'created_at': holiday.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/holidays/<int:holiday_id>', methods=['DELETE'])
def delete_holiday(holiday_id):
    try:
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        # Check if user has permission (Admin or HR)
        user = User.query.filter_by(email=session['user']).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        user_roles = [role.name for role in user.roles]
        if 'Admin' not in user_roles and 'HR' not in user_roles:
            return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
        
        # Find and delete holiday
        holiday = Holiday.query.get(holiday_id)
        if not holiday:
            return jsonify({'status': 'error', 'message': 'Holiday not found'}), 404
        
        db.session.delete(holiday)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Holiday deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === EVALUATION ROUTES ===
@app.route('/evaluation/start')
def evaluation_start():
    """Start evaluation report page"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(email=session['user']).first()
    if not user:
        return redirect(url_for('login'))
    
    return render_template('evaluation_start.html', username=user.name, user_id=user.id)

@app.route('/evaluation/evaluate')
def evaluation_evaluate():
    """Evaluate reports page for Team Leads, HR, Director, MD"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(email=session['user']).first()
    if not user:
        return redirect(url_for('login'))
    
    return render_template('evaluation_evaluate.html', username=user.name, user_id=user.id)

@app.route('/test_md_data')
def test_md_data():
    """Test page for MD data"""
    return send_file('test_md_data.html')

@app.route('/api/evaluation/user_info/<int:user_id>')
def get_evaluation_user_info(user_id):
    """Get user information for evaluation form"""
    try:
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        # Get user info
        user = User.query.get(user_id)
        if not user:
            return jsonify({'status': 'error', 'message': f'User not found with ID: {user_id}'}), 404
        
        # Get employee info if exists
        employee_info = EmployeeInfo.query.filter_by(user_id=user_id).first()
        
        # Determine employment status based on dates
        employment_status = 'Not specified'
        status_duration = 'Not specified'
        
        if employee_info:
            if employee_info.probation_from and employee_info.probation_to:
                employment_status = 'Probation'
                status_duration = f"{employee_info.probation_from} to {employee_info.probation_to}"
            elif employee_info.confirmation_date:
                employment_status = 'Confirmation'
                status_duration = str(employee_info.confirmation_date)
            elif employee_info.date_of_joining:
                employment_status = 'Internship'
                status_duration = f"From {employee_info.date_of_joining}"
        
        user_data = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'position': employee_info.designation if employee_info else 'Not specified',
            'contact_number': employee_info.phone_no if employee_info else 'Not specified',
            'office_branch': employee_info.office_branch if employee_info else 'Not specified',
            'employee_id': employee_info.employee_id if employee_info else 'Not specified',
            'employment_status': employment_status,
            'status_duration': status_duration,
            'salary': employee_info.actual_gross_salary if employee_info else 0
        }
        
        return jsonify({'status': 'success', 'user': user_data})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/evaluation/team_leads')
def get_evaluation_team_leads():
    """Get active team leads for dropdown"""
    try:
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        # Get users with Team Lead role
        team_leads = User.query.join(User.roles).filter(Role.name == 'Team Lead').all()
        
        team_lead_data = []
        for tl in team_leads:
            team_lead_data.append({
                'id': tl.id,
                'name': tl.name,
                'email': tl.email
            })
        
        return jsonify({'status': 'success', 'team_leads': team_lead_data})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/evaluation/submit', methods=['POST'])
def submit_evaluation():
    """Submit evaluation report"""
    try:
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        data = request.get_json()
        user_email = session['user']
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Create evaluation report
        evaluation_report = EvaluationReport(
            employee_id=user.id,
            team_lead_id=data.get('team_lead_id'),
            status='Employee has Submitted',
            name=data.get('name'),
            position=data.get('position'),
            contact_number=data.get('contact_number'),
            email_id=data.get('email_id'),
            office_branch=data.get('office_branch'),
            employee_id_str=data.get('employee_id'),
            employment_status=data.get('employment_status'),
            status_duration=data.get('status_duration'),
            salary=data.get('salary')
        )
        
        db.session.add(evaluation_report)
        db.session.flush()  # Get the ID
        
        # Create self-evaluation response (Page 2)
        self_evaluation = EvaluationResponse(
            evaluation_report_id=evaluation_report.id,
            evaluator_id=user.id,
            evaluator_role='Employee',
            page_number=2,
            attendance_score=data.get('attendance_score'),
            attendance_comments=data.get('attendance_comments'),
            discipline_score=data.get('discipline_score'),
            discipline_comments=data.get('discipline_comments'),
            knowledge_skills_score=data.get('knowledge_skills_score'),
            knowledge_skills_comments=data.get('knowledge_skills_comments'),
            quality_work_score=data.get('quality_work_score'),
            quality_work_comments=data.get('quality_work_comments'),
            teamwork_score=data.get('teamwork_score'),
            teamwork_comments=data.get('teamwork_comments'),
            work_consistency_score=data.get('work_consistency_score'),
            work_consistency_comments=data.get('work_consistency_comments'),
            thinking_process_score=data.get('thinking_process_score'),
            thinking_process_comments=data.get('thinking_process_comments'),
            communication_score=data.get('communication_score'),
            communication_comments=data.get('communication_comments'),
            initiative_score=data.get('initiative_score'),
            initiative_comments=data.get('initiative_comments'),
            motivation_score=data.get('motivation_score'),
            motivation_comments=data.get('motivation_comments'),
            creativity_score=data.get('creativity_score'),
            creativity_comments=data.get('creativity_comments'),
            honesty_score=data.get('honesty_score'),
            honesty_comments=data.get('honesty_comments'),
            overall_rating_score=data.get('overall_rating_score'),
            overall_rating_comments=data.get('overall_rating_comments'),
            signature=data.get('signature'),
            evaluator_name=data.get('evaluator_name'),
            evaluation_date=datetime.strptime(data.get('evaluation_date'), '%Y-%m-%d').date() if data.get('evaluation_date') else None
        )
        
        db.session.add(self_evaluation)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Evaluation submitted successfully', 'evaluation_id': evaluation_report.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/evaluation/reports')
def get_evaluation_reports():
    """Get evaluation reports for current user based on role"""
    try:
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        user_email = session['user']
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Get user roles
        user_roles = [role.name for role in user.roles]
        
        reports = []
        report_ids = set()  # To avoid duplicates
        
        # Show ALL reports that the user has access to based on their roles
        # The form type will be determined by the report status when opened
        
        # Team Lead reports: Reports assigned to user as Team Lead with status 'Employee has Submitted' or 'Team Lead has Reviewed'
        if 'Team Lead' in user_roles:
            team_lead_reports = EvaluationReport.query.filter(
                (EvaluationReport.team_lead_id == user.id) & 
                (EvaluationReport.status.in_(['Employee has Submitted', 'Team Lead has Reviewed']))
            ).all()
            for report in team_lead_reports:
                if report.id not in report_ids:
                    reports.append(report)
                    report_ids.add(report.id)
        
        # HR reports: Reports with status 'Team Lead has Reviewed' (not assigned to user as Team Lead) 
        # and reports that HR has already submitted
        if 'HR' in user_roles:
            hr_reports = EvaluationReport.query.filter(
                ((EvaluationReport.status == 'Team Lead has Reviewed') & (EvaluationReport.team_lead_id != user.id)) |
                (EvaluationReport.status == 'HR has Reviewed')
            ).all()
            for report in hr_reports:
                if report.id not in report_ids:
                    reports.append(report)
                    report_ids.add(report.id)
        
        # Director reports: Reports with status 'HR has Reviewed' or 'Completed' (including those assigned to user as Team Lead but moved beyond Team Lead stage)
        # and reports that Director has already submitted
        if 'Director' in user_roles:
            director_reports = EvaluationReport.query.filter(
                (EvaluationReport.status.in_(['HR has Reviewed', 'Completed', 'Director has Reviewed']))
            ).all()
            for report in director_reports:
                if report.id not in report_ids:
                    reports.append(report)
                    report_ids.add(report.id)
        
        # Fourth priority: Managing Director (only if no other reports)
        if is_managing_director(user_roles) and not reports:
            md_reports = EvaluationReport.query.filter_by(status='Director has Reviewed').all()
            if md_reports:
                reports = md_reports
        
        # Last priority: Employee (always show their own reports)
        if 'Employee' in user_roles and not reports:
            employee_reports = EvaluationReport.query.filter_by(employee_id=user.id).all()
            if employee_reports:
                reports = employee_reports
        
        report_data = []
        for report in reports:
            report_data.append({
                'id': report.id,
                'employee_name': report.name,
                'position': report.position,
                'status': report.status,
                'created_at': report.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': report.updated_at.strftime('%Y-%m-%d %H:%M'),
                'team_lead_id': report.team_lead_id,
                'employee_id': report.employee_id,
                'user_roles': user_roles,
                'current_user_id': user.id
            })
        
        return jsonify({'status': 'success', 'reports': report_data})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/evaluation/report/<int:report_id>')
def get_evaluation_report(report_id):
    """Get specific evaluation report details with all previous evaluations"""
    try:
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        user_email = session['user']
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Get the evaluation report
        report = EvaluationReport.query.get(report_id)
        if not report:
            return jsonify({'status': 'error', 'message': 'Report not found'}), 404
        
        # Check if user has permission to view this report
        user_roles = [role.name for role in user.roles]
        can_view = False
        
        # Allow access based on user roles and report assignment/status
        
        # Team Lead access: Reports assigned to user as Team Lead (any status)
        if 'Team Lead' in user_roles and report.team_lead_id == user.id:
            can_view = True
        # HR access: Reports with status 'Team Lead has Reviewed' (not assigned to user as Team Lead) or 'HR has Reviewed' (HR's own submissions)
        elif 'HR' in user_roles and ((report.status == 'Team Lead has Reviewed' and report.team_lead_id != user.id) or report.status == 'HR has Reviewed'):
            can_view = True
        # Director access: Reports with status 'HR has Reviewed' or 'Completed' (not assigned to user as Team Lead) or 'Director has Reviewed' (Director's own submissions)
        elif 'Director' in user_roles and ((report.status in ['HR has Reviewed', 'Completed'] and report.team_lead_id != user.id) or report.status == 'Director has Reviewed'):
            can_view = True
        # Fourth priority: Managing Director (only if not previous cases)
        elif is_managing_director(user_roles) and report.status == 'Director has Reviewed':
            can_view = True
        # Last priority: Employee (always allow access to their own reports)
        elif 'Employee' in user_roles and report.employee_id == user.id:
            can_view = True
        
        if not can_view:
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Get all evaluation responses for this report
        responses = EvaluationResponse.query.filter_by(evaluation_report_id=report_id).all()
        
        # Organize responses by page number
        evaluations = {}
        for response in responses:
            evaluations[response.page_number] = {
                'evaluator_role': response.evaluator_role,
                'evaluator_name': response.evaluator_name,
                'evaluation_date': response.evaluation_date.strftime('%Y-%m-%d') if response.evaluation_date else None,
                'signature': response.signature,
                'attendance_score': response.attendance_score,
                'attendance_comments': response.attendance_comments,
                'discipline_score': response.discipline_score,
                'discipline_comments': response.discipline_comments,
                'knowledge_skills_score': response.knowledge_skills_score,
                'knowledge_skills_comments': response.knowledge_skills_comments,
                'quality_work_score': response.quality_work_score,
                'quality_work_comments': response.quality_work_comments,
                'teamwork_score': response.teamwork_score,
                'teamwork_comments': response.teamwork_comments,
                'work_consistency_score': response.work_consistency_score,
                'work_consistency_comments': response.work_consistency_comments,
                'thinking_process_score': response.thinking_process_score,
                'thinking_process_comments': response.thinking_process_comments,
                'communication_score': response.communication_score,
                'communication_comments': response.communication_comments,
                'initiative_score': response.initiative_score,
                'initiative_comments': response.initiative_comments,
                'motivation_score': response.motivation_score,
                'motivation_comments': response.motivation_comments,
                'creativity_score': response.creativity_score,
                'creativity_comments': response.creativity_comments,
                'honesty_score': response.honesty_score,
                'honesty_comments': response.honesty_comments,
                'overall_rating_score': response.overall_rating_score,
                'overall_rating_comments': response.overall_rating_comments,
                # HR specific fields
                'commitment_work_score': response.commitment_work_score,
                'commitment_work_comments': response.commitment_work_comments,
                'work_attitude_score': response.work_attitude_score,
                'work_attitude_comments': response.work_attitude_comments,
                'team_orientation_score': response.team_orientation_score,
                'team_orientation_comments': response.team_orientation_comments,
                'integrity_honesty_score': response.integrity_honesty_score,
                'integrity_honesty_comments': response.integrity_honesty_comments,
                'productivity_score': response.productivity_score,
                'productivity_comments': response.productivity_comments,
                'punctuality_score': response.punctuality_score,
                'punctuality_comments': response.punctuality_comments,
                'physical_disposition_score': response.physical_disposition_score,
                'physical_disposition_comments': response.physical_disposition_comments,
                'overall_hr_score': response.overall_hr_score,
                'overall_hr_comments': response.overall_hr_comments,
                # Director/MD specific fields
                'stability_score': response.stability_score,
                'stability_comments': response.stability_comments,
                # MD specific fields
                'further_action_hold': response.further_action_hold,
                'further_action_next_round': response.further_action_next_round,
                'suitable_yes': response.suitable_yes,
                'suitable_no': response.suitable_no,
                'project_assignment': response.project_assignment,
                'area_assignment': response.area_assignment
            }
        
        report_data = {
            'id': report.id,
            'name': report.name,
            'position': report.position,
            'contact_number': report.contact_number,
            'email_id': report.email_id,
            'office_branch': report.office_branch,
            'employee_id_str': report.employee_id_str,
            'employment_status': report.employment_status,
            'status_duration': report.status_duration,
            'salary': report.salary,
            'status': report.status,
            'team_lead_id': report.team_lead_id,
            'employee_id': report.employee_id,
            'created_at': report.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': report.updated_at.strftime('%Y-%m-%d %H:%M'),
            'evaluations': evaluations,
            'user_roles': user_roles
        }
        
        return jsonify({'status': 'success', 'report': report_data})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/evaluation/submit_response', methods=['POST'])
def submit_evaluation_response():
    """Submit evaluation response (Team Lead, HR, Director, MD)"""
    try:
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401
        
        data = request.get_json()
        user_email = session['user']
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Get the evaluation report
        report = EvaluationReport.query.get(data.get('evaluation_report_id'))
        if not report:
            return jsonify({'status': 'error', 'message': 'Report not found'}), 404
        
        # Check if user has permission to evaluate this report
        user_roles = [role.name for role in user.roles]
        evaluator_role = data.get('evaluator_role')
        page_number = data.get('page_number')
        
        can_evaluate = False
        # Check roles in order of priority (highest authority first)
        if evaluator_role == 'Managing Director' and is_managing_director(user_roles):
            can_evaluate = True
        elif evaluator_role == 'Director' and 'Director' in user_roles:
            can_evaluate = True
        elif evaluator_role == 'HR' and 'HR' in user_roles:
            can_evaluate = True
        elif evaluator_role == 'Team Lead' and 'Team Lead' in user_roles and report.team_lead_id == user.id:
            can_evaluate = True
        
        if not can_evaluate:
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Create evaluation response
        evaluation_response = EvaluationResponse(
            evaluation_report_id=report.id,
            evaluator_id=user.id,
            evaluator_role=evaluator_role,
            page_number=page_number,
            attendance_score=data.get('attendance_score'),
            attendance_comments=data.get('attendance_comments'),
            discipline_score=data.get('discipline_score'),
            discipline_comments=data.get('discipline_comments'),
            knowledge_skills_score=data.get('knowledge_skills_score'),
            knowledge_skills_comments=data.get('knowledge_skills_comments'),
            quality_work_score=data.get('quality_work_score'),
            quality_work_comments=data.get('quality_work_comments'),
            teamwork_score=data.get('teamwork_score'),
            teamwork_comments=data.get('teamwork_comments'),
            work_consistency_score=data.get('work_consistency_score'),
            work_consistency_comments=data.get('work_consistency_comments'),
            thinking_process_score=data.get('thinking_process_score'),
            thinking_process_comments=data.get('thinking_process_comments'),
            communication_score=data.get('communication_score'),
            communication_comments=data.get('communication_comments'),
            initiative_score=data.get('initiative_score'),
            initiative_comments=data.get('initiative_comments'),
            motivation_score=data.get('motivation_score'),
            motivation_comments=data.get('motivation_comments'),
            creativity_score=data.get('creativity_score'),
            creativity_comments=data.get('creativity_comments'),
            honesty_score=data.get('honesty_score'),
            honesty_comments=data.get('honesty_comments'),
            overall_rating_score=data.get('overall_rating_score'),
            overall_rating_comments=data.get('overall_rating_comments'),
            signature=data.get('signature'),
            evaluator_name=data.get('evaluator_name'),
            evaluation_date=datetime.strptime(data.get('evaluation_date'), '%Y-%m-%d').date() if data.get('evaluation_date') else None
        )
        
        # Add HR-specific fields if applicable
        if evaluator_role == 'HR':
            evaluation_response.commitment_work_score = data.get('commitment_work_score')
            evaluation_response.commitment_work_comments = data.get('commitment_work_comments')
            evaluation_response.work_attitude_score = data.get('work_attitude_score')
            evaluation_response.work_attitude_comments = data.get('work_attitude_comments')
            evaluation_response.team_orientation_score = data.get('team_orientation_score')
            evaluation_response.team_orientation_comments = data.get('team_orientation_comments')
            evaluation_response.integrity_honesty_score = data.get('integrity_honesty_score')
            evaluation_response.integrity_honesty_comments = data.get('integrity_honesty_comments')
            evaluation_response.productivity_score = data.get('productivity_score')
            evaluation_response.productivity_comments = data.get('productivity_comments')
            evaluation_response.punctuality_score = data.get('punctuality_score')
            evaluation_response.punctuality_comments = data.get('punctuality_comments')
            evaluation_response.physical_disposition_score = data.get('physical_disposition_score')
            evaluation_response.physical_disposition_comments = data.get('physical_disposition_comments')
            evaluation_response.overall_hr_score = data.get('overall_hr_score')
            evaluation_response.overall_hr_comments = data.get('overall_hr_comments')
        
        # Add Director/MD-specific fields if applicable
        if evaluator_role in ['Director', 'Managing Director']:
            # Common evaluation fields that Director and MD also use
            evaluation_response.commitment_work_score = data.get('commitment_work_score')
            evaluation_response.commitment_work_comments = data.get('commitment_work_comments')
            evaluation_response.productivity_score = data.get('productivity_score')
            evaluation_response.productivity_comments = data.get('productivity_comments')
            evaluation_response.punctuality_score = data.get('punctuality_score')
            evaluation_response.punctuality_comments = data.get('punctuality_comments')
            evaluation_response.physical_disposition_score = data.get('physical_disposition_score')
            evaluation_response.physical_disposition_comments = data.get('physical_disposition_comments')
            
            # Director/MD specific fields
            evaluation_response.stability_score = data.get('stability_score')
            evaluation_response.stability_comments = data.get('stability_comments')
        
        # Add MD-specific fields if applicable
        if evaluator_role == 'Managing Director':
            # Common evaluation fields that MD also uses
            evaluation_response.commitment_work_score = data.get('commitment_work_score')
            evaluation_response.commitment_work_comments = data.get('commitment_work_comments')
            evaluation_response.productivity_score = data.get('productivity_score')
            evaluation_response.productivity_comments = data.get('productivity_comments')
            evaluation_response.punctuality_score = data.get('punctuality_score')
            evaluation_response.punctuality_comments = data.get('punctuality_comments')
            evaluation_response.physical_disposition_score = data.get('physical_disposition_score')
            evaluation_response.physical_disposition_comments = data.get('physical_disposition_comments')
            
            # MD-specific fields
            evaluation_response.further_action_hold = data.get('further_action_hold', False)
            evaluation_response.further_action_next_round = data.get('further_action_next_round', False)
            evaluation_response.suitable_yes = data.get('suitable_yes', False)
            evaluation_response.suitable_no = data.get('suitable_no', False)
            evaluation_response.project_assignment = data.get('project_assignment')
            evaluation_response.area_assignment = data.get('area_assignment')
        
        db.session.add(evaluation_response)
        
        # Update report status to show who has reviewed it
        if evaluator_role == 'Team Lead':
            report.status = 'Team Lead has Reviewed'
        elif evaluator_role == 'HR':
            report.status = 'HR has Reviewed'
        elif evaluator_role == 'Director':
            report.status = 'Director has Reviewed'
        elif evaluator_role == 'Managing Director':
            report.status = 'Completed'
        
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': f'{evaluator_role} evaluation submitted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === Vendor API Endpoints ===
@app.route('/api/vendors', methods=['GET'])
def get_vendors():
    """Get all vendors for dropdown"""
    try:
        vendors = Vendor.query.all()
        vendors_list = []
        for vendor in vendors:
            vendors_list.append({
                'id': vendor.id,
                'name': vendor.name,
                'address': vendor.address,
                'contact_no': vendor.contact_no,
                'email': vendor.email,
                'gst_number': vendor.gst_number
            })
        return jsonify({'status': 'success', 'vendors': vendors_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vendors', methods=['POST'])
def create_vendor():
    """Create a new vendor"""
    try:
        data = request.get_json()
        
        # Check if vendor already exists
        existing_vendor = Vendor.query.filter_by(name=data.get('name')).first()
        if existing_vendor:
            return jsonify({'status': 'error', 'message': 'Vendor with this name already exists'}), 400
        
        # Get user ID from session or use default
        user_id = None
        if 'user' in session:
            user = User.query.filter_by(email=session['user']).first()
            if user:
                user_id = user.id
        
        # If no user in session, use the first admin user as default
        if not user_id:
            admin_user = User.query.filter_by(created_by_admin=True).first()
            if admin_user:
                user_id = admin_user.id
        
        vendor = Vendor(
            name=data.get('name'),
            address=data.get('address'),
            contact_no=data.get('contact_no'),
            email=data.get('email'),
            gst_number=data.get('gst_number'),
            created_by=user_id
        )
        
        db.session.add(vendor)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Vendor created successfully', 'vendor_id': vendor.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vendors/<int:vendor_id>', methods=['GET'])
def get_vendor(vendor_id):
    """Get specific vendor details"""
    try:
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({'status': 'error', 'message': 'Vendor not found'}), 404
        
        vendor_data = {
            'id': vendor.id,
            'name': vendor.name,
            'address': vendor.address,
            'contact_no': vendor.contact_no,
            'email': vendor.email,
            'gst_number': vendor.gst_number
        }
        
        return jsonify({'status': 'success', 'vendor': vendor_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vendors/<int:vendor_id>', methods=['PUT'])
def update_vendor(vendor_id):
    """Update vendor details"""
    try:
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({'status': 'error', 'message': 'Vendor not found'}), 404
        
        data = request.get_json()
        
        # Update vendor fields
        vendor.name = data.get('name', vendor.name)
        vendor.address = data.get('address', vendor.address)
        vendor.contact_no = data.get('contact_no', vendor.contact_no)
        vendor.email = data.get('email', vendor.email)
        vendor.gst_number = data.get('gst_number', vendor.gst_number)
        
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Vendor updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5004)

