from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///company_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret-key-CHANGE-THIS' 

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MODELS ---
class EmployeeLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.String(100), nullable=False)
    app_name = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100))
    timestamp = db.Column(db.String(50), nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.String(100), primary_key=True)
    password = db.Column(db.String(200)) 
    start_hour = db.Column(db.Integer, default=9)
    end_hour = db.Column(db.Integer, default=18)
    is_admin = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

with app.app_context():
    db.create_all()
    if not User.query.get('admin'):
        admin = User(id='admin', password='admin123', is_admin=True)
        db.session.add(admin)
        db.session.commit()

# --- ROUTES ---

@app.route('/get_settings/<system_id>')
def get_settings(system_id):
    user = User.query.get(system_id)
    return jsonify({"start": user.start_hour if user else 9, "end": user.end_hour if user else 18})

@app.route('/upload', methods=['POST'])
def receive_data():
    try:
        data = request.get_json()
        new_log = EmployeeLog(
            system_id=data['system_id'], app_name=data['app'], duration=data['time'], 
            location=data['loc'], timestamp=data['timestamp']
        )
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"message": "Saved"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.get(username): return "User exists!"
        
        new_user = User(
            id=username, 
            password=password, 
            start_hour=int(request.form.get('start')), 
            end_hour=int(request.form.get('end'))
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.get(request.form.get('username'))
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('admin_panel' if user.is_admin else 'employee_dashboard'))
        return "Invalid Login"
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def employee_dashboard():
    logs = EmployeeLog.query.filter_by(system_id=current_user.id).all()
    app_usage = {}
    for log in logs: app_usage[log.app_name] = app_usage.get(log.app_name, 0) + log.duration
    
    return render_template('dashboard.html', 
                           labels=list(app_usage.keys()), 
                           data_values=[round(v/60, 1) for v in app_usage.values()])

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin: return "Admins Only"

    selected_user = request.args.get('user', 'all')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    query = EmployeeLog.query
    if selected_user != 'all': query = query.filter_by(system_id=selected_user)
    if start_date: query = query.filter(EmployeeLog.timestamp >= start_date)
    if end_date: query = query.filter(EmployeeLog.timestamp <= end_date + " 23:59:59")
    
    logs = query.all()
    all_users_data = User.query.all()

    app_usage = {}
    total_seconds = 0
    timeline_data = []

    for log in logs:
        app_usage[log.app_name] = app_usage.get(log.app_name, 0) + log.duration
        total_seconds += log.duration
        
        end_dt = datetime.strptime(log.timestamp, '%Y-%m-%d %H:%M:%S')
        start_dt = end_dt - timedelta(seconds=log.duration)
        
        # --- FIXED SECTION: SENDING CLEAN STRINGS ---
        timeline_data.append({
            'row_label': log.system_id if selected_user == 'all' else 'Activity',
            'bar_label': log.app_name,
            'start': start_dt.isoformat(), # Sends "2023-10-10T10:00:00"
            'end': end_dt.isoformat()
        })
        # --------------------------------------------

    return render_template('admin.html',
                           selected_user=selected_user,
                           all_employees=[r.system_id for r in db.session.query(EmployeeLog.system_id).distinct()],
                           labels=list(app_usage.keys()),
                           data_values=[round(v/60, 1) for v in app_usage.values()],
                           total_hours=round(total_seconds / 3600, 2),
                           timeline_data=timeline_data,
                           start_date=start_date,
                           end_date=end_date,
                           all_users_data=all_users_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)