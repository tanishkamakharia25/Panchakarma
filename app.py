from flask import Flask, render_template, request, redirect, url_for
import json
from twilio.rest import Client
from flask_mail import Mail, Message
from src.logger import logger

app = Flask(__name__)

# ------------------ Flask-Mail Configuration ------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

# ------------------ Twilio SMS Configuration ------------------
TWILIO_ACCOUNT_SID = 'your_twilio_sid'
TWILIO_AUTH_TOKEN = 'your_twilio_auth_token'
TWILIO_PHONE_NUMBER = '+1234567890'
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ------------------ JSON Data Handling ------------------
def load_json(file_name):
    try:
        with open(file_name, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(data, file_name):
    with open(file_name, "w") as f:
        json.dump(data, f, indent=4)

# ------------------ Routes ------------------

# 1. Index Page
@app.route('/')
def index():
    return render_template('index.html')

# 2. Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    if request.method == 'POST':
        user_type = request.form['type']
        name = request.form['name']
        email = request.form['email']
        password = request.form.get('password', '')
        extra = request.form.get('license', '')

        if user_type == 'user':
            users = load_json('users.json')
            users[name] = {'email': email, 'password': password}
            save_json(users, 'users.json')
        else:
            practitioners = load_json('practitioners.json')
            practitioners[name] = {'email': email, 'password': password, 'license': extra}
            save_json(practitioners, 'practitioners.json')

        logger.info(f"New signup: {name} ({user_type})")
        return redirect(url_for('index'))
    return render_template('signup.html')

# 3. Schedule Page
@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        patient_name = request.form['name']
        therapy = request.form['therapy']
        date = request.form['date']
        time = request.form['time']
        phone = request.form['phone']
        email = request.form['email']

        patients = load_json("patients.json")
        if patient_name not in patients:
            patients[patient_name] = []
        patients[patient_name].append({
            "therapy": therapy,
            "date": date,
            "time": time,
            "feedback": None,
            "phone": phone,
            "email": email
        })
        save_json(patients, "patients.json")

        # Send SMS
        try:
            client.messages.create(
                to=phone,
                from_=TWILIO_PHONE_NUMBER,
                body=f"Hello {patient_name}, your {therapy} session is scheduled on {date} at {time}."
            )
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")

        # Send Email
        try:
            msg = Message("Panchakarma Therapy Scheduled",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.body = f"Dear {patient_name},\nYour {therapy} session is scheduled on {date} at {time}.\nPlease follow pre-procedure guidelines."
            mail.send(msg)
        except Exception as e:
            logger.error(f"Email sending failed: {e}")

        logger.info(f"Scheduled therapy: {patient_name} - {therapy} on {date} at {time}")
        return redirect(url_for('index'))
    return render_template('schedule.html')

# 4. Feedback Page
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        patient_name = request.form['name']
        therapy = request.form['therapy']
        feedback_text = request.form['feedback']

        patients = load_json("patients.json")
        if patient_name in patients:
            for session in patients[patient_name]:
                if session['therapy'] == therapy:
                    session['feedback'] = feedback_text
                    break
            save_json(patients, "patients.json")
            logger.info(f"Feedback submitted: {patient_name} - {therapy}")
        return redirect(url_for('index'))
    return render_template('feedback.html')

# 5. Progress Page
@app.route('/progress/<patient_name>')
def progress(patient_name):
    patients = load_json("patients.json")
    if patient_name in patients:
        feedback_counts = {}
        for session in patients[patient_name]:
            if session['feedback']:
                feedback_counts[session['therapy']] = feedback_counts.get(session['therapy'], 0) + 1
        return render_template('progress.html',
                               patient_name=patient_name,
                               feedback_data=feedback_counts if feedback_counts else None)
    return "Patient not found"

# 6. Precautions Page
@app.route('/precautions')
def precautions():
    return render_template('precautions.html')

# 7. Upcoming Sessions (Registered Users)
@app.route('/upcoming/<patient_name>')
def upcoming(patient_name):
    patients = load_json("patients.json")
    sessions = patients.get(patient_name, [])
    return render_template('upcoming.html', sessions=sessions)

# 8. Before/After Page (Registered Users)
@app.route('/before_after/<patient_name>', methods=['GET', 'POST'])
def before_after(patient_name):
    data_store = load_json('before_after.json')
    if request.method == 'POST':
        before_issues = request.form.get('before_issues','')
        after_issues = request.form.get('after_issues','')
        data_store[patient_name] = {'before': before_issues, 'after': after_issues}
        save_json(data_store, 'before_after.json')
        logger.info(f"Before/After updated for {patient_name}")
        return redirect(url_for('index'))

    data = data_store.get(patient_name, {'before':'','after':''})
    return render_template('before_after.html', data=data)

# 9. About Page
@app.route('/about')
def about():
    return render_template('about.html')

# ------------------ Run Flask App ------------------
if __name__ == '__main__':
    app.run(debug=True)