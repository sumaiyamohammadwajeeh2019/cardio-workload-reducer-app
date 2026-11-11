from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import datetime
import csv, io, urllib.parse, sqlite3, os, math
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.name = "Cardio Work Reducer"
app.secret_key = "cardio123"
DB = "cardio.db"@app.route("/")
def index():
    return redirect("/workflow")

DOCTORS = ["Dr. Rahim", "Dr. Karim", "Dr. Sara", "Dr. Tanvir"]

# Users dictionary for login (doctor credentials)
USERS = {
    "dr. rahim": {"password": "generated_hash_for_dr_rahim", "role": "doctor"},
    "dr. karim": {"password": "generated_hash_for_dr_karim", "role": "doctor"},
    "dr. sara": {"password": "generated_hash_for_dr_sara", "role": "doctor"},
    "dr. tanvir": {"password": "generated_hash_for_dr_tanvir", "role": "doctor"},
}

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS patients(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, age TEXT, phone TEXT, bp TEXT, hr TEXT, ef TEXT, ecg TEXT,
        type TEXT, doctor TEXT, color TEXT, action TEXT, plan TEXT, auto_note TEXT, followup TEXT, discharge TEXT,
        time TEXT, date TEXT, history_count INTEGER, last_visit TEXT, last_ef TEXT, last_plan TEXT, ef_change TEXT, wa_link TEXT, status TEXT DEFAULT 'active')""")
    c.execute("""CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name_key TEXT, date TEXT, ef TEXT, plan TEXT, type TEXT)""")
    # Users table for login
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT)""")
    # Insert default admin if not exists
    cur = c.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        c.execute("INSERT INTO users(username,password_hash) VALUES(?,?)", ('admin', generate_password_hash('1234')))
    # Prescriptions table
    c.execute("""CREATE TABLE IF NOT EXISTS prescriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, medicine TEXT, dosage TEXT,
        frequency TEXT, doctor TEXT, date TEXT)""")
    c.commit()
    c.close()
init()

HTML = """
<!DOCTYPE html><html><head><title>Cardio Final + DB</title>
<style>body{font-family:Arial;max-width:1050px;margin:auto;padding:20px;background:#f4f7fa}
.card{background:white;padding:15px;border-radius:10px;margin:10px 0;box-shadow:0 2px 5px #ddd}
.red{border-left:6px solid red}.yellow{border-left:6px solid orange}.green{border-left:6px solid green}
input,select,textarea{width:100%;padding:8px;margin:5px 0}button{padding:9px 16px;background:#007bff;color:white;border:none;border-radius:5px;cursor:pointer}
.top{display:flex;gap:10px;flex-wrap:wrap}.box{flex:1;background:white;padding:12px;border-radius:10px;text-align:center;min-width:130px}
.flex{display:flex;gap:10px}.flex>*{flex:1}.hist{background:#fff3cd;padding:10px;border-radius:8px;margin-top:8px}
.badge{background:#d4edda;padding:3px 8px;border-radius:10px;font-size:12px}
@media print{form,.no-print{display:none!important}.card{box-shadow:none;border:1px solid #000}}
</style></head>
<body>
<div class="no-print" style="display:flex;justify-content:space-between">
  <b>👨‍⚕️ {{user}} | 💾 DB Saved | Total Visits Ever: {{total_visits}}</b>
  <a href="/qtc"><button style="background:#28a745; margin-left:10px;">QT Calculator</button></a>
  <a href="/risk"><button style="background:#fd7e14; margin-left:10px;">Risk</button></a>
  <a href="/dosage"><button style="background:#6c5ce7; margin-left:10px;">Dosage</button></a>
  <a href="/ecg"><button style="background:#00c9a7; margin-left:10px;">ECG</button></a>
  <a href="/patients"><button style="background:#6c7575; margin-left:10px;">Patients</button></a>
  <a href="/workflow"><button style="#e83e8c; margin-left:10px;">Workflow</button></a>
<a href="/prescriptions"><button style="#28a745; margin-left:10px;\">Prescriptions</button></a>
<a href="/smart-workload"><button style="#17a2b8; margin-left:10px;">Smart Workload</button></a>
   <a href="/burnout-meter"><button style="#dc3545; margin-left:10px;">Burnout</button></a>
   <a href="/sos-mode"><button style="#6c7575; margin-left:10px;">SOS</button></a>
   <a href="/language"><button style="#6c7575; margin-left:10px;">EN/BN</button></a>
  <a href="/changepassword"><button style="background:#ffc107; margin-left:10px;">Change Pass</button></a>
  <a href="/assistant"><button style="#6c7575; margin-left:10px;">Assistant</button></a>
  <a href="/logout"><button style="background:#dc3545;">Logout</button></a>
</div>
<h1>❤️ Cardio Workload - With Database</h1>
<div class="top"><div class="box"><h2>{{total}}</h2>Today Active</div><div class="box"><h2 style="color:red">{{urgent}}</h2>Urgent</div><div class="box"><h2>{{time_saved}} min</h2>Saved</div><div class="box"><h2>{{done_count}}</h2>Done Today</div></div>

<div class="card no-print"><h3>👨‍⚕️ Doctor-wise</h3><div class="flex">{% for d,c in doc_count.items() %}<div class="box"><b>{{d}}</b><h2>{{c}}</h2>{{"🔴 Overloaded" if c>=5 else "🟢 Normal"}}</div>{% endfor %}</div><p><b>Least Busy:</b> {{least_busy}}</p></div>

<div class="card no-print"><h3>+ Add Patient</h3>
<form method="POST" action="/add">
<div class="flex"><input name="name" placeholder="Patient Name" required><input name="age" placeholder="Age/Sex"><input name="phone" placeholder="Phone 01XXXXXXXXX"></div>
<div class="flex"><input name="bp" placeholder="BP 150/90"><input name="hr" placeholder="HR 95"><input name="ef" placeholder="EF %"></div>
<div class="flex"><input name="ecg" placeholder="ECG"><select name="doctor">{% for d in doctors %}<option>{{d}}</option>{% endfor %}</select></div>
<select name="type"><option>New Chest Pain</option><option>OPD Follow-up</option><option>Post-Stent / Post-CABG</option><option>Echo Report</option><option>ECG Review</option><option>Heart Failure</option></select>
<textarea name="notes" placeholder="Symptoms..."></textarea>
<select name="risk"><option value="1">Low</option><option value="2">Medium</option><option value="3">High</option></select>
<button>Add & Auto-Triage</button></form></div>

<div class="no-print" style="display:flex;gap:8px">
<form method="GET" action="/" style="flex:1;display:flex;gap:5px"><input name="q" placeholder="🔍 Search by name / phone..." value="{{q}}"><button>Search</button></form>
<a href="/export"><button style="background:green">📥 CSV</button></a><a href="/report"><button style="background:purple">📄 Daily Report</button></a><a href="/all"><button style="background:orange">📚 All History</button></a></div>

<h3>Today's Queue ({{patients|length}}) <span class="badge">Auto-Saved in DB</span></h3>
{% for p in patients %}<div class="card {{p.color}}"><b>{{p.name}} ({{p.age}})</b> - {{p.type}} | {{p.time}} | 👨‍⚕️ {{p.doctor}} | 📞 {{p.phone}}
{% if p.history_count>0 %}<div class="hist">📚 History: {{p.history_count}} no. visit | Ager: {{p.last_visit}} | Ager EF: {{p.last_ef}} | {{p.ef_change}}</div>{% else %}<div class="hist">🆕 New Patient</div>{% endif %}
<p>BP: {{p.bp}} | HR: {{p.hr}} | EF: {{p.ef}}% | ECG: {{p.ecg}}</p>
<p><b>🧠 Summary:</b> {{p.auto_note}}</p><p><b>💊 Plan:</b> {{p.plan}}</p><p><b>📅 Follow-up:</b> {{p.followup}}</p><p><b>📋 Discharge:</b> {{p.discharge}}</p>
<div class="no-print"><a href="/done/{{p.id}}">✅ Done</a> | <button onclick="window.print()">🖨️ Print</button> | <a href="{{p.wa_link}}" target="_blank"><button style="background:#25D366">💬 WhatsApp</button></a></div></div>{% endfor %}
</body></html>
"""

LOGIN = """<!DOCTYPE html><html><body style="font-family:Arial;max-width:400px;margin:100px auto;text-align:center"><h1>❤️ Cardio Login</h1><form method="POST"><select name="user" style="width:100%;padding:10px"><option>Dr. Rahim</option><option>Dr. Karim</option><option>Dr. Sara</option><option>Dr. Tanvir</option></select><br><br><div class="flex"><label>Password</label><input name="pass" type="password" id="passInput" style="width:100%;padding:10px"><input type="checkbox" id="showPass" style="margin-left:5px;"> Show</div><br><br><button style="padding:10px 30px;background:#007bff;color:white;border:none">Login</button></form>{% if err %}<p style="color:red">{{err}}</p>{% endif %}</body></html><script>document.getElementById('showPass').addEventListener('change', function(){ var ipt = document.getElementById('passInput'); ipt.type = this.checked ? 'text' : 'password'; });</script>"""
REPORT = """<!DOCTYPE html><html><head><style>body{font-family:Arial;max-width:800px;margin:auto;padding:20px}table{width:100%;border-collapse:collapse}td,th{border:1px solid #000;padding:8px}@media print{.no-print{display:none}}</style></head><body><h1>📄 Daily Report - {{date}}</h1><p>Doctor: {{user}} | Today: {{total}} | Urgent: {{urgent}} | Done: {{done_count}} | Saved: {{time_saved}} min | Total Visits Ever: {{total_visits}}</p><h3>Doctor-wise</h3><table><tr><th>Doctor</th><th>Patients</th></tr>{% for d,c in doc_count.items() %}<tr><td>{{d}}</td><td>{{c}}</td></tr>{% endfor %}</table><h3>Patients</h3><table><tr><th>Name</th><th>Doctor</th><th>Type</th><th>Plan</th></tr>{% for p in patients %}<tr><td>{{p.name}}</td><td>{{p.doctor}}</td><td>{{p.type}}</td><td>{{p.plan}}</td></tr>{% endfor %}</table><br><div class="no-print"><button onclick="window.print()">🖨️ Print / Save PDF</button> <a href="/">Back</a></div></body></html>"""
ALL = """<!DOCTYPE html><html><head><style>body{font-family:Arial;max-width:900px;margin:auto;padding:20px}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px}</style></head><body><h1>📚 All Patient History - From Database</h1><a href="/">← Back</a><br><br><table><tr><th>Name</th><th>Date</th><th>Doctor</th><th>EF</th><th>Type</th><th>Status</th></tr>{% for p in rows %}<tr><td>{{p.name}} ({{p.phone}})</td><td>{{p.date}} {{p.time}}</td><td>{{p.doctor}}</td><td>{{p.ef}}%</td><td>{{p.type}}</td><td>{{p.status}}</td></tr>{% endfor %}</table></body></html>"""

@app.route("/login", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = USERS.get(username)
        if user and check_password_hash(user["password"], password):
            session["user"] = username
            session["role"] = user["role"]
            return redirect("/")
        return render_template_string(LOGIN, err="Invalid username or password")
    return render_template_string(LOGIN, err="")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
    q=request.args.get("q","").lower()
    c=db(); rows=c.execute("SELECT * FROM patients WHERE status='active' ORDER BY CASE color WHEN 'red' THEN 0 WHEN 'yellow' THEN 1 ELSE 2 END, id DESC").fetchall()
    if q: rows=[r for r in rows if q in r['name'].lower() or q in (r['phone'] or "").lower()]
    total_visits=c.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    done_count=c.execute("SELECT COUNT(*) FROM patients WHERE status='done' AND date=?", (datetime.now().strftime("%d %b %Y"),)).fetchone()[0]
    c.close()
    doc_count={d: sum(1 for r in rows if r['doctor']==d) for d in DOCTORS}
    return render_template_string(HTML, patients=rows, total=len(rows), urgent=sum(1 for r in rows if r['color']=='red'), time_saved=len(rows)*7, done_count=done_count, q=q, doctors=DOCTORS, doc_count=doc_count, least_busy=min(doc_count, key=doc_count.get), user=session['user'], total_visits=total_visits)

@app.route("/add", methods=["POST"])
def add():
    f=request.form; name=f['name'].strip(); age=f['age']; bp=f['bp'] or "N/A"; hr=f['hr'] or "N/A"; ef=f['ef'] or "N/A"; ecg=f['ecg'] or "Not done"; phone=f['phone'] or ""; typ=f['type']; notes=f['notes']; risk=int(f['risk']); doctor=f['doctor']
    c=db(); key=name.lower()
    prev=c.execute("SELECT * FROM history WHERE name_key=? ORDER BY id DESC LIMIT 1", (key,)).fetchone()
    hist_count=c.execute("SELECT COUNT(*) FROM history WHERE name_key=?", (key,)).fetchone()[0]
    last_visit=last_ef=last_plan=ef_change=""
    if prev:
        last_visit=prev['date']; last_ef=prev['ef']; last_plan=prev['plan']
        try:
            diff=int(ef)-int(last_ef); ef_change=f"📈 EF Improved +{diff}%" if diff>0 else (f"📉 EF Dropped {diff}%" if diff<0 else "➡️ EF Same")
        except: pass
    try: ef_v=int(ef); bp_s=int(bp.split('/')[0]) if '/' in bp else 120; hr_v=int(hr)
    except: ef_v=60; bp_s=120; hr_v=80
    s=""
    if "ST elevation" in ecg or "STEMI" in ecg: s+="STEMI EMERGENCY. "
    elif "AF" in ecg: s+="Atrial Fibrillation. "
    elif "Normal" in ecg: s+="ECG Normal. "
    else: s+=f"ECG: {ecg}. "
    if ef_v<35: s+="Severe LV dysfunction. "
    elif ef_v<50: s+="Mild-Mod LV dysfunction. "
    else: s+="Preserved EF. "
    if bp_s>=140: s+="HIGH BP. "
    if hr_v>100: s+="Tachycardia. "
    if risk==3 or "STEMI" in ecg: risk=3
    if risk==3: color,action,plan,fup="red","See NOW","Admit/CCU, Troponin STAT","Tomorrow"
    elif risk==2: color,action,plan,fup="yellow","See Today","Echo+ECG, Meds adjust","2 Weeks"
    else: color,action,plan,fup="green","Nurse/Junior","Continue meds","1 Month"
    discharge=f"{name}, {typ}. {s} Plan: {plan}. Follow-up: {fup}."
    wa_text=f"Hello {name}, Cardio Report: {s} Plan: {plan}. Follow-up: {fup}. Doctor: {doctor}."
    clean=''.join(filter(str.isdigit, phone))
    if clean.startswith("0"): clean="880"+clean[1:]
    elif clean and not clean.startswith("880"): clean="880"+clean
    wa_link=f"https://wa.me/{clean}?text={urllib.parse.quote(wa_text)}" if clean!="880" and clean else "#"
    date_now=datetime.now().strftime("%d %b %Y"); time_now=datetime.now().strftime("%I:%M %p")
    c.execute("INSERT INTO patients(name,age,phone,bp,hr,ef,ecg,type,doctor,color,action,plan,auto_note,followup,discharge,time,date,history_count,last_visit,last_ef,last_plan,ef_change,wa_link) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (name,age,phone,bp,hr,ef,ecg,typ,doctor,color,action,plan,s+f"Symptoms: {notes}",fup,discharge,time_now,date_now,hist_count,last_visit,last_ef,last_plan,ef_change,wa_link))
    c.execute("INSERT INTO history(name_key,date,ef,plan,type) VALUES(?,?,?, ?,?)", (key, date_now+" "+time_now, ef, plan, typ))
    c.commit(); c.close()
    return redirect("/")

@app.route("/done/<int:pid>")
def done(pid):
    c=db(); c.execute("UPDATE patients SET status='done' WHERE id=?", (pid,)); c.commit(); c.close(); return redirect("/")
@app.route("/all")
def all_hist():
    if 'user' not in session: return redirect("/login")
    c=db(); rows=c.execute("SELECT * FROM patients ORDER BY id DESC LIMIT 200").fetchall(); c.close()
    return render_template_string(ALL, rows=rows)
@app.route("/export")
def export():
    c=db(); rows=c.execute("SELECT * FROM patients WHERE status='active'").fetchall(); c.close()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Name","Doctor","Phone","BP","HR","EF","ECG","Type","Summary","Plan","Visit No","Date"])
    for p in rows: w.writerow([p['name'],p['doctor'],p['phone'],p['bp'],p['hr'],p['ef'],p['ecg'],p['type'],p['auto_note'],p['plan'],p['history_count']+1,p['date']])
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=cardio_daily.csv"})
@app.route("/report")
def report():
    if 'user' not in session: return redirect("/login")
    c=db(); rows=c.execute("SELECT * FROM patients WHERE status='active'").fetchall(); total_visits=c.execute("SELECT COUNT(*) FROM history").fetchone()[0]; done_count=c.execute("SELECT COUNT(*) FROM patients WHERE status='done' AND date=?", (datetime.now().strftime("%d %b %Y"),)).fetchone()[0]; c.close()
    doc_count={d: sum(1 for r in rows if r['doctor']==d) for d in DOCTORS}
    return render_template_string(REPORT, date=datetime.now().strftime("%d %b %Y"), patients=rows, total=len(rows), urgent=sum(1 for r in rows if r['color']=='red'), done_count=done_count, time_saved=len(rows)*7, doc_count=doc_count, user=session['user'], total_visits=total_visits)

CALCULATORS = """<!DOCTYPE html><html><head><title>Cardio Calculators</title>
<style>body{font-family:Arial;max-width:800px;margin:auto;padding:20px;background:#f4f7fa}
.card{background:white;padding:15px;border-radius:10px;margin:10px 0;box-shadow:0 2px 5px #ddd}
@media print{.no-print{display:none!important}.card{box-shadow:none;border:1px solid #000}}}
</style></head><body><div class="no-print" style="display:flex;justify-content:space-between;"><b>Cardio Calculators</b><a href="/"><button style="background:#6c7575;">Back</button></a><a href="javascript:window.print()" style="background:#28a745;margin-left:10px;">Print</button></a></div>
<h2>QT Corrected (QTc) Calculator</h2>
<form method="post">
  <div class="flex">
    <div><label>QT interval (ms)</label><input name="qt" type="number" step="0.1" required></div>
    <div><label>RR interval (ms)</label><input name="rr" type="number" step="0.1" required></div>
  </div>
  <button type="submit">Calculate QTc</button>
</form>
{% if result %}<div class="card{% if 'Prolonged' in result %} red{% else %} green{% endif %}" style="margin-top:20px;">{{ result }}</div>{% endif %}
<p><small>Developed by Dr. Sumaiya Mohammad, SMRR Team, Bangladesh</small></p></body></html>"""
@app.route("/calculators", methods=["GET", "POST"])
def calculators():
    if 'user' not in session: return redirect("/login")
    result = None
    if request.method == "POST":
        try:
            qt = float(request.form["qt"])
            rr = float(request.form["rr"])
            qtc = qt / math.sqrt(rr/1000)
            if qtc > 450:
                result = f"QTc = {qtc:.1f} ms (Prolonged)"
            else:
                result = f"QTc = {qtc:.1f} ms (Normal)"
        except Exception as e:
            result = "Invalid input"
    return render_template_string(CALCULATORS, result=result)
@app.route("/risk", methods=["GET", "POST"])
def risk():
    result = None
    if request.method == "POST":
        try:
            age = float(request.form["age"])
            sex = request.form["sex"]
            total_chol = float(request.form["total_chol"])
            hdl = float(request.form["hdl"])
            sbp = float(request.form["sbp"])
            smoking = request.form.get("smoking") == "on"
            diabetes = request.form.get("diabetes") == "on"
            result = compute_ascvd_risk(age, sex, total_chol, hdl, sbp, smoking, diabetes)
        except Exception as e:
            result = "Invalid input"
    form = """
    <h2>10‑Year ASCVD Risk Calculator</h2>
    <form method="post" style="max-width:500px;">
      <div class="flex"><label>Age (years)</label><input name="age" type="number" step="1" required></div>
      <div class="flex">
        <label>Sex</label>
        <select name="sex">
          <option>Male</option><option>Female</option>
        </select>
      </div>
      <div class="flex"><label>Total Cholesterol (mg/dL)</label><input name="total_chol" type="number" step="1" required></div>
      <div class="flex"><label>HDL (mg/dL)</label><input name="hdl" type="number" step="1" required></div>
      <div class="flex"><label>Systolic BP (mmHg)</label><input name="sbp" type="number" step="1" required></div>
      <div class="flex"><label>Smoking</label><input type="checkbox" name="smoking" {% if smoking else %}disabled{% endif %}> Yes</div>
      <div class="flex"><label>Diabetes</label><input type="checkbox" name="diabetes" {% if diabetes else %}disabled{% endif %}> Yes</div>
      <button type="submit">Calculate Risk</button>
    </form>
    {% if result %}<div class="card red" style="margin-top:20px;">{{ result }}</div>{% endif %}
    <p><small>Developed by Dr. Sumaiya Mohammad, SMRR Team, Bangladesh</small></p>
    """
    return form

@app.route("/dosage", methods=["GET", "POST"])
def dosage():
    result = None
    if request.method == "POST":
        try:
            medication = request.form["medication"]
            weight = float(request.form["weight"])
            result = compute_dosage(medication, weight)
        except Exception as e:
            result = "Invalid input"
    form = """
    <h2>Medication Dosage Calculator</h2>
    <form method="post" style="max-width:500px;">
      <div class="flex"><label>Medication</label>
        <select name="medication">
          <option>Metoprolol</option><option>Lisinopril</option><option>Atorvastatin</option><option>Aspirin</option>
        </select></div>
      <div class="flex"><label>Weight (kg)</label><input name="weight" type="number" step="0.1" required></div>
      <button type="submit">Get Dose Guidance</button>
    </form>
    {% if result %}<div class="card green" style="margin-top:20px;">{{ result }}</div>{% endif %}
    <p><small>Developed by Dr. Sumaiya Mohammad, SMRR Team, Bangladesh</small></p>
    """
    return form

@app.route("/ecg", methods=["GET", "POST"])
def ecg():
    result = None
    if request.method == "POST":
        try:
            hr = float(request.form["hr"])
            pr = float(request.form["pr"])
            qrs = float(request.form["qrs"])
            qt = float(request.form["qt"])
            sex = request.form["sex"]
            result = interpret_ecg(hr, pr, qrs, qt, sex)
        except Exception as e:
            result = "Invalid input"
    form = """
    <h2>ECG Interpretation Tool</h2>
    <form method="post" style="max-width:600px;">
      <div class="flex"><label>Heart Rate (bpm)</label><input name="hr" type="number" step="1" required></div>
      <div class="flex"><label>PR interval (ms)</label><input name="pr" type="number" step="0.1" required></div>
      <div class="flex"><label>QRS duration (ms)</label><input name="qrs" type="number" step="0.1" required></div>
      <div class="flex"><label>QT interval (ms)</label><input name="qt" type="number" step="0.1" required></div>
      <div class="flex"><label>Sex</label>
        <select name="sex">
          <option>Male</option><option>Female</option>
        </select></div>
      <button type="submit">Interpret ECG</button>
    </form>
    {% if result %}<div class="card yellow" style="margin-top:20px;">{{ result }}</div>{% endif %}
    <p><small>Developed by Dr. Sumaiya Mohammad, SMRR Team, Bangladesh</small></p>
    """
    return form

@app.route("/patients")
def patients():
    patients = get_patients()
    table_rows = ""
    for p in patients:
        table_rows += f"<tr><td>{p['name']}</td><td>{p['age']}</td><td>{p['doctor']}</td><td>{p['bp']}</td><td>{p['hr']}</td><td>{p['ef']}</td><td>{p['status']}</td><td>{p['date']}</td></tr>"
    form = f"""
    <h2>Patient Management System</h2>
    <p>Active patients ({{patients|length}}):</p>
    <table style="width:100%; border-collapse:collapse; margin-top:10px;">
      <tr style="background:#f4f7fa;">
        <th style="padding:8px;border:1px solid #ddd;">Name</th>
        <th style="padding:8px;border:1px solid #ddd;">Age</th>
        <th style="padding:8px;border:1px solid #ddd;">Doctor</th>
        <th style="padding:8px;border:1px solid #ddd;">BP</th>
        <th style="padding:8px;border:1px solid #ddd;">HR</th>
        <th style="padding:8px;border:1px solid #ddd;">EF</th>
        <th style="padding:8px;border:1px solid #ddd;">Status</th>
        <th style="padding:8px;border:1px solid #ddd;">Last Visit</th>
      </tr>
      {table_rows}
    </table>
    <p><small>Developed by Dr. Sumaiya Mohammad, SMRR Team, Bangladesh</small></p>
    """
    return form

@app.route("/workflow", methods=["GET", "POST"])
def workflow():
    # Initialize tasks list in session if not present
    if "workflow_tasks" not in session:
        session["workflow_tasks"] = []
    if request.method == "POST":
        task = {
            "text": request.form["task"],
            "urgent": request.form.get("urgent") == "on",
            "important": request.form.get("important") == "on"
        }
        session["workflow_tasks"].append(task)
    # Build 2x2 matrix quadrants
    do_now = [t for t in session["workflow_tasks"] if t["urgent"] and t["important"]]
    delegate = [t for t in session["workflow_tasks"] if t["urgent"] and not t["important"]]
    schedule = [t for t in session["workflow_tasks"] if not t["urgent"] and t["important"]]
    delete = [t for t in session["workflow_tasks"] if not t["urgent"] and not t["important"]]
    table_rows = ""
    for quadrant_name, quadrant_tasks in [
        ("Do Now (Urgent+Important)", do_now),
        ("Delegate (Urgent+Not Important)", delegate),
        ("Schedule (Not Urgent+Important)", schedule),
        ("Delete (Not Urgent+Not Important)", delete)
    ]:
        row = f"<tr><td style='width:25%;vertical-align:top;background:#e8f4fd;padding:8px;border:1px solid #ddd;'><b>{quadrant_name}</b></td><td style='vertical-align:top;padding:8px;border:1px solid #ddd;'>"
        if quadrant_tasks:
            for t in quadrant_tasks:
                row += f"<div style='margin-bottom:4px;background:#fff;padding:4px;border-radius:4px;'>{t['text']} <span style='float:right;color:gray;font-size:0.8em;'>(U:{t['urgent']} I:{t['important']})</span></div>"
        else:
            row += "No tasks"
        row += "</td></tr>"
        table_rows += row
    form = """
    <h2>Workflow Optimization (Eisenhower Matrix)</h2>
    <form method="post" style="max-width:600px;margin-bottom:20px;">
      <div class="flex"><label>Task description</label><input name="task" required></div>
      <div class="flex">
        <label>Urgent?</label><input type="checkbox" name="urgent" {% if request.method == 'POST' and any(t['urgent'] for t in session.get('workflow_tasks',[])) %}checked{% endif %}>>
        <label>Important?</label><input type="checkbox" name="important" {% if request.method == 'POST' and any(t['important'] for t in session.get('workflow_tasks',[])) %}checked{% endif %}>>
      </div>
      <button type="submit">Add Task</button>
    </form>
    <h3>Eisenhower Matrix</h3>
    <table style="width:100%; border-collapse:collapse; margin-top:10px;">
      {table_rows}
    </table>
    <p><small>Developed by Dr. Sumaiya Mohammad, SMRR Team, Bangladesh</small></p>
    """
    return form

def compute_ascvd_risk(age, sex, total_chol, hdl, sbp, smoking, diabetes):
    """Calculate 10-year ASCVD risk using ACC/AHA Pooled Cohort Equations."""
    import math
    if sex.lower().startswith('m'):
        intercept = -29.939
        ln_coef = 0.1515
        age_coef = 0.0736
        sbp_coef = 0.0903
        smoker_coef = 0.644
        diabetes_coef = 0.385
        hdl_coef = -0.228
    else:
        intercept = -25.668
        ln_coef = 0.125
        age_coef = 0.0513
        sbp_coef = 0.097
        smoker_coef = 0.512
        diabetes_coef = 0.866
        hdl_coef = -0.324
    ln_risk = (intercept
               + age_coef * age
               + ln_coef * math.log(total_chol)
               + sbp_coef * sbp
               + smoker_coef * (1 if smoking else 0)
               + diabetes_coef * (1 if diabetes else 0)
               + hdl_coef * hdl)
    risk = 1 - math.exp(ln_risk)
    risk = max(0.0, min(1.0, risk))
    return f"{risk*100:.1f}%"

def compute_dosage(medication, weight):
    """Provide cardiac medication dosing guidance based on weight."""
    if medication.lower() == "metoprolol":
        if weight >= 70:
            return "Starting dose: 50 mg PO BID; Max: 400 mg/day"
        else:
            return "Starting dose: 25 mg PO BID; Max: 400 mg/day"
    elif medication.lower() == "lisinopril":
        return "Starting dose: 10 mg PO daily; Max: 40 mg/day"
    elif medication.lower() == "atorvastatin":
        return "Starting dose: 10‑20 mg PO daily; Max: 80 mg/day"
    elif medication.lower() == "aspirin":
        return "Dose: 81 mg PO daily (primary prevention) or 325 mg PO daily (secondary prevention)"
    else:
        return "Medication not recognized"

def interpret_ecg(hr, pr, qrs, qt, sex):
    """Basic ECG interpretation with normal ranges and possible findings."""
    rr = 60000 / hr
    qtc_calc = qt / math.sqrt(rr / 1000)
    findings = []
    if hr < 60:
        findings.append(f"Heart rate {hr} bpm: Bradycardia")
    elif hr > 100:
        findings.append(f"Heart rate {hr} bpm: Tachycardia")
    else:
        findings.append(f"Heart rate {hr} bpm: Normal")
    if pr < 120:
        findings.append(f"PR interval {pr} ms: Short")
    elif pr > 200:
        findings.append(f"PR interval {pr} ms: First-degree AV block")
    else:
        findings.append(f"PR interval {pr} ms: Normal")
    if qrs > 120:
        findings.append(f"QRS duration {qrs} ms: Wide (bundle branch block or ventricular rhythm)")
    else:
        findings.append(f"QRS duration {qrs} ms: Normal")
    if sex.lower().startswith('f'):
        if qtc_calc > 470:
            findings.append(f"QTc (calculated) {qtc_calc:.1f} ms: Prolonged (female)")
        else:
            findings.append(f"QTc (calculated) {qtc_calc:.1f} ms: Normal")
    else:
        if qtc_calc > 460:
            findings.append(f"QTc (calculated) {qtc_calc:.1f} ms: Prolonged (male)")
        else:
            findings.append(f"QTc (calculated) {qtc_calc:.1f} ms: Normal")
    return "; ".join(findings)

def get_patients():
    """Fetch all active patients from the database."""
    c = db()
    rows = c.execute("SELECT id, name, age, doctor, bp, hr, ef, status, date FROM patients WHERE status='active'").fetchall()
    c.close()
    return [dict(r) for r in rows]

if __name__=="__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
@app.route("/changepassword", methods=["GET", "POST"])
def changepassword():
    if 'user' not in session:
        return redirect("/login")
    if request.method == "POST":
        current = request.form['current']
        new = request.form['new']
        confirm = request.form['confirm']
        c = db()
        row = c.execute("SELECT password_hash FROM users WHERE username=?", (session['user'],)).fetchone()
        c.close()
        if not row or not check_password_hash(row[0], current):
            return render_template_string(LOGIN, err="Current password incorrect")
        if new != confirm:
            return render_template_string(LOGIN, err="New passwords do not match")
        c = db()
        c.execute("UPDATE users SET password_hash=? WHERE username=?", (generate_password_hash(new), session['user']))
        c.commit()
        c.close()
        return render_template_string(LOGIN, err="Password changed successfully")
    return render_template_string("""<!DOCTYPE html><html><body style="font-family:Arial;margin:100px auto;text-align:center"><h2>Change Password</h2><form method="post"><div class="flex"><label>Current password</label><input name="current" type="password" required></div><div class="flex"><label>New password</label><input name="new" type="password" required></div><div class="flex"><label>Confirm</label><input name="confirm" type="password" required></div><br><button style="padding:10px 30px;background:#28a745;color:white;border:none">Update</button></form></body></html>""")

@app.route("/assistant", methods=["GET", "POST"])
def assistant():
    if 'user' in session and session.get('assistant'):
        return redirect("/")
    if request.method == "POST":
        password = request.form['pass']
        c = db()
        row = c.execute("SELECT password_hash FROM users WHERE username='assistant'").fetchone()
        c.close()
        if row and check_password_hash(row[0], password):
            session['assistant'] = True
            return redirect("/")
        else:
            return render_template_string(LOGIN, err="Invalid assistant password")
    return render_template_string("""<!DOCTYPE html><html><body style="font-family:Arial;margin:100px auto;text-align:center"><h2>Assistant Login</h2><form method="post"><div class="flex"><label>Password</label><input name="pass" type="password" required></div><br><button style="padding:10px 30px;background:#28a745;color:white;border:none">Login</button></form></body></html>""")
app.run(host="0.0.0.0", port=5001, debug=True)