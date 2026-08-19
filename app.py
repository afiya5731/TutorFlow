import os
import json
import calendar
import datetime as dt
from datetime import datetime, timezone, timedelta

from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import threading

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here_bhopal_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- 100% TIMEOUT-SAFE GMAIL CONFIGURATION FOR RENDER ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'tutorflowonline@gmail.com'
app.config['MAIL_PASSWORD'] = 'iobxtivpaxqjvahh'  # 16-digit App Password
app.config['MAIL_DEFAULT_SENDER'] = ('TutorFlow Team', 'tutorflowonline@gmail.com')
app.config['MAIL_TIMEOUT'] = 5  # 5s strict timeout to avoid 502 crashes

db = SQLAlchemy(app)
mail = Mail(app)

# ==============================================================================
# 🗂️ DATABASE MODELS
# ==============================================================================

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False) 
    area = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    grade = db.Column(db.String(255), nullable=False)
    tutor_type = db.Column(db.String(50))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Subscription Management
    subscription_plan = db.Column(db.String(50), default='Starter')
    subscription_status = db.Column(db.String(20), default='Active')
    plan_expiry = db.Column(db.DateTime, nullable=True)

    students = db.relationship('Student', backref='teacher', lazy=True)

class ParentRequest(db.Model):
    __tablename__ = 'parent_request'
    id = db.Column(db.Integer, primary_key=True)
    parent_name = db.Column(db.String(100), nullable=False)
    parent_phone = db.Column(db.String(20), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    message = db.Column(db.Text)
    grade = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Pending')
    attendance = db.Column(db.Integer, default=0)
    fees = db.Column(db.Boolean, default=False)
    monthly_fee = db.Column(db.Float, default=0.0)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(50), nullable=True)
    area = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    monthly_fee = db.Column(db.Float, default=0.0)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=db.func.current_date())
    status = db.Column(db.String(10), nullable=False)

class FeeRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False) 
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(10), default='Pending')
    date_paid = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.String(20), nullable=False)
    target_value = db.Column(db.String(100), nullable=True)
    date_posted = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    grade = db.Column(db.String(50), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    file_url = db.Column(db.Text, nullable=False)
    date_shared = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    grade = db.Column(db.String(50), nullable=False)
    questions_json = db.Column(db.Text, nullable=False)
    total_marks = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class QuizSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    student = db.relationship('Student', backref='submissions')
    quiz = db.relationship('Quiz', backref='submissions')

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"DB Create Error: {e}")

# ==============================================================================
# 👑 CONTEXT PROCESSOR (Auto Plan & Expiry Sync)
# ==============================================================================
@app.context_processor
def inject_user_plan():
    if 'teacher_id' in session:
        teacher = Teacher.query.get(session['teacher_id'])
        if teacher:
            if teacher.plan_expiry and datetime.now() > teacher.plan_expiry:
                teacher.subscription_plan = 'Starter'
                teacher.subscription_status = 'Expired'
                teacher.plan_expiry = None
                db.session.commit()
            return {'plan': teacher.subscription_plan or 'Starter'}
    return {'plan': 'Starter'}

# --- ASYNC EMAIL HELPER ---
def send_async_email(app_instance, msg):
    with app_instance.app_context():
        try:
            mail.send(msg)
            print("✅ Mail sent successfully via background thread!")
        except Exception as e:
            print(f"⚠️ Email Send Exception: {e}")

# ==============================================================================
# 🛣️ ROUTES & CONTROLLERS
# ==============================================================================

@app.route('/')
def index():
    area_query = request.args.get('area', '').strip()
    grade_query = request.args.get('grade', '').strip()
    tutor_type_query = request.args.get('tutor_type', '').strip()
    
    query = Teacher.query.filter_by(is_verified=True)

    if area_query:
        query = query.filter(Teacher.area.ilike(f"%{area_query}%"))
    if grade_query:
        query = query.filter(Teacher.grade.ilike(f"%{grade_query}%"))
    if tutor_type_query:
        query = query.filter(Teacher.tutor_type.ilike(f"%{tutor_type_query}%"))

    teachers = query.all()
    return render_template('index.html', teachers=teachers)

@app.route('/verify-email/<int:t_id>')
def verify_email(t_id):
    teacher = Teacher.query.get_or_404(t_id)
    teacher.is_verified = True 
    db.session.commit()
    flash("✨ Account verified successfully! You can now log in to your dashboard.", "success")
    return redirect('/teacher-login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        raw_phone = request.form.get('phone', '').strip()
        country_code = request.form.get('country_code', '+91').strip()
        formatted_phone = f"{country_code}{raw_phone}" if not raw_phone.startswith('+') else raw_phone
        email = request.form.get('email', '').strip().lower()
        
        existing_teacher = Teacher.query.filter_by(email=email).first()
        if existing_teacher:
            flash("⚠️ Error: This email address is already registered!", "danger")
            return redirect('/register')

        selected_subjects = request.form.getlist('subject')
        selected_grades = request.form.getlist('grade')

        subject_str = ", ".join(selected_subjects) if selected_subjects else "All Subjects"
        grade_str = ", ".join(selected_grades) if selected_grades else "All Grades"

        new_teacher = Teacher(
            name=request.form.get('name'),
            email=email,
            password=request.form.get('password'),
            phone=formatted_phone, 
            area=request.form.get('area', 'Global'),
            subject=subject_str,
            grade=grade_str,
            tutor_type=request.form.get('tutor_type', 'Online / Remote'),
            is_verified=False
        )
        
        db.session.add(new_teacher)
        db.session.commit()

        base_url = request.host_url.rstrip('/')
        if request.headers.get('X-Forwarded-Proto') == 'https' and base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://', 1)

        verification_link = f"{base_url}/verify-email/{new_teacher.id}"
        
        msg = Message("Verify Your TutorFlow Account", recipients=[email])
        msg.html = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #6366f1;">Welcome to TutorFlow!</h2>
                <p>Hello {new_teacher.name},</p>
                <p>Thank you for registering as an instructor. Please click the button below to verify your email and activate your account:</p>
                <a href="{verification_link}" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 15px 0;">Verify Email Address</a>
                <p style="font-size: 0.8rem; color: #666;">If the button doesn't work, copy-paste this link into your browser:<br>{verification_link}</p>
                <br>
                <p>Best Regards,<br>TutorFlow Team</p>
            </div>
        """
        
        try:
            thr = threading.Thread(target=send_async_email, args=[app, msg])
            thr.daemon = True
            thr.start()
        except Exception as e:
            print(f"Thread Error: {e}")

        flash("✨ Registration Successful! Verification mail sent. Please check your inbox/spam folder.", "success")
        return redirect('/teacher-login')
        
    return render_template('register.html')

@app.route('/teacher-login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        teacher = Teacher.query.filter_by(email=email, password=password).first()
        if teacher:
            if not teacher.is_verified:
                flash("🔒 Access Denied: Please verify your email first. Check your inbox/spam folder.", "warning")
                return redirect('/teacher-login')
            
            session['teacher_id'] = teacher.id
            return redirect('/teacher_dashboard') 
        
        flash("❌ Invalid credentials! Please check your email and password.", "danger")
        return redirect('/teacher-login')
        
    return render_template('teacher_login.html')

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    
    t_id = session['teacher_id']
    teacher = Teacher.query.get(t_id)
    my_students = ParentRequest.query.filter_by(teacher_id=t_id, status='Pending').all()

    current_month_str = datetime.now().strftime("%B %Y")
    
    total_earnings_query = db.session.query(db.func.sum(FeeRecord.amount)).filter(
        FeeRecord.teacher_id == t_id,
        FeeRecord.status == 'Paid'
    ).first()
    total_earnings = total_earnings_query[0] if total_earnings_query[0] else 0
    
    monthly_earnings_query = db.session.query(db.func.sum(FeeRecord.amount)).filter(
        FeeRecord.teacher_id == t_id,
        FeeRecord.month == current_month_str, 
        FeeRecord.status == 'Paid'
    ).first()
    monthly_earnings = monthly_earnings_query[0] if monthly_earnings_query[0] else 0
    
    start_of_month = datetime.now().date().replace(day=1)
    
    total_sessions = Attendance.query.filter(
        Attendance.teacher_id == t_id,
        Attendance.date >= start_of_month
    ).count()
    
    total_present = Attendance.query.filter(
        Attendance.teacher_id == t_id,
        Attendance.date >= start_of_month,
        Attendance.status == 'Present'
    ).count()
    
    monthly_attendance_pct = round((total_present / total_sessions * 100), 1) if total_sessions > 0 else 0

    return render_template('teacher_dashboard.html', 
                           teacher=teacher, 
                           students=my_students,
                           total_earnings=total_earnings,
                           monthly_earnings=monthly_earnings,
                           current_month=current_month_str,
                           attendance_pct=monthly_attendance_pct)

@app.route('/edit-teacher-profile', methods=['GET', 'POST'])
def edit_teacher_profile():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    
    teacher = Teacher.query.get(session['teacher_id'])
    if request.method == 'POST':
        teacher.area = request.form['area']
        teacher.subject = request.form['subject']
        teacher.grade = request.form['grade']
        teacher.tutor_type = request.form['tutor_type']
        
        new_pass = request.form.get('new_password')
        if new_pass and new_pass.strip():
            teacher.password = new_pass.strip()
            
        db.session.commit()
        return redirect('/teacher_dashboard')
        
    return render_template('edit_teacher_profile.html', teacher=teacher)

@app.route('/my-students')
def my_students():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    
    t_id = session['teacher_id']
    students_list = Student.query.filter_by(teacher_id=t_id, status='Active').all()
    today = datetime.now()
    start_of_month = today.date().replace(day=1)
    current_month = today.strftime('%B %Y')
    
    paid_ids = [r.student_id for r in FeeRecord.query.filter_by(
        teacher_id=t_id, month=current_month, status='Paid').all()]

    for s in students_list:
        s.is_paid_this_month = s.id in paid_ids 
        total_days = Attendance.query.filter(
            Attendance.student_id == s.id,
            Attendance.teacher_id == t_id,
            Attendance.date >= start_of_month
        ).count()
        present_days = Attendance.query.filter(
            Attendance.student_id == s.id,
            Attendance.teacher_id == t_id,
            Attendance.date >= start_of_month,
            Attendance.status == 'Present'
        ).count()
        s.calc_attendance = round((present_days / total_days) * 100, 1) if total_days > 0 else 0

    teacher = Teacher.query.get(t_id)
    return render_template('my_students.html', students=students_list, teacher=teacher)

@app.route('/attendance-dashboard')
def attendance_dashboard():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    t_id = session['teacher_id']
    my_students = Student.query.filter_by(teacher_id=t_id, status='Active').all()
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('attendance_dashboard.html', students=my_students, today_date=current_date)

@app.route('/mark-student-attendance', methods=['POST'])
def mark_student_attendance():
    data = request.json
    s_id = data.get('student_id')
    t_id = session.get('teacher_id')
    status = data.get('status') 
    date_str = data.get('date') 
    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()

    record = Attendance.query.filter_by(student_id=s_id, teacher_id=t_id, date=selected_date).first()
    if record:
        record.status = status
    else:
        new_attendance = Attendance(student_id=s_id, teacher_id=t_id, date=selected_date, status=status)
        db.session.add(new_attendance)
    
    db.session.commit()
    return {"message": f"Marked {status} for {selected_date}"}

@app.route('/collect-fee', methods=['GET', 'POST'])
def collect_fee():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    t_id = session['teacher_id']
    current_month = datetime.now().strftime('%B %Y')

    if request.method == 'POST':
        s_id = request.form.get('student_id')
        amt = request.form.get('amount')
        
        if not s_id or not amt:
            return "Error: Student ID or Amount is missing", 400
            
        record = FeeRecord.query.filter_by(student_id=s_id, month=current_month).first()
        if record:
            record.status = 'Paid'
            record.amount = float(amt)
            record.date_paid = datetime.now(timezone.utc)
        else:
            new_payment = FeeRecord(
                student_id=s_id,
                teacher_id=t_id,
                amount=float(amt),
                month=current_month,
                status='Paid',
                date_paid=datetime.now(timezone.utc)
            )
            db.session.add(new_payment)
            
        db.session.commit()
        return redirect('/collect-fee')

    all_students = Student.query.filter_by(teacher_id=t_id, status='Active').all()
    paid_records = FeeRecord.query.filter_by(teacher_id=t_id, month=current_month, status='Paid').all()
    total_collected = sum(r.amount for r in paid_records)
    
    fee_data = []
    total_pending = 0
    for s in all_students:
        paid_entry = next((r for r in paid_records if r.student_id == s.id), None)
        is_paid = paid_entry is not None
        display_amount = paid_entry.amount if is_paid else s.monthly_fee
        fee_data.append({
            'student_id': s.id,
            'student_name': s.name,
            'amount' : display_amount,
            'is_paid': is_paid,
            'phone': s.phone
        })
        if not is_paid:
            total_pending += (s.monthly_fee or 0)

    return render_template('collect_fee.html', 
                           fee_data=fee_data, 
                           total_collected=total_collected, 
                           total_pending=total_pending,
                           current_month=current_month)

# --- STUDY MATERIAL & QUIZ ROUTES ---
@app.route('/teacher/study-material', methods=['GET', 'POST'])
def teacher_study_material():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    
    t_id = session['teacher_id']
    teacher = Teacher.query.get_or_404(t_id)
    
    if request.method == 'POST':
        action_type = request.form.get('action_type')
        
        if action_type == 'add_material':
            new_mat = StudyMaterial(
                teacher_id=t_id,
                title=request.form.get('title'),
                grade=request.form.get('grade'),
                file_type=request.form.get('file_type'),
                file_url=request.form.get('file_url')
            )
            db.session.add(new_mat)
            db.session.commit()
            flash("✨ Material shared successfully!", "success")

        elif action_type == 'add_quiz':
            title = request.form.get('quiz_title')
            grade = request.form.get('quiz_grade')
            raw_quiz_data = request.form.get('raw_quiz_data')
            try:
                parsed = json.loads(raw_quiz_data)
                new_quiz = Quiz(
                    teacher_id=t_id,
                    title=title,
                    grade=grade,
                    questions_json=json.dumps(parsed),
                    total_marks=len(parsed)
                )
                db.session.add(new_quiz)
                db.session.commit()
                flash("🎯 Quiz created successfully!", "success")
            except Exception as e:
                flash(f"⚠️ Invalid Quiz JSON: {e}", "danger")

        return redirect('/teacher/study-material')

    materials = StudyMaterial.query.filter_by(teacher_id=t_id).order_by(StudyMaterial.date_shared.desc()).all()
    quizzes = Quiz.query.filter_by(teacher_id=t_id).order_by(Quiz.created_at.desc()).all()
    submissions = QuizSubmission.query.join(Quiz).filter(Quiz.teacher_id == t_id).order_by(QuizSubmission.submitted_at.desc()).all()

    return render_template('teacher_study_material.html', 
                           teacher=teacher, 
                           materials=materials, 
                           quizzes=quizzes, 
                           submissions=submissions)

@app.route('/teacher/delete-material/<int:mat_id>')
def delete_study_material(mat_id):
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    mat = StudyMaterial.query.get_or_404(mat_id)
    if mat.teacher_id == session['teacher_id']:
        db.session.delete(mat)
        db.session.commit()
        flash("Study material deleted.", "info")
    return redirect('/teacher/study-material')

@app.route('/teacher/delete-quiz/<int:quiz_id>')
def delete_quiz(quiz_id):
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.teacher_id == session['teacher_id']:
        QuizSubmission.query.filter_by(quiz_id=quiz.id).delete()
        db.session.delete(quiz)
        db.session.commit()
        flash("Quiz and scores deleted.", "info")
    return redirect('/teacher/study-material')

# --- STUDENT PORTAL ROUTES ---
@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        student = Student.query.filter_by(email=email, password=password).first()
        if student:
            session['student_id'] = student.id 
            return redirect('/student-dashboard') 
        flash("❌ Invalid credentials!", "danger")
    return render_template('student_login.html')

@app.route('/student-dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect('/student-login')
    
    s_id = session['student_id']
    student = Student.query.get_or_404(s_id)
    teacher = Teacher.query.get(student.teacher_id)
    current_month = datetime.now().strftime('%B %Y')
    
    fee_record = FeeRecord.query.filter_by(student_id=s_id, month=current_month, status='Paid').first()
    is_paid = fee_record is not None
    
    records = Attendance.query.filter_by(student_id=s_id).order_by(Attendance.date.desc()).limit(10).all()
    total = Attendance.query.filter_by(student_id=s_id).count()
    present = Attendance.query.filter_by(student_id=s_id, status='Present').count()
    attendance_pct = round((present / total * 100), 1) if total > 0 else 0

    all_notices = Notice.query.filter_by(teacher_id=student.teacher_id).order_by(Notice.date_posted.desc()).all()
    relevant_notices = [n for n in all_notices if n.target_type == 'all' or (n.target_type == 'batch' and n.target_value == student.grade) or (n.target_type == 'individual' and n.target_value == str(student.id))]
        
    return render_template('student_dashboard.html', 
                           student=student, 
                           teacher=teacher,
                           is_paid=is_paid, 
                           attendance=attendance_pct,
                           attendance_records=records,
                           current_month=current_month,
                           notices=relevant_notices)

@app.route('/student/study-material')
def student_study_material():
    if 'student_id' not in session:
        return redirect('/student-login')
    
    student = Student.query.get_or_404(session['student_id'])
    materials = StudyMaterial.query.filter_by(teacher_id=student.teacher_id, grade=student.grade).all()
    quizzes = Quiz.query.filter_by(teacher_id=student.teacher_id, grade=student.grade).all()
    student_submissions = {sub.quiz_id: sub for sub in QuizSubmission.query.filter_by(student_id=student.id).all()}

    return render_template('student_study_material.html', 
                           student=student, 
                           materials=materials, 
                           quizzes=quizzes,
                           submissions=student_submissions)

@app.route('/student/attempt-quiz/<int:quiz_id>', methods=['GET', 'POST'])
def attempt_quiz(quiz_id):
    if 'student_id' not in session:
        return redirect('/student-login')

    student = Student.query.get_or_404(session['student_id'])
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = json.loads(quiz.questions_json)
    existing_submission = QuizSubmission.query.filter_by(quiz_id=quiz.id, student_id=student.id).first()

    if request.method == 'POST':
        score = sum(1 for idx, q in enumerate(questions) if request.form.get(f'question_{idx}', '').strip().lower() == q.get('answer', '').strip().lower())
        if existing_submission:
            existing_submission.score = score
            existing_submission.submitted_at = datetime.now(timezone.utc)
        else:
            submission = QuizSubmission(quiz_id=quiz.id, student_id=student.id, score=score, total=len(questions))
            db.session.add(submission)
        
        db.session.commit()
        flash(f"🎉 Test Submitted! Score: {score}/{len(questions)}", "success")
        return redirect('/student/study-material')

    return render_template('attempt_quiz.html', quiz=quiz, questions=questions, submission=existing_submission)

@app.route('/student-profile')
def student_profile():
    if 'student_id' not in session:
        return redirect('/student-login')
    current_student = Student.query.get_or_404(session['student_id'])
    attendance_data = Attendance.query.filter_by(student_id=current_student.id).all()
    fee_records = FeeRecord.query.filter_by(student_id=current_student.id).all()
    return render_template('student_profile.html', student=current_student, attendance=attendance_data, fees=fee_records)

# --- SUBSCRIPTION ROUTES ---
@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/manage-subscription')
def manage_subscription():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')

    teacher = Teacher.query.get_or_404(session['teacher_id'])
    if teacher.plan_expiry and datetime.now() > teacher.plan_expiry:
        teacher.subscription_plan = 'Starter'
        teacher.subscription_status = 'Expired'
        teacher.plan_expiry = None
        db.session.commit()

    billing_cycle = "₹0 / Forever Free" if teacher.subscription_plan == 'Starter' else "₹299 / Month"
    renewal_date = teacher.plan_expiry.strftime('%d %B, %Y') if teacher.plan_expiry else "N/A (Free Plan)"

    return render_template('manage_subscription.html',
                           plan=teacher.subscription_plan,
                           status=teacher.subscription_status,
                           billing_cycle=billing_cycle,
                           renewal_date=renewal_date)

@app.route('/checkout/<plan_name>')
def checkout(plan_name):
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    price = "299" if plan_name == 'pro' else "0"
    display_title = "Pro Educator (14-Day Free Trial)" if plan_name == 'pro' else "Starter Plan"
    return render_template('checkout.html', plan_name=plan_name, display_title=display_title, price=price)

@app.route('/process-subscription', methods=['POST'])
def process_subscription():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')

    teacher = Teacher.query.get_or_404(session['teacher_id'])
    expiry_datetime = datetime.now() + timedelta(days=14)
    teacher.subscription_plan = 'Pro Educator'
    teacher.subscription_status = 'Active'
    teacher.plan_expiry = expiry_datetime
    db.session.commit()

    flash('🎉 Congratulations! Your Pro Educator 14-Day Free Trial is now active!', 'success')
    return redirect('/manage-subscription')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
