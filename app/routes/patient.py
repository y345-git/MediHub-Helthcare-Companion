from flask import Blueprint, render_template, redirect, url_for, flash, send_file, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Patient, Prescription, FollowUp, Doctor, HealthReport
import google.generativeai as genai
from datetime import datetime
from reportlab.pdfgen import canvas
from io import BytesIO
import os
from app.utils.email import send_medicine_expiry_alert

patient_bp = Blueprint('patient', __name__)

# Configure Gemini AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

@patient_bp.route('/health_analysis')
@login_required
def health_analysis():
    if current_user.role != 'patient':
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient or not patient.is_premium:
        flash('This feature is only available for premium patients')
        return redirect(url_for('dashboard'))
    
    # Get patient's medical history
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).all()
    follow_ups = FollowUp.query.filter_by(patient_id=patient.id).all()
    
    # Prepare data for AI analysis
    medical_history = f"Patient: {patient.name}, Age: {patient.age}, Gender: {patient.gender}\n\n"
    medical_history += "Prescriptions:\n"
    for p in prescriptions:
        medical_history += f"- {p.medication} ({p.dosage}): {p.instructions}\n"
    
    medical_history += "\nFollow-ups:\n"
    for f in follow_ups:
        medical_history += f"- {f.visit_date.strftime('%Y-%m-%d')}: {f.notes}\n"
    
    # Get AI analysis
    response = model.generate_content(f"Analyze this patient's medical history and provide insights:\n\n{medical_history}")
    analysis = response.text
    
    return render_template('health_analysis.html', analysis=analysis)

@patient_bp.route('/download_prescription/<int:prescription_id>')
@login_required
def download_prescription(prescription_id):
    prescription = Prescription.query.get_or_404(prescription_id)
    patient = Patient.query.get(prescription.patient_id)
    doctor = Doctor.query.get(prescription.doctor_id)
    
    # Create PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # Add content to PDF
    p.drawString(100, 800, f"Prescription for: {patient.name}")
    p.drawString(100, 780, f"Date: {prescription.date.strftime('%Y-%m-%d')}")
    p.drawString(100, 760, f"Doctor: Dr. {doctor.name}")
    p.drawString(100, 740, f"Specialization: {doctor.specialization}")
    p.drawString(100, 700, "Medication Details:")
    p.drawString(100, 680, f"Medication: {prescription.medication}")
    p.drawString(100, 660, f"Dosage: {prescription.dosage}")
    p.drawString(100, 640, f"Instructions: {prescription.instructions}")
    
    p.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"prescription_{patient.name}_{prescription.date.strftime('%Y%m%d')}.pdf",
        mimetype='application/pdf'
    )

@patient_bp.route('/health_chatbot', methods=['GET', 'POST'])
@login_required
def health_chatbot():
    if current_user.role != 'patient':
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient or not patient.is_premium:
        flash('This feature is only available for premium patients')
        return redirect(url_for('dashboard'))
    
    # Get patient's medical history for context
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).all()
    follow_ups = FollowUp.query.filter_by(patient_id=patient.id).all()
    
    # Prepare patient context for the AI
    patient_context = f"""Patient Information:
- Name: {patient.name}
- Age: {patient.age}
- Gender: {patient.gender}
- Doctor: Dr. {patient.doctor.name if patient.doctor else 'Not assigned'}

Medical History:
- Prescriptions: {', '.join([p.medication for p in prescriptions]) if prescriptions else 'None'}
- Recent Follow-ups: {len(follow_ups)} visits

Please provide medical advice while considering this patient's contextin atmost 10 lines . Always remind them to consult their doctor for serious concerns."""

    if request.method == 'POST':
        user_message = request.form.get('message')
        if user_message:
            # Combine patient context with user's message
            prompt = f"{patient_context}\n\nPatient's Question: {user_message}"
            
            try:
                response = model.generate_content(prompt)
                return jsonify({'response': response.text})
            except Exception as e:
                return jsonify({'error': 'Failed to generate response. Please try again.'}), 500
    
    return render_template('health_chatbot.html', patient=patient)

@patient_bp.route('/health_report')
@login_required
def health_report():
    if current_user.role != 'patient':
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient or not patient.is_premium:
        flash('This feature is only available for premium patients')
        return redirect(url_for('dashboard'))
    
    # Get patient's medical history
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).all()
    follow_ups = FollowUp.query.filter_by(patient_id=patient.id).order_by(FollowUp.visit_date).all()
    
    # Prepare data for AI analysis
    import os
    import google.generativeai as genai
    from datetime import datetime, timedelta
    
    # Configure Gemini
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    # Format patient data for analysis
    patient_data = f"""
Patient Information:
- Name: {patient.name}
- Age: {patient.age}
- Gender: {patient.gender}
- Doctor: {patient.doctor.name if patient.doctor else 'Not assigned'}
"""

    # Format follow-up data
    follow_up_data = ""
    if follow_ups:
        follow_up_data = "Follow-up History:\n"
        for i, follow_up in enumerate(follow_ups):
            follow_up_data += f"""
Visit #{i+1} - {follow_up.visit_date.strftime('%Y-%m-%d')}:
- Doctor: {follow_up.doctor.name}
- Complaints: {follow_up.complaints or 'None recorded'}
- Examination: {follow_up.examination or 'None recorded'}
- Diagnosis: {follow_up.diagnosis or 'None recorded'}
- Treatment: {follow_up.treatment or 'None recorded'}
- Notes: {follow_up.notes or 'None recorded'}
"""
            
            # Add medicines prescribed during this follow-up
            if follow_up.medicines:
                follow_up_data += "Medicines Prescribed:\n"
                for medicine in follow_up.medicines:
                    follow_up_data += f"- {medicine.name} ({medicine.dosage}): {medicine.notes or 'No notes'}\n"
    
    # Format prescription data
    prescription_data = ""
    if prescriptions:
        prescription_data = "Standalone Prescriptions:\n"
        for prescription in prescriptions:
            prescription_data += f"""
- Date: {prescription.date.strftime('%Y-%m-%d')}
- Doctor: {prescription.doctor.name}
- Medication: {prescription.medication}
- Dosage: {prescription.dosage}
- Instructions: {prescription.instructions}
"""
    
    # Calculate follow-up frequency
    followup_frequency = ""
    if len(follow_ups) >= 2:
        # Calculate average days between follow-ups
        total_days = 0
        for i in range(1, len(follow_ups)):
            days_between = (follow_ups[i].visit_date - follow_ups[i-1].visit_date).days
            total_days += days_between
        
        avg_days = total_days / (len(follow_ups) - 1)
        
        if avg_days <= 30:
            followup_frequency = f"Frequent follow-ups (average {avg_days:.1f} days between visits)"
        elif avg_days <= 90:
            followup_frequency = f"Regular follow-ups (average {avg_days:.1f} days between visits)"
        else:
            followup_frequency = f"Infrequent follow-ups (average {avg_days:.1f} days between visits)"
    
    try:
        # Generate AI analysis for each section
        current_condition_prompt = f"""
Analyze the patient's current health condition based on:

{patient_data}
{follow_up_data}
{prescription_data}

Provide a brief 3-point summary:
1. Current health status
2. Ongoing issues
3. Overall assessment

Keep each point to 1-2 lines maximum.
"""
        current_condition_response = model.generate_content(current_condition_prompt)
        current_condition = current_condition_response.text
        
        # Health Improvement Analysis
        improvement_prompt = f"""
Analyze health trends based on:

{patient_data}
{follow_up_data}
{prescription_data}

Provide a 3-point summary:
1. Improvement/deterioration trends
2. Treatment effectiveness
3. Key areas of concern

Keep each point to 1-2 lines maximum.
"""
        improvement_response = model.generate_content(improvement_prompt)
        improvement_analysis = improvement_response.text
        
        # Disease Risk Detection
        risk_prompt = f"""
Identify disease risks based on:

{patient_data}
{follow_up_data}
{prescription_data}

Provide a 3-point summary:
1. Primary disease risks
2. Risk factors
3. Warning signs

Keep each point to 1-2 lines maximum.
"""
        risk_response = model.generate_content(risk_prompt)
        risk_detection = risk_response.text
        
        # Recommended Tests
        tests_prompt = f"""
Recommend medical tests based on:

{patient_data}
{follow_up_data}
{prescription_data}

List 3-5 specific tests with:
1. Test name
2. Purpose
3. Recommended frequency

One line per test.
"""
        tests_response = model.generate_content(tests_prompt)
        recommended_tests = tests_response.text
        
        # Prescription Analysis
        prescription_analysis_prompt = f"""
Analyze prescriptions based on:

{prescription_data}
{follow_up_data}

Provide a 3-point summary:
1. Medication patterns
2. Potential interactions
3. Adherence recommendations

Keep each point to 1-2 lines maximum.
"""
        prescription_analysis_response = model.generate_content(prescription_analysis_prompt)
        prescription_analysis = prescription_analysis_response.text
        
        # AI Recommendations
        recommendations_prompt = f"""
Provide health recommendations based on:

{patient_data}
{follow_up_data}
{prescription_data}

List 3-5 specific recommendations:
1. Lifestyle changes
2. Preventive measures
3. Follow-up schedule

One line per recommendation.
"""
        recommendations_response = model.generate_content(recommendations_prompt)
        ai_recommendations = recommendations_response.text
        
        # Generate summary
        summary_prompt = f"""
Create a 2-paragraph summary of:

Current Condition: {current_condition}
Improvement: {improvement_analysis}
Risks: {risk_detection}
Recommendations: {ai_recommendations}

Focus on critical health status and key recommendations.
Keep it under 100 words total.
"""
        summary_response = model.generate_content(summary_prompt)
        summary = summary_response.text
        
        # Create and save the health report
        health_report = HealthReport(
            patient_id=patient.id,
            current_condition=current_condition,
            improvement_analysis=improvement_analysis,
            followup_frequency=followup_frequency,
            risk_detection=risk_detection,
            recommended_tests=recommended_tests,
            prescription_analysis=prescription_analysis,
            ai_recommendations=ai_recommendations,
            summary=summary
        )
        db.session.add(health_report)
        db.session.commit()
        
        # Compile all report data for display
        report_data = {
            'current_condition': current_condition,
            'improvement_analysis': improvement_analysis,
            'followup_frequency': followup_frequency,
            'risk_detection': risk_detection,
            'recommended_tests': recommended_tests,
            'prescription_analysis': prescription_analysis,
            'ai_recommendations': ai_recommendations,
            'summary': summary,
            'date_generated': health_report.date_generated
        }
        
        return render_template('health_report.html', patient=patient, report_data=report_data)
        
    except Exception as e:
        flash(f'Error generating health report: {str(e)}', 'error')
        return render_template('health_report.html', patient=patient)

@patient_bp.route('/medicine_expiry_alerts', methods=['GET', 'POST'])
@login_required
def medicine_expiry_alerts():
    if current_user.role != 'patient':
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient or not patient.is_premium:
        flash('This feature is only available for premium patients')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        if 'medicine_image' not in request.files:
            flash('No image uploaded', 'error')
            return render_template('medicine_expiry_alerts.html', patient=patient)
        
        image_file = request.files['medicine_image']
        if image_file.filename == '':
            flash('No image selected', 'error')
            return render_template('medicine_expiry_alerts.html', patient=patient)
        
        # Save the image temporarily
        import tempfile
        import os
        from datetime import datetime, date
        from PIL import Image
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Save and open the uploaded file with PIL
            image_file.save(temp_path)
            image = Image.open(temp_path)
            
            # Use Gemini to analyze the image
            prompt = """Analyze this medicine packet image and extract the following information:
1. Medicine name
2. Expiry date (in YYYY-MM-DD format)
3. Batch number (if visible)

Focus specifically on finding the expiry date. If you can't find it, indicate that clearly.
Format your response as:
Medicine: [name]
Expiry Date: [YYYY-MM-DD]
Batch: [number]"""
            
            response = model.generate_content([prompt, image])
            analysis = response.text
            
            # Extract medicine name and expiry date from the analysis
            import re
            medicine_match = re.search(r'Medicine:\s*([^\n]+)', analysis)
            expiry_date_match = re.search(r'Expiry Date:\s*(\d{4}-\d{2}-\d{2})', analysis)
            
            if expiry_date_match:
                extracted_date = expiry_date_match.group(1)
                medicine_name = medicine_match.group(1) if medicine_match else "Unknown Medicine"
                
                try:
                    # Parse the extracted date
                    expiry_date = datetime.strptime(extracted_date, "%Y-%m-%d").date()
                    today = date.today()
                    days_until_expiry = (expiry_date - today).days
                    
                    # Determine alert level and message
                    if expiry_date < today:
                        alert_level = "danger"
                        alert_message = f"⚠ WARNING: Medicine expired on {expiry_date.strftime('%d %B %Y')}!"
                    elif days_until_expiry <= 30:
                        alert_level = "warning"
                        alert_message = f"⚠ ALERT: Medicine expires in {days_until_expiry} days!"
                    elif days_until_expiry <= 90:
                        alert_level = "info"
                        alert_message = f"ℹ Medicine expires in {days_until_expiry} days"
                    else:
                        alert_level = "success"
                        alert_message = f"✅ Medicine is valid until {expiry_date.strftime('%d %B %Y')}"
                    
                    # Send email alert
                    if hasattr(patient, 'email') and patient.email:  # Check if email attribute exists and is not None
                        email_sent = send_medicine_expiry_alert(
                            patient_email=patient.email,
                            medicine_name=medicine_name,
                            expiry_date=expiry_date.strftime('%d %B %Y'),
                            days_until_expiry=days_until_expiry,
                            alert_level=alert_level
                        )
                        if email_sent:
                            flash('Email alert has been sent to your registered email address.', 'success')
                        else:
                            flash('Failed to send email alert. Please check your email settings.', 'warning')
                    else:
                        flash('Email alert could not be sent. Please update your profile with an email address.', 'info')
                    
                    return render_template('medicine_expiry_alerts.html',
                                        patient=patient,
                                        analysis=analysis,
                                        expiry_date=expiry_date.strftime('%d %B %Y'),
                                        days_until_expiry=days_until_expiry,
                                        alert_level=alert_level,
                                        alert_message=alert_message)
                    
                except ValueError:
                    flash('❌ Could not parse the expiry date from the image', 'error')
            else:
                flash('❌ Could not extract expiry date. Try a clearer image.', 'error')
            
            return render_template('medicine_expiry_alerts.html', patient=patient, analysis=analysis)
            
        except Exception as e:
            flash(f'Error analyzing image: {str(e)}', 'error')
            return render_template('medicine_expiry_alerts.html', patient=patient)
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                print(f"Error deleting temporary file: {str(e)}")
    
    return render_template('medicine_expiry_alerts.html', patient=patient)

@patient_bp.route('/medication_alternatives', methods=['GET', 'POST'])
@login_required
def medication_alternatives():
    if current_user.role != 'patient':
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient or not patient.is_premium:
        flash('This feature is only available for premium patients')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        prescribed_medicine = request.form.get('prescribed_medicine')
        alternative_medicine = request.form.get('alternative_medicine')
        
        # Get patient's medical history for context
        prescriptions = Prescription.query.filter_by(patient_id=patient.id).all()
        current_medications = [p.medication for p in prescriptions]
        
        # Prepare context for AI
        context = f"""Patient Information:
- Name: {patient.name}
- Age: {patient.age}
- Gender: {patient.gender}
- Current Medications: {', '.join(current_medications) if current_medications else 'None'}

Medication Comparison:
- Currently Prescribed: {prescribed_medicine}
- Alternative Option: {alternative_medicine}

Please analyze if this alternative medication would be suitable for this patient, considering:
1. Potential interactions with current medications
2. Age and gender-specific considerations
3. Common side effects
4. Effectiveness comparison
5. Safety profile
6.Content comparison 

Give all this in 4-7 lines. only
Provide a detailed recommendation with clear reasoning to check if the alternative medicine is suitable for the patient yes or no clearly."""

        try:
            response = model.generate_content(context)
            recommendation = response.text
            return render_template('medication_alternatives.html', 
                                patient=patient,
                                recommendation=recommendation,
                                prescribed_medicine=prescribed_medicine,
                                alternative_medicine=alternative_medicine)
        except Exception as e:
            flash('Failed to generate recommendation. Please try again.', 'error')
            return render_template('medication_alternatives.html', patient=patient)
    
    return render_template('medication_alternatives.html', patient=patient)

@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if current_user.role != 'patient':
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Update patient information
        patient.name = request.form.get('name')
        patient.age = int(request.form.get('age'))
        patient.gender = request.form.get('gender')
        patient.contact = request.form.get('contact')
        patient.address = request.form.get('address')
        
        # Update email if provided
        email = request.form.get('email')
        if email:
            patient.email = email
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('patient.update_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
    
    return render_template('patient_profile.html', patient=patient)

@patient_bp.route('/health_reports')
@login_required
def list_health_reports():
    if current_user.role != 'patient':
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient or not patient.is_premium:
        flash('This feature is only available for premium patients')
        return redirect(url_for('dashboard'))
    
    # Get all health reports for the patient, ordered by date (newest first)
    reports = HealthReport.query.filter_by(patient_id=patient.id).order_by(HealthReport.date_generated.desc()).all()
    
    return render_template('health_reports.html', patient=patient, reports=reports)

@patient_bp.route('/view_health_report/<int:report_id>')
@login_required
def view_health_report(report_id):
    if current_user.role != 'patient':
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient or not patient.is_premium:
        flash('This feature is only available for premium patients')
        return redirect(url_for('dashboard'))
    
    # Get the specific health report
    report = HealthReport.query.get_or_404(report_id)
    
    # Ensure the report belongs to the current patient
    if report.patient_id != patient.id:
        flash('Access denied. This report belongs to another patient.')
        return redirect(url_for('patient.health_reports'))
    
    # Compile report data for display
    report_data = {
        'current_condition': report.current_condition,
        'improvement_analysis': report.improvement_analysis,
        'followup_frequency': report.followup_frequency,
        'risk_detection': report.risk_detection,
        'recommended_tests': report.recommended_tests,
        'prescription_analysis': report.prescription_analysis,
        'ai_recommendations': report.ai_recommendations,
        'summary': report.summary,
        'date_generated': report.date_generated
    }
    
    return render_template('health_report.html', patient=patient, report_data=report_data) 