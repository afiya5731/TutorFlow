from flask import Flask, render_template, request, redirect, session, flash 
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import threading
import datetime
from datetime import date, datetime, timezone
import sys
import io
import os
import calendar


app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here_bhopal_2026'

# --- DYNAMIC DATABASE CONFIGURATION (NEON / RENDER / LOCAL) ---
db_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")

# Render/Neon postgres prefix fix
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# --- 100% TIMEOUT-SAFE GMAIL CONFIGURATION FOR RENDER ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'tutorflowonline@gmail.com'
app.config['MAIL_PASSWORD'] = 'iobxtivpaxqjvahh'  # 16-digit App Password
app.config['MAIL_DEFAULT_SENDER'] = 'tutorflowonline@gmail.com'
app.config['MAIL_TIMEOUT'] = 5  # 5s strict timeout to avoid 502 crashes


mail = Mail(app)

# ==============================================================================
# 🗂️ DATABASE MODELS
# ==============================================================================

# Database Model for Teachers
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False) 
    area = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(50), nullable=False)
    tutor_type = db.Column(db.String(50))           # Home Tutor / Coaching /online
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    
    # 👑 ADD THESE THREE COLUMNS FOR SUBSCRIPTIONS:
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
    fees  = db.Column(db.Boolean, default=False)
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
    status = db.Column(db.String(10), nullable=False) # 'Present' or 'Absent'

class FeeRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False) 
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.String(20), nullable=False) # e.g., "May 2026"
    status = db.Column(db.String(10), default='Pending') # 'Paid' or 'Pending'
    date_paid = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.String(20), nullable=False) # 'all', 'batch', 'individual'
    target_value = db.Column(db.String(100), nullable=True) # e.g. "Class 10th" ya Student ID "12"
    date_posted = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
import json

class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    grade = db.Column(db.String(50), nullable=False)  # e.g., "Class 10"
    file_type = db.Column(db.String(20), nullable=False)  # 'pdf', 'image', 'doc', 'link'
    file_url = db.Column(db.Text, nullable=False)  # Cloud link / Google Drive link / Static path
    date_shared = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    grade = db.Column(db.String(50), nullable=False)
    # JSON structure storing questions, options & answer:
    # [{"question": "...", "options": ["A", "B", "C", "D"], "answer": "A"}]
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
# ==============================================================================
# 🔥 FORCE TABLE CREATION ON RENDER (MODELS KE BAAD RUN HONA CHAHIYE)
# ==============================================================================
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully on Render cloud!")
    except Exception as e:
        print(f"Database table check status: {e}")

@app.route('/')
def index():
    area_query = request.args.get('area', '').strip()
    grade_query = request.args.get('grade', '').strip()
    tutor_type_query = request.args.get('tutor_type', '').strip()
    
    # 👑 FIX 1: Sirf verified instructors hi homepage filters par show honge
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
    
    # 👑 FIX 2: Blank text ke bajaye sleek redirect aur green alert validation
    flash("✨ Account verified successfully! You can now log in to your console workspace.", "success")
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
            tutor_type=request.form.get('tutor_type'),
            is_verified=False
        )
        
        try:
            db.session.add(new_teacher)
            db.session.commit()
        except Exception as db_err:
            db.session.rollback()
            print(f"Database Error: {db_err}")
            flash(f"❌ Database error: {db_err}", "danger")
            return redirect('/register')

        base_url = request.host_url.rstrip('/')
        verification_link = f"{base_url}/verify-email/{new_teacher.id}"
        
        msg = Message("Verify Your TutorFlow Account", recipients=[email])
        msg.html = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2 style="color: #6366f1;">Welcome to TutorFlow!</h2>
                <p>Hello {new_teacher.name},</p>
                <p>Thank you for registering. Please click below to verify your account:</p>
                <a href="{verification_link}" style="display: inline-block; background: #6366f1; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; font-weight: bold;">Verify Email Address</a>
                <br><br>
                <p>Best Regards,<br>TutorFlow Team</p>
            </div>
        """
        
        try:
            mail.send(msg)
        except Exception as e:
            print(f"SMTP Error: {e}")
            flash("⚠️ Account created, but verification email failed to send. Please contact admin.", "warning")
            return redirect('/teacher-login')

        flash("✨ Registration Successful! Please check your email to verify your account.", "success")
        return redirect('/teacher-login')
        
    return render_template('register.html')
        

@app.route('/teacher-login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        teacher = Teacher.query.filter_by(email=email, password=password).first()
        
        if teacher:
            # 👑 FIX 3: Unverified users dashboard par nahi ja payenge, login screen par hi flash banner dikhega
            if not teacher.is_verified:
                flash("🔒 Access Denied: Please verify your email channel first. Check your inbox/spam folder for the verification link.", "warning")
                return redirect('/teacher-login')
            
            session['teacher_id'] = teacher.id
            return redirect('/teacher_dashboard') 
        
        flash("❌ Invalid credentials! System configuration mismatch.", "danger")
        return redirect('/teacher-login')
        
    return render_template('teacher_login.html')

# --- ✉️ CLOUD-SAFE BACKGROUND EMAIL SENDING FUNCTION ---
def send_async_email(app_instance, msg):
    # Explicitly app context ko block scope ke andar ensure karein
    with app_instance.app_context():
        try:
            mail.send(msg)
            print("Email sent successfully from Render cloud production environment!")
        except Exception as e:
            print(f"Render SMTP Delivery Failure Exception Details: {e}")


# --- 📝 REGISTER ROUTE (COMPLETELY SAFE FROM SYNTAX ERRORS) ---
@app.route('/student-register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        email = request.form.get('email')
        t_id = request.form.get('teacher_id') or session.get('teacher_id')
        
        # 👑 Blank text page ke bajaye template flash feedback filters
        if not t_id:
            flash("❌ Registration Failed: Teacher ID is missing. Please check the link.", "danger")
            return redirect('/student-register')

        existing_user = Student.query.filter_by(email=email).first()
        if existing_user:
            flash("⚠️ Warning: This email address is already registered!", "warning")
            return redirect('/student-register')

        # 1. Create Student Object
        new_student = Student(
            name=request.form.get('name'),
            email=email,
            phone=request.form.get('phone'),
            password=request.form.get('password'),
            grade=request.form.get('grade'),
            area=request.form.get('area'),
            teacher_id=t_id,  
            status='Active'
        )
        
        # 2. 👑 FIX: ParentRequest ko return se pehle object array mein banaya
        new_request = ParentRequest(
            parent_name=request.form.get('name'),
            parent_phone=request.form.get('phone'),
            grade=request.form.get('grade'),
            teacher_id=t_id,
            status='Active' 
        )
        
        try:
            # Dono records ko ek sath single database commit execution par lock kiya
            db.session.add(new_student)
            db.session.add(new_request)
            db.session.commit()
            
            # Success feedback set kiya
            flash("✨ Registration Successful! Welcome aboard. Please login here.", "success")
            # Raw text page ke bajaye user ko direct Student Login page par route kiya
            return redirect('/student-login')
            
        except Exception as e:
            db.session.rollback()
            print(f"Database Crash Logs: {e}")
            flash("❌ A database error occurred during registration. Please try again.", "danger")
            return redirect('/student-register')
            
    return render_template('student_register.html')




def notify_via_whatsapp(phone, parent_name, subject, parent_phone):
    import pywhatkit
    if not phone.startswith('+'):
        phone = f"+91{phone}"
    try:
        msg = f"New Lead: {parent_name}'s number {parent_phone} for {subject}"
        pywhatkit.sendwhatmsg_instantly(phone, msg, 15, True, 2)
    except Exception as e:
        print(f"Error: {e}")


@app.route('/send_request/<int:t_id>', methods=['POST'])
def send_request(t_id):
    if request.method == 'POST':
        p_name = request.form.get('parent_name')
        p_phone = request.form.get('parent_phone')
        p_msg = request.form.get('message')

        new_entry = ParentRequest(
            parent_name=p_name, 
            parent_phone=p_phone, 
            message=p_msg, 
            teacher_id=t_id
        )
        db.session.add(new_entry)
        db.session.commit()

        teacher = Teacher.query.get(t_id)

        if teacher.phone:
            thread = threading.Thread(
                target=notify_via_whatsapp, 
                args=(teacher.phone, p_name, teacher.subject, p_phone) 
            )
            thread.start()

        return "<h3>Request Sent Successfully! <a href='/'>Go Back</a></h3>"


@app.route('/update_status/<int:req_id>/<string:new_status>')
def update_status(req_id, new_status):
    req = ParentRequest.query.get_or_404(req_id)
    req.status = new_status
    db.session.commit()
    # '/dashboard/id' ke bajaye direct teacher dashboard par bheinjiye jahan session active hai
    return redirect('/teacher_dashboard')


@app.route('/about')
def about():
    return render_template('about.html')





@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        student = Student.query.filter_by(email=email, password=password).first()
        
        if student:
            session['student_id'] = student.id 
            return redirect('/student-dashboard') 
        else:
            flash("❌ Invalid credentials!")
    return render_template('student_login.html')


@app.route('/logout')
def logout():
    session.pop('student_id', None)
    session.pop('teacher_id', None)
    return redirect('/')


@app.route('/student-dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect('/student-login')
    
    s_id = session['student_id']
    student = Student.query.get(s_id)
    teacher = Teacher.query.get(student.teacher_id)
    current_month = datetime.now().strftime('%B %Y')
    
    fee_record = FeeRecord.query.filter_by(student_id=s_id, month=current_month, status='Paid').first()
    is_paid = fee_record is not None
    
    records = Attendance.query.filter_by(student_id=s_id).order_by(Attendance.date.desc()).limit(10).all()
    
    total = Attendance.query.filter_by(student_id=s_id).count()
    present = Attendance.query.filter_by(student_id=s_id, status='Present').count()
    attendance_pct = round((present / total * 100), 1) if total > 0 else 0


    # Yeh code /student-dashboard route ke andar rahega:
    student = Student.query.get(session['student_id']) # Single student object

    all_notices = Notice.query.filter_by(teacher_id=student.teacher_id).order_by(Notice.date_posted.desc()).all()

    relevant_notices = []
    for n in all_notices:
        if n.target_type == 'all':
            relevant_notices.append(n)
        elif n.target_type == 'batch' and n.target_value == student.grade:
            relevant_notices.append(n)
        elif n.target_type == 'individual' and n.target_value == str(student.id):
            relevant_notices.append(n)
        
    return render_template('student_dashboard.html', 
                           student=student, 
                           teacher=teacher,
                           is_paid=is_paid, 
                           attendance=attendance_pct,
                           attendance_records=records,
                           current_month=current_month,
                           notices=relevant_notices)
    

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'student_id' not in session:
        return redirect('/student-login')
    
    student = Student.query.get(session['student_id'])
    
    if request.method == 'POST':
        student.name = request.form['name']
        student.email = request.form['email']
        student.grade = request.form['grade']
        student.area = request.form['area']
        
        db.session.commit()
        return redirect('/student-profile')
        
    return render_template('edit_profile.html', student=student)


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'student_id' not in session:
        return redirect('/student-login')
    
    if request.method == 'POST':
        old_pass = request.form['old_password']
        new_pass = request.form['new_password']
        confirm_pass = request.form['confirm_password']
        
        student = Student.query.get(session['student_id'])
        
        if student.password != old_pass:
            return "Old password is incorrect!"
        if new_pass != confirm_pass:
            return "New passwords do not match!"
            
        student.password = new_pass
        db.session.commit()
        return "<h3>Password updated successfully! <a href='/student-profile'>Back to Profile</a></h3>"
        
    return render_template('change_password.html')



@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    
    t_id = session['teacher_id']
    teacher = Teacher.query.get(t_id)
    subscription_plan = teacher.subscription_plan or 'Starter'
    my_students = ParentRequest.query.filter_by(teacher_id=t_id, status='Pending').all()
    print(f"DEBUG: Found {len(my_students)} requests for Teacher ID {t_id}")

    action = request.args.get('action')
    target_req_id = request.args.get('req_id')
    
    if action and target_req_id:
        target_request = ParentRequest.query.filter_by(id=target_req_id, teacher_id=t_id).first()
        if target_request:
            if action == 'mark_called':
                target_request.status = 'Called'
            elif action == 'mark_completed':
                target_request.status = 'Completed'
            db.session.commit()
            return redirect('/teacher_dashboard')

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
    
    current_date = datetime.now().date()
    start_of_month = current_date.replace(day=1)
    
    total_sessions_query = Attendance.query.filter(
        Attendance.teacher_id == t_id,
        Attendance.date >= start_of_month
    ).count()
    
    total_present_query = Attendance.query.filter(
        Attendance.teacher_id == t_id,
        Attendance.date >= start_of_month,
        Attendance.status == 'Present'
    ).count()
    
    monthly_attendance_pct = (total_present_query / total_sessions_query * 100) if total_sessions_query > 0 else 0
    monthly_attendance_pct = round(monthly_attendance_pct, 1)
    
    return render_template('teacher_dashboard.html', 
                           teacher=teacher, 
                           students=my_students,
                           total_earnings=total_earnings,
                           monthly_earnings=monthly_earnings,
                           current_month=current_month_str,
                           attendance_pct=monthly_attendance_pct,
                           plan=subscription_plan)


@app.route('/edit-teacher-profile', methods=['GET', 'POST'])
def edit_teacher_profile():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    
    teacher = Teacher.query.get(session['teacher_id'])
    subscription_plan = session.get('subscription_plan', 'Starter')
    if request.method == 'POST':
        teacher.area = request.form['area']
        teacher.subject = request.form['subject']
        teacher.grade = request.form['grade']
        teacher.tutor_type = request.form['tutor_type']
        
        # Security Feature integration (Change Password inside Profile)
        new_pass = request.form.get('new_password')
        if new_pass and new_pass.strip():
            teacher.password = new_pass.strip()
            
        db.session.commit()
        return redirect('/teacher_dashboard')
        
    return render_template('edit_teacher_profile.html', teacher=teacher,plan=subscription_plan)





@app.route('/my-students')
def my_students():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    
    t_id = session['teacher_id']
    students_list = Student.query.filter_by(teacher_id=t_id, status='Active').all()
    subscription_plan = session.get('subscription_plan', 'Starter')
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
        
        if total_days > 0:
            s.calc_attendance = round((present_days / total_days) * 100, 1)
        else:
            s.calc_attendance = 0 

    teacher = Teacher.query.get(t_id)
    return render_template('my_students.html', students=students_list, teacher=teacher,plan=subscription_plan)


@app.route('/move-to-active/<int:req_id>')
def move_to_active(req_id):
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
        
    t_id = session['teacher_id']
    req = ParentRequest.query.get_or_404(req_id)
    req.status = 'Active'
    
    existing_student = Student.query.filter_by(phone=req.parent_phone).first()
    
    if not existing_student:
        student_grade = req.grade if req.grade else "Not Specified"
        student_area = "Indrapuri" 
        fee_value = req.monthly_fee if hasattr(req, 'monthly_fee') and req.monthly_fee else 0.0

        new_student = Student(
            name=req.parent_name,
            phone=req.parent_phone,
            teacher_id=t_id,
            grade=student_grade,
            area=student_area,
            monthly_fee=fee_value, 
            status='Active',       
            email=f"{req.parent_name.replace(' ', '').lower()}{req.id}@tutor.com", 
            password="password123" 
        )
        db.session.add(new_student)
    else:
        existing_student.teacher_id = t_id
        if hasattr(req, 'monthly_fee') and req.monthly_fee:
            existing_student.monthly_fee = req.monthly_fee

    db.session.commit()
    return redirect('/my-students')


@app.route('/remove-student/<int:req_id>')
def remove_student(req_id):
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
        
    req = ParentRequest.query.get_or_404(req_id)
    linked_student = Student.query.filter_by(phone=req.parent_phone).first()
    
    if linked_student:
        Attendance.query.filter_by(student_id=linked_student.id).delete()
        FeeRecord.query.filter_by(student_id=linked_student.id).delete()
        db.session.delete(linked_student)
    
    db.session.delete(req)
    db.session.commit()
    return redirect('/my-students')


@app.route('/add-student-manual', methods=['POST'])
def add_student_manual():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')

    t_id = session['teacher_id']
    p_name = request.form.get('parent_name')
    p_phone = request.form.get('parent_phone')
    p_grade = request.form.get('grade') or "Not Specified"
    fee = request.form.get('monthly_fee')
    
    fee_value = float(fee) if fee and fee.strip() else 0.0
    
    existing_student = Student.query.filter_by(phone=p_phone, teacher_id=t_id).first()
    
    if not existing_student:
        new_student = Student(
            name=p_name,
            phone=p_phone, 
            grade=p_grade,
            monthly_fee=fee_value,
            teacher_id=t_id,
            status='Active', 
            area="Bhopal",
            email=f"{p_name.replace(' ', '').lower()}{p_phone[-4:]}@tutor.com",
            password="password123"
        )
        db.session.add(new_student)
    else:
        existing_student.status = 'Active'
        existing_student.monthly_fee = fee_value

    new_request = ParentRequest(
        parent_name=p_name,
        parent_phone=p_phone,
        grade=p_grade,
        monthly_fee=fee_value,
        teacher_id=t_id,
        status='Active'
    )
    db.session.add(new_request)
    db.session.commit()
    return redirect('/my-students')


@app.route('/attendance-dashboard')
def attendance_dashboard():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    subscription_plan = session.get('subscription_plan', 'Starter') 
    t_id = session['teacher_id']
    my_students = Student.query.filter_by(teacher_id=t_id, status='Active').all()
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('attendance_dashboard.html', students=my_students, today_date=current_date,plan=subscription_plan)


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


@app.route('/get-calendar-month/<int:s_id>')
def get_calendar_month(s_id):
    t_id = session.get('teacher_id')
    today = datetime.now()
    curr_month = today.month
    curr_year = today.year
    
    records = Attendance.query.filter(
        Attendance.student_id == s_id,
        Attendance.teacher_id == t_id,
        db.extract('month', Attendance.date) == curr_month,
        db.extract('year', Attendance.date) == curr_year
    ).all()

    attendance_map = {r.date.strftime("%Y-%m-%d"): r.status for r in records}
    cal = calendar.monthcalendar(curr_year, curr_month)
    
    return {
        "month_name": today.strftime("%B %Y"),
        "calendar": cal,
        "attendance": attendance_map,
        "today": today.strftime("%Y-%m-%d")
    }
    

@app.route('/student-history/<int:s_id>')
def student_history(s_id):
    t_id = session.get('teacher_id')
    records = Attendance.query.filter_by(student_id=s_id, teacher_id=t_id).all()
    history = [{"date": r.date.strftime("%Y-%m-%d"), "status": r.status} for r in records]
    return {"history": history}


@app.route('/collect-fee', methods=['GET', 'POST'])
def collect_fee():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    subscription_plan = session.get('subscription_plan', 'Starter')
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
            
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"Database Error: {e}"
        
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
                           current_month=current_month,
                           plan=subscription_plan)


@app.route('/generate-receipt/<int:s_id>/<month>')
def generate_receipt(s_id, month):
    is_teacher = 'teacher_id' in session
    is_self_student = 'student_id' in session and session['student_id'] == s_id
    
    if not is_teacher and not is_self_student:
        return "Unauthorized Access", 403
    
    student = Student.query.get_or_404(s_id)
    teacher = Teacher.query.get(student.teacher_id)
    
    record = FeeRecord.query.filter_by(
        student_id=s_id, 
        month=month, 
        status='Paid'
    ).first_or_404()

    return render_template('receipt_template.html', 
                           teacher=teacher, 
                           student=student, 
                           record=record)   


@app.route('/student-profile')
def student_profile():
    if 'student_id' not in session:
        flash("Please log in to access your profile.", "danger")
        return redirect('/student-login')
        
    # Student fetch parameters
    current_student = Student.query.get_or_404(session['student_id'])
    
    # 👑 FIX 1: 'Attendance' query is correct
    attendance_data = Attendance.query.filter_by(student_id=current_student.id).all()
    
    # 👑 FIX 2: Model name badal kar 'FeeRecord' kiya jo aapke DB mein hai
    fee_records = FeeRecord.query.filter_by(student_id=current_student.id).all()
    
    # Render map framework syncing variables smoothly
    return render_template(
        'student_profile.html', 
        student=current_student, 
        attendance=attendance_data, 
        fees=fee_records # 'fees' variable template loop ke liye perfectly loaded hai
    )



@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        purpose = request.form.get('purpose')  # Business / Support / Feedback
        message = request.form.get('message')
        
        if not name or not email or not message:
            flash("Please fill all required fields.", "danger")
            return redirect('/contact')
            
        # Professional Email Draft
        subject = f"🚀 New Client Strategy Ticket: {purpose} from {name}"
        msg = Message(subject, recipients=[app.config['MAIL_USERNAME']])
        
        msg.html = f"""
            <div style="font-family: Arial, sans-serif; padding: 25px; color: #18181b; background-color: #fcfbfc; max-width: 600px; border: 1px solid #e4e4e7; border-radius: 16px;">
                <h3 style="color: #18181b; border-bottom: 1px solid #e4e4e7; padding-bottom: 12px; font-weight: bold; letter-spacing: -0.02em;">New Strategy Inbound Lead</h3>
                <p style="margin: 10px 0;"><strong>Identity:</strong> {name}</p>
                <p style="margin: 10px 0;"><strong>Mailing Channel:</strong> {email}</p>
                <p style="margin: 10px 0;"><strong>Objective:</strong> <span style="background: #f4f4f5; color: #18181b; padding: 4px 12px; border-radius: 50px; font-size: 0.85rem; font-weight: 600; border: 1px solid #e4e4e7;">{purpose}</span></p>
                <div style="background: #ffffff; padding: 18px; border-radius: 12px; margin-top: 20px; border: 1px solid #e4e4e7; box-shadow: 0 4px 12px rgba(0,0,0,0.01);">
                    <p style="margin: 0; line-height: 1.6; color: #71717a; font-style: italic;">"{message}"</p>
                </div>
                <br>
                <p style="font-size: 0.75rem; color: #a1a1aa; margin-top: 15px;">Automated stream from TutorFlow Core Desk.</p>
            </div>
        """
        
        # Dispatch background mail safely
        thr = threading.Thread(target=send_async_email, args=[app, msg])
        thr.start()
        
        flash("Your message has been sent successfully! We will get back to you shortly.", "success")
        return redirect('/contact')
        
    return render_template('contact.html')

 # ==============================================================================
# 👑 PERMANENTLY ACCOUNT DELETION ROUTE
# ==============================================================================
@app.route('/delete-teacher-account')
def delete_teacher_account():
    if 'teacher_id' not in session:
        flash("Unauthorized access blocked.", "danger")
        return redirect('/teacher-login')

    try:
        teacher_to_delete = Teacher.query.get_or_404(session['teacher_id'])
        
        # 👑 CRITICAL FIXED SEQUENCE WITH CAPITAL 'False'
        students_of_teacher = Student.query.filter_by(teacher_id=teacher_to_delete.id).all()
        student_ids = [s.id for s in students_of_teacher]

        # Child constraint checks with Python standard True/False definitions
        if student_ids:
            Attendance.query.filter(Attendance.student_id.in_(student_ids)).delete(synchronize_session=False)
            FeeRecord.query.filter(FeeRecord.student_id.in_(student_ids)).delete(synchronize_session=False)

        Attendance.query.filter_by(teacher_id=teacher_to_delete.id).delete()
        FeeRecord.query.filter_by(teacher_id=teacher_to_delete.id).delete()
        ParentRequest.query.filter_by(teacher_id=teacher_to_delete.id).delete()
        
        Student.query.filter_by(teacher_id=teacher_to_delete.id).delete()

        # Final purge transaction execution
        db.session.delete(teacher_to_delete)
        db.session.commit()
        
        session.clear()
        flash("✨ Account and all records purged successfully.", "success")
        return redirect('/')
        
    except Exception as e:
        db.session.rollback()
        print(f"Purging Failure Database Error: {e}")
        flash("❌ Systems Error: Unable to complete account deletion.", "danger")
        return redirect('/teacher_dashboard')




@app.route('/broadcast-notice', methods=['GET', 'POST'])
def broadcast_notice():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    subscription_plan = session.get('subscription_plan', 'Starter')
    t_id = session['teacher_id']
    teacher = Teacher.query.get_or_404(t_id)
    students = Student.query.filter_by(teacher_id=t_id, status='Active').all()
    batches = list(set([s.grade for s in students if s.grade]))

    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        target_type = request.form.get('target_type')

        if target_type == 'batch':
            target_val = request.form.get('selected_batch')
            new_notice = Notice(teacher_id=t_id, title=title, message=message, target_type='batch', target_value=str(target_val))
            db.session.add(new_notice)
            
        elif target_type == 'individual':
            # Get list of all checked student IDs
            selected_ids = request.form.getlist('selected_student_ids')
            for s_id in selected_ids:
                new_notice = Notice(teacher_id=t_id, title=title, message=message, target_type='individual', target_value=str(s_id))
                db.session.add(new_notice)
        else:
            new_notice = Notice(teacher_id=t_id, title=title, message=message, target_type='all', target_value=None)
            db.session.add(new_notice)

        db.session.commit()
        flash("📢 Notice Broadcasted Successfully!", "success")
        return redirect('/broadcast-notice')

    sent_notices = Notice.query.filter_by(teacher_id=t_id).order_by(Notice.date_posted.desc()).all()
    return render_template('broadcast_notice.html', teacher=teacher, students=students, batches=batches, notices=sent_notices,plan=subscription_plan)



@app.route('/delete-notice/<int:n_id>')
def delete_notice(n_id):
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    
    notice = Notice.query.get_or_404(n_id)
    if notice.teacher_id == session['teacher_id']:
        db.session.delete(notice)
        db.session.commit()
        flash("Notice deleted successfully.", "info")
        
    return redirect('/broadcast-notice')


# Inside @app.route('/student-dashboard')


@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


from flask import render_template, session, redirect, url_for, flash, request
from datetime import datetime, timedelta

# --- ROUTE 1: MANAGE SUBSCRIPTION PAGE ---
import datetime as dt
from flask import render_template, session, redirect, url_for, flash, request


# --- ROUTE 1: MANAGE SUBSCRIPTION PAGE ---
@app.route('/manage-subscription')
def manage_subscription():
    if 'teacher_id' not in session:
        flash('Please login first!', 'danger')
        return redirect('/teacher-login')

    teacher = Teacher.query.get(session['teacher_id'])
    if not teacher:
        return redirect('/teacher-login')

    # 👑 Auto-check Expiry: If 14 days passed, downgrade to Starter automatically
    if teacher.plan_expiry and datetime.now() > teacher.plan_expiry:
        teacher.subscription_plan = 'Starter'
        teacher.subscription_status = 'Expired'
        teacher.plan_expiry = None
        db.session.commit()
        flash('Your 14-Day Pro Trial has ended. Account switched to Starter Plan.', 'info')

    # Pricing & Date details for template
    if teacher.subscription_plan == 'Starter':
        billing_cycle = "₹0 / Forever Free"
        renewal_date = "N/A (Free Plan)"
    else:
        billing_cycle = "₹299 / Month"
        renewal_date = teacher.plan_expiry.strftime('%d %B, %Y') if teacher.plan_expiry else "N/A"

    return render_template(
        'manage_subscription.html',
        plan=teacher.subscription_plan,
        status=teacher.subscription_status,
        billing_cycle=billing_cycle,
        renewal_date=renewal_date
    )
# --- ROUTE 2: UPGRADE / CANCEL ACTION HANDLER ---
@app.route('/update-subscription-plan', methods=['POST'])
def update_subscription_plan():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))
    
    action = request.form.get('action')
    if action == 'cancel':
        session['subscription_status'] = 'Cancelled'
    elif action == 'renew':
        session['subscription_status'] = 'Active'

    return redirect(url_for('manage_subscription'))



# --- 1. PAYMENT / TRIAL CHECKOUT PAGE ---
@app.route('/checkout/<plan_name>')
def checkout(plan_name):
    if 'teacher_id' not in session:
        flash('Please login to start your Pro trial or subscription!', 'warning')
        return redirect(url_for('teacher_login'))
    
    price = "299" if plan_name == 'pro' else "0"
    display_title = "Pro Educator (14-Day Free Trial)" if plan_name == 'pro' else "Starter Plan"
    
    return render_template('checkout.html', plan_name=plan_name, display_title=display_title, price=price)





# --- 2. PAYMENT CONFIRMATION & EMAIL SENDER ---
@app.route('/process-subscription', methods=['POST'])
def process_subscription():
    if 'teacher_id' not in session:
        flash('Please login first!', 'warning')
        return redirect('/teacher-login')

    t_id = session['teacher_id']
    teacher = Teacher.query.get(t_id)

    if not teacher:
        flash('Teacher profile not found. Please log in again.', 'danger')
        return redirect('/teacher-login')

    user_email = teacher.email
    user_name = teacher.name
    plan_choice = request.form.get('plan_choice', 'Pro Educator')

    # 👑 Save 14-day expiry date directly into the database
    expiry_datetime = datetime.now() + timedelta(days=14)
    teacher.subscription_plan = 'Pro Educator'
    teacher.subscription_status = 'Active'
    teacher.plan_expiry = expiry_datetime
    db.session.commit()

    renewal_date_str = expiry_datetime.strftime('%d %B, %Y')

    # 📧 EMAIL 1: User Confirmation
    try:
        msg_user = Message(
            subject="🎉 Congratulations! Your TutorFlow Pro Trial is Active",
            recipients=[user_email]
        )
        msg_user.html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f8fafc;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 16px; border: 1px solid #e2e8f0;">
                <h2 style="color: #a855f7;">Welcome to TutorFlow Pro! 🚀</h2>
                <p>Hi <strong>{user_name}</strong>,</p>
                <p>Congratulations! Your <strong>14-Day Free Trial for Pro Educator Plan</strong> has been activated successfully.</p>
                <div style="background: #f1f5f9; padding: 15px; border-radius: 12px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Active Plan:</strong> Pro Educator Trial</p>
                    <p style="margin: 5px 0;"><strong>Trial Valid Until:</strong> {renewal_date_str}</p>
                    <p style="margin: 5px 0;"><strong>Amount Charged:</strong> ₹0.00 (Trial Period)</p>
                </div>
                <p>You can now generate unlimited PDF fee receipts, track student attendance, and send WhatsApp notifications effortlessly!</p>
                <br>
                <p style="color: #64748b; font-size: 12px;">Need help? Reply to this email or contact tutorflowonline@gmail.com</p>
            </div>
        </div>
        """
        mail.send(msg_user)

        # 📧 EMAIL 2: Admin Notification
        msg_admin = Message(
            subject=f"🔔 New Subscriber Alert: {user_name} subscribed to Pro Trial",
            recipients=['tutorflowonline@gmail.com']
        )
        msg_admin.html = f"""
        <h3>New Pro Subscription Activated!</h3>
        <p><strong>Teacher Name:</strong> {user_name}</p>
        <p><strong>Email ID:</strong> {user_email}</p>
        <p><strong>Plan Chosen:</strong> {plan_choice} (14-Day Trial)</p>
        <p><strong>Activation Date:</strong> {datetime.now().strftime('%d %B, %Y %I:%M %p')}</p>
        <p><strong>Expiry Date:</strong> {renewal_date_str}</p>
        """
        mail.send(msg_admin)

    except Exception as e:
        print(f"Email Error: {e}")

    flash('🎉 Congratulations! Your Pro Educator 14-Day Free Trial is now active!', 'success')
    return redirect('/manage-subscription')
  
  
  
  
  
# 👑 GLOBAL TEMPLATE CONTEXT (Available in all HTML templates automatically)
@app.context_processor
def inject_user_plan():
    if 'teacher_id' in session:
        teacher = Teacher.query.get(session['teacher_id'])
        if teacher:
            # Check expiry automatically
            if teacher.plan_expiry and datetime.now() > teacher.plan_expiry:
                teacher.subscription_plan = 'Starter'
                teacher.subscription_status = 'Expired'
                teacher.plan_expiry = None
                db.session.commit()
            return {'plan': teacher.subscription_plan or 'Starter'}
    return {'plan': 'Starter'}
  
# --- TEACHER STUDY MATERIAL & QUIZ DESK ---



# --- ATTEMPT QUIZ PAGE ---
# --- TEACHER STUDY MATERIAL & QUIZ DESK ---
@app.route('/teacher/study-material', methods=['GET', 'POST'])
def teacher_study_material():
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    
    t_id = session['teacher_id']
    teacher = Teacher.query.get_or_404(t_id)
    
    if request.method == 'POST':
        action_type = request.form.get('action_type')
        
        # 1. Add Material (PDF / Doc / Image / Link)
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
            flash("✨ Material shared with class successfully!", "success")

        # 2. Add Quiz (Supports direct import from NotebookLM / JSON / Plain text)
        elif action_type == 'add_quiz':
            title = request.form.get('quiz_title')
            grade = request.form.get('quiz_grade')
            raw_quiz_data = request.form.get('raw_quiz_data')
            
            try:
                # Validate JSON format
                parsed = json.loads(raw_quiz_data)
                total_marks = len(parsed)
                new_quiz = Quiz(
                    teacher_id=t_id,
                    title=title,
                    grade=grade,
                    questions_json=json.dumps(parsed),
                    total_marks=total_marks
                )
                db.session.add(new_quiz)
                db.session.commit()
                flash("🎯 Quiz created successfully!", "success")
            except Exception as e:
                flash(f"⚠️ Invalid Quiz Format. Please provide valid JSON. Error: {e}", "danger")

        return redirect('/teacher/study-material')

    materials = StudyMaterial.query.filter_by(teacher_id=t_id).order_by(StudyMaterial.date_shared.desc()).all()
    quizzes = Quiz.query.filter_by(teacher_id=t_id).order_by(Quiz.created_at.desc()).all()
    submissions = QuizSubmission.query.join(Quiz).filter(Quiz.teacher_id == t_id).order_by(QuizSubmission.submitted_at.desc()).all()

    return render_template('teacher_study_material.html', 
                           teacher=teacher, 
                           materials=materials, 
                           quizzes=quizzes, 
                           submissions=submissions)


# --- STUDENT STUDY & QUIZ PORTAL ---
@app.route('/student/study-material')
def student_study_material():
    if 'student_id' not in session:
        return redirect('/student-login')
    
    student = Student.query.get_or_404(session['student_id'])
    
    # Fetch materials and quizzes matching student's grade and teacher
    materials = StudyMaterial.query.filter_by(teacher_id=student.teacher_id, grade=student.grade).all()
    quizzes = Quiz.query.filter_by(teacher_id=student.teacher_id, grade=student.grade).all()
    
    # Map attempted quizzes with scores
    student_submissions = {sub.quiz_id: sub for sub in QuizSubmission.query.filter_by(student_id=student.id).all()}

    return render_template('student_study_material.html', 
                           student=student, 
                           materials=materials, 
                           quizzes=quizzes,
                           submissions=student_submissions)


# --- ATTEMPT QUIZ PAGE ---
@app.route('/student/attempt-quiz/<int:quiz_id>', methods=['GET', 'POST'])
def attempt_quiz(quiz_id):
    if 'student_id' not in session:
        return redirect('/student-login')

    student = Student.query.get_or_404(session['student_id'])
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = json.loads(quiz.questions_json)

    # Check if already attempted
    existing_submission = QuizSubmission.query.filter_by(quiz_id=quiz.id, student_id=student.id).first()

    if request.method == 'POST':
        score = 0
        total = len(questions)

        for idx, q in enumerate(questions):
            selected_option = request.form.get(f'question_{idx}')
            if selected_option and selected_option.strip().lower() == q.get('answer', '').strip().lower():
                score += 1

        if existing_submission:
            existing_submission.score = score
            existing_submission.submitted_at = datetime.now(timezone.utc)
        else:
            submission = QuizSubmission(
                quiz_id=quiz.id,
                student_id=student.id,
                score=score,
                total=total
            )
            db.session.add(submission)
        
        db.session.commit()
        flash(f"🎉 Test Submitted! Your Score: {score}/{total}", "success")
        return redirect('/student/study-material')

    return render_template('attempt_quiz.html', quiz=quiz, questions=questions, submission=existing_submission)
  
# Delete Study Material
@app.route('/teacher/delete-material/<int:mat_id>')
def delete_study_material(mat_id):
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    mat = StudyMaterial.query.get_or_404(mat_id)
    if mat.teacher_id == session['teacher_id']:
        db.session.delete(mat)
        db.session.commit()
        flash("Study material deleted successfully.", "info")
    return redirect('/teacher/study-material')

# Delete Quiz & Its Submissions
@app.route('/teacher/delete-quiz/<int:quiz_id>')
def delete_quiz(quiz_id):
    if 'teacher_id' not in session:
        return redirect('/teacher-login')
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.teacher_id == session['teacher_id']:
        # Delete related submissions first
        QuizSubmission.query.filter_by(quiz_id=quiz.id).delete()
        db.session.delete(quiz)
        db.session.commit()
        flash("Quiz and its submission records deleted successfully.", "info")
    return redirect('/teacher/study-material')
  
if __name__ == '__main__':
    app.run(debug=True)
