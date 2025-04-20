from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from app.models import db, User, Doctor, Patient, Prescription, FollowUp
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('landing.html')

@main_bp.route('/get-started')
def get_started():
    return render_template('index.html')

@main_bp.route('/landing')
def landing():
    return render_template('landing.html')

@main_bp.route('/login/<role>', methods=['GET', 'POST'])
def role_login(role):
    if role not in ['receptionist', 'doctor', 'patient']:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, role=role).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password')
    
    template = f'{role}_login.html'
    return render_template(template)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get current date for display
    now = datetime.now()
    
    # Mock data for demonstration
    stats = {
        'total_patients': 1250,
        'today_appointments': 42,
        'available_doctors': 18,
        'pending_reports': 7
    }
    
    recent_appointments = [
        {
            'patient_name': 'John Doe',
            'doctor_name': 'Dr. Smith',
            'date': now,
            'status': 'Scheduled',
            'status_color': 'primary'
        },
        {
            'patient_name': 'Jane Smith',
            'doctor_name': 'Dr. Johnson',
            'date': now,
            'status': 'Completed',
            'status_color': 'success'
        },
        {
            'patient_name': 'Robert Brown',
            'doctor_name': 'Dr. Williams',
            'date': now,
            'status': 'Cancelled',
            'status_color': 'danger'
        },
        {
            'patient_name': 'Emily Davis',
            'doctor_name': 'Dr. Brown',
            'date': now,
            'status': 'In Progress',
            'status_color': 'warning'
        }
    ]
    
    notifications = [
        {
            'message': 'New patient registration: Sarah Wilson',
            'time': '10 minutes ago',
            'icon': 'user-plus',
            'color': 'primary'
        },
        {
            'message': 'Appointment reminder: Dr. Johnson at 2:00 PM',
            'time': '1 hour ago',
            'icon': 'calendar-check',
            'color': 'info'
        },
        {
            'message': 'Lab report ready for patient ID: #12345',
            'time': '2 hours ago',
            'icon': 'file-medical',
            'color': 'success'
        },
        {
            'message': 'System maintenance scheduled for tonight',
            'time': '3 hours ago',
            'icon': 'tools',
            'color': 'warning'
        }
    ]
    
    if current_user.role == 'receptionist':
        doctors = Doctor.query.all()
        patients = Patient.query.all()
        return render_template('receptionist_dashboard.html', doctors=doctors, patients=patients)
    elif current_user.role == 'doctor':
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        patients = Patient.query.filter_by(doctor_id=doctor.id).all() if doctor else []
        return render_template('doctor_dashboard.html', doctor=doctor, patients=patients)
    else:  # patient
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        prescriptions = Prescription.query.filter_by(patient_id=patient.id).all() if patient else []
        follow_ups = FollowUp.query.filter_by(patient_id=patient.id).all() if patient else []
        return render_template('patient_dashboard.html', patient=patient, prescriptions=prescriptions, follow_ups=follow_ups)
    
    # Default dashboard for admin or other roles
    return render_template('dashboard.html', now=now, stats=stats, recent_appointments=recent_appointments, notifications=notifications)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.landing'))

# Placeholder routes for the features mentioned in the landing page
@main_bp.route('/new_appointment')
@login_required
def new_appointment():
    return render_template('new_appointment.html')

@main_bp.route('/patient_records')
@login_required
def patient_records():
    return render_template('patient_records.html')

@main_bp.route('/medical_reports')
@login_required
def medical_reports():
    return render_template('medical_reports.html')

@main_bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html') 