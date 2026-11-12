# ============================================
# CARDIO WORK REDUCER - COMPLETE CODE
# PART 1 of 3 - Login + DB + Home + Patients
# Developed by Dr. Sumaiya Mohammad, SMRR Team
# ============================================
from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import datetime
import csv, io, urllib.parse, sqlite3, os, math
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cardio123"
DB = "cardio.db"

DOCTORS = ["Dr. Rahim", "Dr. Karim", "Dr. Sara", "Dr. Tanvir"]

# Sobar password 1234
USERS = {
    "Dr. Rahim": {"password": generate_password_hash("1234"), "role": "doctor"},
    "Dr. Karim": {"password": generate_password_hash("1234"), "role": "doctor"},
    "Dr. Sara": {"password": generate_password_hash("1234"), "role": "doctor"},
    "Dr. Tanvir": {"password": generate_password_hash("1234"), "role": "doctor"},
    "assistant": {"password": generate_password_hash("1234"), "role": "assistant"},
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
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT)""")
    cur = c.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        c.execute("INSERT INTO users(username,password_hash) VALUES(?,?)", ('admin', generate_password_hash('1234')))
    c.execute("""CREATE TABLE IF NOT EXISTS prescriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, medicine TEXT, dosage TEXT,
        frequency TEXT, doctor TEXT, date TEXT)""")
    c.commit()
    c.close()
init()

# ============ HTML TEMPLATES ============
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
<div class="no-print" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:5px">
  <b>{{user}} | Total Visits: {{total_visits}}</b>
  <div>
  <a href="/all"><button style="background:orange">All In One</button></a>
  <a href="/qtc"><button style="background:#28a745;">QT Calculator</button></a>
  <a href="/risk"><button style="background:#fd7e14;">Risk</button></a>
  <a href="/dosage"><button style="background:#6c5ce7;">Dosage</button></a>
  <a href="/ecg"><button style="background:#00c9a7;">ECG</button></a>
  <a href="/patients"><button style="background:#6c7575;">Patients</button></a>
  <a href="/workflow"><button style="background:#e83e8c;">Workflow</button></a>
  <a href="/prescriptions"><button style="background:#28a745;">Prescriptions</button></a>
  <a href="/smart-workload"><button style="background:#17a2b8;">Smart Workload</button></a>
  <a href="/burnout-meter"><button style="background:#dc3545;">Burnout</button></a>
  <a href="/sos-mode"><button style="background:#6c7575;">SOS</button></a>
  <a href="/changepassword"><button style="background:#ffc107;color:black;">Change Pass</button></a>
  <a href="/logout"><button style="background:#dc3545;">Logout</button></a>
  </div>
</div>
<h1>❤️ Cardio Workload - With Database</h1>
<div class="top"><div class="box"><h2>{{total}}</h2>Today Active</div><div class="box"><h2 style="color:red">{{urgent}}</h2>Urgent</div><div class="box"><h2>{{time_saved}} min</h2>Saved</div><div class="box"><h2>{{done_count}}</h2>Done Today</div></div>
<div class="card no-print"><h3>Doctor-wise</h3><div class="flex">{% for d,c in doc_count.items() %}<div class="box"><b>{{d}}</b><h2>{{c}}</h2>{{"🔴 Overloaded" if c>=5 else "🟢 Normal"}}</div>{% endfor %}</div><p><b>Least Busy:</b> {{least_busy}}</p></div>
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
<a href="/export"><button style="background:green">📥 CSV</button></a><a href="/report"><button style="background:purple">📄 Daily Report</button></a><a href="/history"><button style="background:orange">📚 All History</button></a></div>
<h3>Today's Queue ({{patients|length}})</h3>
{% for p in patients %}<div class="card {{p.color}}"><b>{{p.name}} ({{p.age}})</b> - {{p.type}} | {{p.time}} | {{p.doctor}} | {{p.phone}}
{% if p.history_count>0 %}<div class="hist">📚 History: {{p.history_count}} no. visit | Ager: {{p.last_visit}} | Ager EF: {{p.last_ef}} | {{p.ef_change}}</div>{% else %}<div class="hist">🆕 New Patient</div>{% endif %}
<p>BP: {{p.bp}} | HR: {{p.hr}} | EF: {{p.ef}}% | ECG: {{p.ecg}}</p>
<p><b>Summary:</b> {{p.auto_note}}</p><p><b>Plan:</b> {{p.plan}}</p><p><b>Follow-up:</b> {{p.followup}}</p><p><b>Discharge:</b> {{p.discharge}}</p>
<div class="no-print"><a href="/done/{{p.id}}">✅ Done</a> | <button onclick="window.print()">🖨️ Print</button> | <a href="{{p.wa_link}}" target="_blank"><button style="background:#25D366">💬 WhatsApp</button></a></div></div>{% endfor %}
</body></html>
"""

LOGIN = """<!DOCTYPE html><html><body style="font-family:Arial;max-width:400px;margin:100px auto;text-align:center"><h1>❤️ Cardio Login</h1><form method="POST"><select name="user" style="width:100%;padding:10px"><option>Dr. Rahim</option><option>Dr. Karim</option><option>Dr. Sara</option><option>Dr. Tanvir</option><option>assistant</option></select><br><br><input name="pass" type="password" placeholder="Password = 1234" style="width:100%;padding:10px"><br><br><button style="padding:10px 30px;background:#007bff;color:white;border:none">Login</button></form>{% if err %}<p style="color:red">{{err}}</p>{% endif %}</body></html>"""

REPORT = """<!DOCTYPE html><html><head><style>body{font-family:Arial;max-width:800px;margin:auto;padding:20px}table{width:100%;border-collapse:collapse}td,th{border:1px solid #000;padding:8px}@media print{.no-print{display:none}}</style></head><body><h1>📄 Daily Report - {{date}}</h1><p>Doctor: {{user}} | Today: {{total}} | Urgent: {{urgent}} | Done: {{done_count}} | Saved: {{time_saved}} min | Total Visits Ever: {{total_visits}}</p><h3>Doctor-wise</h3><table><tr><th>Doctor</th><th>Patients</th></tr>{% for d,c in doc_count.items() %}<tr><td>{{d}}</td><td>{{c}}</td></tr>{% endfor %}</table><h3>Patients</h3><table><tr><th>Name</th><th>Doctor</th><th>Type</th><th>Plan</th></tr>{% for p in patients %}<tr><td>{{p.name}}</td><td>{{p.doctor}}</td><td>{{p.type}}</td><td>{{p.plan}}</td></tr>{% endfor %}</table><br><div class="no-print"><button onclick="window.print()">🖨️ Print / Save PDF</button> <a href="/">Back</a></div></body></html>"""

ALL = """<!DOCTYPE html><html><head><style>body{font-family:Arial;max-width:900px;margin:auto;padding:20px}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px}</style></head><body><h1>📚 All Patient History - From Database</h1><a href="/">← Back</a><br><br><table><tr><th>Name</th><th>Date</th><th>Doctor</th><th>EF</th><th>Type</th><th>Status</th></tr>{% for p in rows %}<tr><td>{{p.name}} ({{p.phone}})</td><td>{{p.date}} {{p.time}}</td><td>{{p.doctor}}</td><td>{{p.ef}}%</td><td>{{p.type}}</td><td>{{p.status}}</td></tr>{% endfor %}</table></body></html>"""

# ============ LOGIN / LOGOUT / HOME ============
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("user", "").strip()
        password = request.form.get("pass", "")
        user = USERS.get(username)
        if user and check_password_hash(user["password"], password):
            session["user"] = username
            session["role"] = user["role"]
            return redirect("/")
        return render_template_string(LOGIN, err="Invalid username or password - Password 1234")
    return render_template_string(LOGIN, err="")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def home():
    if 'user' not in session: return redirect("/login")
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
    if 'user' not in session: return redirect("/login")
    f=request.form; name=f['name'].strip(); age=f['age']; bp=f['bp'] or "N/A"; hr=f['hr'] or "N/A"; ef=f['ef'] or "N/A"; ecg=f['ecg'] or "Not done"; phone=f['phone'] or ""; typ=f['type']; notes=f['notes']; risk=int(f['risk']); doctor=f['doctor']
    c=db(); key=name.lower()
    prev=c.execute("SELECT * FROM history WHERE name_key=? ORDER BY id DESC LIMIT 1", (key,)).fetchone()
    hist_count=c.execute("SELECT COUNT(*) FROM history WHERE name_key=?", (key,)).fetchone()[0]
    last_visit=last_ef=last_plan=ef_change=""
    if prev:
        last_visit=prev['date']; last_ef=prev['ef']; last_plan=prev['plan']
        try:
            diff=int(ef)-int(last_ef); ef_change=f"EF Improved +{diff}%" if diff>0 else (f"EF Dropped {diff}%" if diff<0 else "EF Same")
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

@app.route("/history")
def all_hist():
    if 'user' not in session: return redirect("/login")
    c=db(); rows=c.execute("SELECT * FROM patients ORDER BY id DESC LIMIT 200").fetchall(); c.close()
    return render_template_string(ALL, rows=rows)

@app.route("/export")
def export():
    if 'user' not in session: return redirect("/login")
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
.card{background:white;padding:15px;border-radius:10px;margin:10px 0}.flex{display:flex;gap:10px}.flex>*{flex:1}input{width:100%;padding:8px;margin:5px 0}button{padding:9px 16px;background:#007bff;color:white;border:none;border-radius:5px}
</style></head><body><a href="/">Back</a><h2>QT Corrected (QTc) Calculator</h2>
<form method="post"><div class="flex"><div><label>QT interval (ms)</label><input name="qt" type="number" step="0.1" required></div><div><label>RR interval (ms)</label><input name="rr" type="number" step="0.1" required></div></div><button type="submit">Calculate QTc</button></form>
{% if result %}<div class="card">{{ result }}</div>{% endif %}
<p><small>Developed by Dr. Sumaiya Mohammad, SMRR Team, Bangladesh</small></p></body></html>"""

@app.route("/calculators", methods=["GET", "POST"])
def calculators():
    if 'user' not in session: return redirect("/login")
    result = None
    if request.method == "POST":
        try:
            qt = float(request.form["qt"]); rr = float(request.form["rr"])
            qtc = qt / math.sqrt(rr/1000)
            result = f"QTc = {qtc:.1f} ms (Prolonged)" if qtc > 450 else f"QTc = {qtc:.1f} ms (Normal)"
        except: result = "Invalid input"
    return render_template_string(CALCULATORS, result=result)

@app.route("/qtc", methods=["GET", "POST"])
def qtc():
    return redirect("/calculators")

@app.route("/risk", methods=["GET", "POST"])
def risk():
    if 'user' not in session: return redirect("/login")
    result = None
    if request.method == "POST":
        try:
            age = float(request.form["age"]); sex = request.form["sex"]; total_chol = float(request.form["total_chol"]); hdl = float(request.form["hdl"]); sbp = float(request.form["sbp"]); smoking = request.form.get("smoking") == "on"; diabetes = request.form.get("diabetes") == "on"
            result = compute_ascvd_risk(age, sex, total_chol, hdl, sbp, smoking, diabetes)
        except: result = "Invalid input"
    form = """<a href="/">Back</a><h2>10-Year ASCVD Risk Calculator</h2><form method="post" style="max-width:500px;"><label>Age</label><input name="age" type="number" required><label>Sex</label><select name="sex"><option>Male</option><option>Female</option></select><label>Total Cholesterol</label><input name="total_chol" type="number" required><label>HDL</label><input name="hdl" type="number" required><label>Systolic BP</label><input name="sbp" type="number" required><label><input type="checkbox" name="smoking"> Smoking</label><br><label><input type="checkbox" name="diabetes"> Diabetes</label><br><br><button type="submit">Calculate Risk</button></form>{% if result %}<div style="margin-top:20px;background:#fff3cd;padding:10px;">{{ result }}</div>{% endif %}"""
    return render_template_string(form, result=result)

@app.route("/dosage", methods=["GET", "POST"])
def dosage():
    if 'user' not in session: return redirect("/login")
    result = None
    if request.method == "POST":
        try: result = compute_dosage(request.form["medication"], float(request.form["weight"]))
        except: result = "Invalid input"
    form = """<a href="/">Back</a><h2>Medication Dosage Calculator</h2><form method="post" style="max-width:500px;"><label>Medication</label><select name="medication"><option>Metoprolol</option><option>Lisinopril</option><option>Atorvastatin</option><option>Aspirin</option></select><label>Weight (kg)</label><input name="weight" type="number" step="0.1" required><button type="submit">Get Dose Guidance</button></form>{% if result %}<div style="margin-top:20px;background:#d4edda;padding:10px;">{{ result }}</div>{% endif %}"""
    return render_template_string(form, result=result)

@app.route("/ecg", methods=["GET", "POST"])
def ecg():
    if 'user' not in session: return redirect("/login")
    result = None
    if request.method == "POST":
        try: result = interpret_ecg(float(request.form["hr"]), float(request.form["pr"]), float(request.form["qrs"]), float(request.form["qt"]), request.form["sex"])
        except: result = "Invalid input"
    form = """<a href="/">Back</a><h2>ECG Interpretation Tool</h2><form method="post" style="max-width:600px;"><label>Heart Rate (bpm)</label><input name="hr" type="number" required><label>PR interval (ms)</label><input name="pr" type="number" step="0.1" required><label>QRS duration (ms)</label><input name="qrs" type="number" step="0.1" required><label>QT interval (ms)</label><input name="qt" type="number" step="0.1" required><label>Sex</label><select name="sex"><option>Male</option><option>Female</option></select><button type="submit">Interpret ECG</button></form>{% if result %}<div style="margin-top:20px;background:#fff3cd;padding:10px;">{{ result }}</div>{% endif %}"""
    return render_template_string(form, result=result)

@app.route("/patients")
def patients():
    if 'user' not in session: return redirect("/login")
    patients_list = get_patients()
    table_rows = ""
    for p in patients_list:
        table_rows += f"<tr><td>{p['name']}</td><td>{p['age']}</td><td>{p['doctor']}</td><td>{p['bp']}</td><td>{p['hr']}</td><td>{p['ef']}</td><td>{p['status']}</td><td>{p['date']}</td></tr>"
    form = f"""<a href="/">Back</a><h2>Patient Management System</h2><p>Active patients {len(patients_list)}:</p><table style="width:100%; border-collapse:collapse;background:white;"><tr><th>Name</th><th>Age</th><th>Doctor</th><th>BP</th><th>HR</th><th>EF</th><th>Status</th><th>Last Visit</th></tr>{table_rows}</table>"""
    return form

# ============ WORKFLOW - DOCTOR TASK OPTIONS ============
@app.route("/workflow", methods=["GET", "POST"])
def workflow():
    if 'user' not in session: return redirect("/login")
    if "workflow_tasks" not in session: session["workflow_tasks"] = []
    if request.method == "POST":
        preset = request.form.get("preset", "")
        custom = request.form.get("task", "").strip()
        task_text = preset if preset and preset != "Custom" else custom
        if not task_text: task_text = "Untitled Task"
        task = {
            "text": task_text,
            "doctor": request.form.get("doctor", session['user']),
            "category": request.form.get("category", "General"),
            "time": request.form.get("time", "Today"),
            "urgent": request.form.get("urgent") == "on",
            "important": request.form.get("important") == "on",
            "notes": request.form.get("notes", "")
        }
        session["workflow_tasks"].append(task)
        session.modified = True
        return redirect("/workflow")
    if request.args.get("clear") == "1":
        session["workflow_tasks"] = []
        session.modified = True
        return redirect("/workflow")

    do_now = [t for t in session["workflow_tasks"] if t["urgent"] and t["important"]]
    delegate = [t for t in session["workflow_tasks"] if t["urgent"] and not t["important"]]
    schedule = [t for t in session["workflow_tasks"] if not t["urgent"] and t["important"]]
    delete = [t for t in session["workflow_tasks"] if not t["urgent"] and not t["important"]]
    table_rows = ""
    for quadrant_name, quadrant_tasks, color in [
        ("Do Now (Urgent+Important)", do_now, "#ffcccc"),
        ("Delegate (Urgent+Not Important)", delegate, "#ffe0b2"),
        ("Schedule (Not Urgent+Important)", schedule, "#c8e6c9"),
        ("Delete (Not Urgent+Not Important)", delete, "#eeeeee")
    ]:
        row = f"<tr><td style='width:25%;vertical-align:top;background:{color};padding:10px;border:1px solid #ddd;'><b>{quadrant_name}</b><br><small>{len(quadrant_tasks)} tasks</small></td><td style='vertical-align:top;padding:10px;border:1px solid #ddd;'>"
        if quadrant_tasks:
            for t in quadrant_tasks:
                row += f"<div style='background:#fff;padding:8px;border-radius:6px;margin-bottom:6px;border-left:4px solid #007bff;'><b>{t['text']}</b><br><small>👨‍⚕️ {t.get('doctor','')} | 📂 {t.get('category','')} | 🕒 {t.get('time','')} | U:{t['urgent']} I:{t['important']}</small><br><i>{t.get('notes','')}</i></div>"
        else: row += "No tasks"
        row += "</td></tr>"
        table_rows += row

    form = """<a href="/">Back</a> <a href="/all">All In One</a>
    <h2>Workflow Optimization (Eisenhower Matrix) - Doctor Tasks</h2>
    <form method="post" style="max-width:700px;background:#fff;padding:15px;border-radius:10px;">
      <label><b>Doctor Task - Select Option:</b></label>
      <select name="preset">
        <option>Ward Round - CCU / Ward</option>
        <option>OPD - New Patient Checkup</option>
        <option>OPD - Follow-up Patient</option>
        <option>Echo Report Review</option>
        <option>ECG Review - Emergency</option>
        <option>Angiogram / Cath Lab</option>
        <option>Post-Stent / Post-CABG Follow-up</option>
        <option>Heart Failure Clinic</option>
        <option>Discharge Summary Write</option>
        <option>Prescription Review & Sign</option>
        <option>Patient Counselling - Diet / Lifestyle</option>
        <option>Emergency - Chest Pain / STEMI</option>
        <option>Referral - Transfer Patient</option>
        <option>Report - Daily Summary</option>
        <option>Custom</option>
      </select>
      <label>Or Write Custom Task:</label><input name="task" placeholder="Ex: Call patient for Echo follow-up">
      <div style="display:flex;gap:10px;">
        <div style="flex:1;"><label>Assign Doctor</label><select name="doctor"><option>Dr. Rahim</option><option>Dr. Karim</option><option>Dr. Sara</option><option>Dr. Tanvir</option></select></div>
        <div style="flex:1;"><label>Category</label><select name="category"><option>Clinical</option><option>Emergency</option><option>OPD</option><option>Report</option><option>Admin</option></select></div>
        <div style="flex:1;"><label>When</label><select name="time"><option>Today</option><option>Tomorrow</option><option>This Week</option><option>Next Week</option></select></div>
      </div>
      <label>Notes / Details:</label><input name="notes" placeholder="Ex: Patient Rahim, EF 30%, need urgent Echo">
      <br><label><input type="checkbox" name="urgent"> Urgent?</label> &nbsp; <label><input type="checkbox" name="important"> Important?</label><br><br>
      <button type="submit" style="padding:10px 20px;background:#007bff;color:white;border:none;border-radius:5px;">Add Task</button>
      <a href="/workflow?clear=1">Clear All</a>
    </form>
    <h3>Eisenhower Matrix - Total: {total} tasks</h3>
    <table style="width:100%; border-collapse:collapse;background:white;">{table_rows}</table>
    <p><small>Tip: Urgent+Important = Do Now. Urgent but not Important = Delegate to Junior / Nurse.</small></p>
    """
    form = form.replace("{table_rows}", table_rows).replace("{total}", str(len(session["workflow_tasks"])))
    return form

# ============ HELPER FUNCTIONS ============
def compute_ascvd_risk(age, sex, total_chol, hdl, sbp, smoking, diabetes):
    if sex.lower().startswith('m'):
        intercept = -29.939; ln_coef = 0.1515; age_coef = 0.0736; sbp_coef = 0.0903; smoker_coef = 0.644; diabetes_coef = 0.385; hdl_coef = -0.228
    else:
        intercept = -25.668; ln_coef = 0.125; age_coef = 0.0513; sbp_coef = 0.097; smoker_coef = 0.512; diabetes_coef = 0.866; hdl_coef = -0.324
    ln_risk = (intercept + age_coef * age + ln_coef * math.log(total_chol) + sbp_coef * sbp + smoker_coef * (1 if smoking else 0) + diabetes_coef * (1 if diabetes else 0) + hdl_coef * hdl)
    risk = 1 - math.exp(ln_risk); risk = max(0.0, min(1.0, risk))
    return f"{risk*100:.1f}%"

def compute_dosage(medication, weight):
    if medication.lower() == "metoprolol": return "Starting dose: 50 mg PO BID; Max: 400 mg/day" if weight >= 70 else "Starting dose: 25 mg PO BID; Max: 400 mg/day"
    elif medication.lower() == "lisinopril": return "Starting dose: 10 mg PO daily; Max: 40 mg/day"
    elif medication.lower() == "atorvastatin": return "Starting dose: 10-20 mg PO daily; Max: 80 mg/day"
    elif medication.lower() == "aspirin": return "Dose: 81 mg PO daily (primary) or 325 mg PO daily (secondary)"
    else: return "Medication not recognized"

def interpret_ecg(hr, pr, qrs, qt, sex):
    rr = 60000 / hr; qtc_calc = qt / math.sqrt(rr / 1000); findings = []
    findings.append(f"Heart rate {hr} bpm: {'Bradycardia' if hr < 60 else 'Tachycardia' if hr > 100 else 'Normal'}")
    findings.append(f"PR interval {pr} ms: {'Short' if pr < 120 else 'First-degree AV block' if pr > 200 else 'Normal'}")
    findings.append(f"QRS duration {qrs} ms: {'Wide' if qrs > 120 else 'Normal'}")
    limit = 470 if sex.lower().startswith('f') else 460
    findings.append(f"QTc {qtc_calc:.1f} ms: {'Prolonged' if qtc_calc > limit else 'Normal'}")
    return "; ".join(findings)

def get_patients():
    c = db(); rows = c.execute("SELECT id, name, age, doctor, bp, hr, ef, status, date FROM patients WHERE status='active'").fetchall(); c.close(); return [dict(r) for r in rows]
# ============================================
# PART 3 of 3 - Prescription + Workload + Burnout + SOS + All In One
# ============================================

@app.route("/changepassword", methods=["GET", "POST"])
def changepassword():
    if 'user' not in session: return redirect("/login")
    if request.method == "POST":
        current = request.form['current']; new = request.form['new']; confirm = request.form['confirm']
        c = db(); row = c.execute("SELECT password_hash FROM users WHERE username=?", (session['user'],)).fetchone(); c.close()
        if not row or not check_password_hash(row[0], current): return render_template_string(LOGIN, err="Current password incorrect")
        if new != confirm: return render_template_string(LOGIN, err="New passwords do not match")
        c = db(); c.execute("UPDATE users SET password_hash=? WHERE username=?", (generate_password_hash(new), session['user'])); c.commit(); c.close()
        return render_template_string(LOGIN, err="Password changed successfully")
    return render_template_string("""<!DOCTYPE html><html><body style="font-family:Arial;margin:100px auto;text-align:center"><h2>Change Password</h2><form method="post"><label>Current password</label><input name="current" type="password" required><br><label>New password</label><input name="new" type="password" required><br><label>Confirm</label><input name="confirm" type="password" required><br><br><button style="padding:10px 30px;background:#28a745;color:white;border:none">Update</button></form></body></html>""")

# ============ PRESCRIPTION - DETAILING ============
@app.route("/prescriptions", methods=["GET", "POST"])
def prescriptions():
    if 'user' not in session: return redirect("/login")
    c = db()
    if request.method == "POST":
        c.execute("INSERT INTO prescriptions(patient_name, medicine, dosage, frequency, doctor, date) VALUES(?,?,?,?,?,?)",
            (request.form.get("patient_name"), f"{request.form.get('medicine')} - {request.form.get('instruction','')}", request.form.get("dosage"), request.form.get("frequency"), request.form.get("doctor", session['user']), datetime.now().strftime("%d %b %Y")))
        c.commit()
    rows = c.execute("SELECT * FROM prescriptions ORDER BY id DESC LIMIT 100").fetchall()
    c.close()
    list_html = ""
    for r in rows:
        list_html += f"<tr><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td><td>{r[6]}</td></tr>"
    return f"""<a href="/">Back</a><h1>📋 Prescriptions - Detailing</h1>
    <form method="post" style="max-width:700px;background:#fff;padding:15px;border-radius:10px;">
      <label>Patient Name</label><input name="patient_name" required placeholder="Ex: Md. Rahim">
      <label>Medicine - Select</label><select name="medicine"><option>Aspirin</option><option>Clopidogrel</option><option>Atorvastatin</option><option>Metoprolol</option><option>Lisinopril</option><option>Amlodipine</option><option>Furosemide</option><option>Spironolactone</option><option>Warfarin</option><option>Isosorbide</option></select>
      <div style="display:flex;gap:10px;"><div style="flex:1;"><label>Dosage</label><select name="dosage"><option>75 mg</option><option>81 mg</option><option>5 mg</option><option>10 mg</option><option>20 mg</option><option>40 mg</option><option>50 mg</option></select></div>
      <div style="flex:1;"><label>Frequency</label><select name="frequency"><option>Once Daily (OD)</option><option>Twice Daily (BD)</option><option>Thrice Daily (TDS)</option><option>At Night (HS)</option><option>After Meal</option><option>Before Meal</option><option>SOS - When Needed</option></select></div></div>
      <label>Doctor</label><select name="doctor"><option>Dr. Rahim</option><option>Dr. Karim</option><option>Dr. Sara</option><option>Dr. Tanvir</option></select>
      <label>Instruction / Detailing</label><input name="instruction" placeholder="Ex: After food, 1 month, Check BP after 7 days, No salt">
      <br><button type="submit" style="padding:10px 20px;background:#28a745;color:white;border:none;">+ Add Prescription</button>
    </form>
    <h3>Recent Prescriptions ({len(rows)})</h3>
    <table style="width:100%;border-collapse:collapse;background:white;"><tr><th>Patient</th><th>Medicine + Instruction</th><th>Dosage</th><th>Frequency</th><th>Doctor</th><th>Date</th></tr>{list_html}</table>
    <p><small>Detailing: Medicine er sathe khabar er niyom, koto din, ki check korte hobe - sob likhe dao.</small></p>
    """

# ============ SMART WORKLOAD ============
@app.route("/smart-workload")
def smart_workload():
    if 'user' not in session: return redirect("/login")
    c = db(); rows = c.execute("SELECT * FROM patients WHERE status='active'").fetchall(); c.close()
    html = "<a href='/'>Back</a><h1>📊 Smart Workload - Doctor-wise</h1><p>Auto calculation from Today's Active Patients</p>"
    for d in DOCTORS:
        lst = [r for r in rows if r['doctor']==d]
        urgent = sum(1 for r in lst if r['color']=='red')
        score = len(lst)*10 + urgent*15
        status = "🔴 OVERLOADED - New patient dio na, Delegate koro" if len(lst)>=5 else "🟡 BUSY - Olpo patient dite paro" if len(lst)>=3 else "🟢 FREE - New patient nite parbe"
        suggestion = "Suggestion: Next patient ke Least Busy doctor ke dao. Urgent gula age dekho." if len(lst)>=5 else "Suggestion: Normal routine continue koro."
        html += f"<div style='background:white;padding:15px;border-radius:10px;margin:10px 0;'><h3>{d} - {len(lst)} Patients | Urgent: {urgent} | Workload Score: {score}/100</h3><p><b>{status}</b></p><p>{suggestion}</p><p>Patients: " + ", ".join([f"{r['name']} ({r['type']})" for r in lst]) + "</p></div>"
    counts = {d: sum(1 for r in rows if r['doctor']==d) for d in DOCTORS}
    least = min(counts, key=counts.get)
    html += f"<div style='background:#d4edda;padding:15px;border-radius:10px;'><b>✅ Recommendation: Next New Patient -> {least} (Sobcheye kom kaj)</b></div>"
    return html

# ============ BURNOUT METER ============
@app.route("/burnout-meter", methods=["GET", "POST"])
def burnout():
    if 'user' not in session: return redirect("/login")
    result = ""
    if request.method == "POST":
        try:
            hours = int(request.form.get("hours", 8))
            patients = int(request.form.get("patients", 10))
            sleep = int(request.form.get("sleep", 7))
            stress = int(request.form.get("stress", 5))
            score = (hours-8)*5 + (patients-10)*2 + (7-sleep)*8 + stress*5
            score = max(0, min(100, score))
            if score < 30: level, color, advice = "🟢 Low Burnout - Tumi valo aso!", "#d4edda", "Continue: Regular break nao, pani khao."
            elif score < 60: level, color, advice = "🟡 Medium Burnout - Sabdhan!", "#fff3cd", "Advice: Ajke 30 min break nao, Heavy patient kom nao, Kalke early leave nao."
            else: level, color, advice = "🔴 High Burnout - SOS! Rest dorkar", "#f8d7da", "Advice: Ajkei Senior ke janao, Duty komao, 1 din rest nao, Emergency chara notun patient nio na."
            result = f"<div style='background:{color};padding:20px;border-radius:10px;'><h2>Burnout Score: {score}/100</h2><h3>{level}</h3><p>{advice}</p><p>Hours: {hours}h | Patients: {patients} | Sleep: {sleep}h | Stress: {stress}/10</p></div>"
        except: result = "Invalid input"
    return f"""<a href="/">Back</a><h1>🔥 Burnout Meter - Doctor Self Check</h1>
    <form method="post" style="max-width:600px;background:white;padding:15px;border-radius:10px;">
      <label>Doctor</label><select name="doctor"><option>Dr. Rahim</option><option>Dr. Karim</option><option>Dr. Sara</option><option>Dr. Tanvir</option></select>
      <label>Ajke koto ghonta duty korso?</label><input name="hours" type="number" value="8" required>
      <label>Ajke kotojon patient dekhso?</label><input name="patients" type="number" value="10" required>
      <label>Goto rate koto ghonta ghumaiso?</label><input name="sleep" type="number" value="7" required>
      <label>Stress Level (1-10)</label><input name="stress" type="number" min="1" max="10" value="5" required>
      <br><button type="submit" style="padding:10px 20px;background:#dc3545;color:white;border:none;">Check My Burnout</button>
    </form><br>{result}
    <p><small>Detailing: Score 60+ hole SOS Mode e jao, Senior ke inform koro.</small></p>
    """

# ============ SOS MODE ============
@app.route("/sos-mode", methods=["GET", "POST"])
def sos_mode():
    if 'user' not in session: return redirect("/login")
    msg = ""
    if request.method == "POST":
        typ = request.form.get("type")
        patient = request.form.get("patient", "")
        msg = f"<div style='background:#f8d7da;padding:20px;border-radius:10px;'><h2>🚨 SOS ACTIVATED - {typ}</h2><p>Patient: {patient} | Doctor: {session['user']} | Time: {datetime.now().strftime('%I:%M %p')}</p><p><b>Action:</b> Senior Doctor + Nurse ke call dao. CCU bed ready koro.</p></div>"
    return f"""<a href="/">Back</a><h1>🚨 SOS Mode - Emergency</h1>{msg}
    <form method="post" style="max-width:600px;background:white;padding:15px;border-radius:10px;">
      <label>Emergency Type - Select:</label><select name="type"><option>STEMI - ST Elevation MI</option><option>Cardiac Arrest</option><option>Severe Chest Pain</option><option>Heart Failure - Breathlessness</option><option>High BP Crisis - 200/120+</option><option>Low BP - Shock</option><option>Arrhythmia - Very Fast / Slow HR</option></select>
      <label>Patient Name / Bed No</label><input name="patient" placeholder="Ex: Rahim - Bed 5, CCU" required>
      <label>Details</label><input name="details" placeholder="Ex: BP 90/60, HR 120, EF 25%">
      <br><button type="submit" style="padding:15px 30px;background:#dc3545;color:white;border:none;font-size:18px;">🚨 ACTIVATE SOS</button>
    </form>
    <h3>Emergency Protocol - Step by Step:</h3>
    <div style="background:white;padding:15px;border-radius:10px;">
      <p><b>1. STEMI:</b> ECG STAT -> Aspirin 300mg + Clopidogrel -> Troponin -> Cath Lab Call -> CCU Admit</p>
      <p><b>2. Cardiac Arrest:</b> CPR Start -> Defibrillator -> Adrenaline -> Senior Call</p>
      <p><b>3. Heart Failure:</b> Oxygen -> Furosemide IV -> BP Check -> Echo</p>
      <p><b>4. BP Crisis:</b> BP Recheck -> Labetalol / GTN -> ICU</p>
      <p><b>📞 Emergency Numbers:</b> CCU: 101 | Senior Doctor: Call Now | Nurse Station: 102</p>
    </div>
    """

@app.route("/language")
def language():
    session['language'] = 'bn' if session.get('language') == 'en' else 'en'
    return redirect(request.referrer or "/")

@app.route("/assistant", methods=["GET", "POST"])
def assistant():
    if request.method == "POST":
        if request.form.get('pass') == "1234":
            session['assistant'] = True; return redirect("/")
        return render_template_string(LOGIN, err="Invalid assistant password")
    return render_template_string("""<!DOCTYPE html><html><body style="font-family:Arial;margin:100px auto;text-align:center"><h2>Assistant Login</h2><form method="post"><label>Password</label><input name="pass" type="password" required><br><br><button style="padding:10px 30px;background:#28a745;color:white;border:none">Login</button></form></body></html>""")

@app.route('/all')
def all_in_one():
    if 'user' not in session: return redirect("/login")
    return """
    <html><body style="font-family: Arial; padding: 20px;">
    <h1>🏥 Sob Eksathe - Hospital Dashboard</h1>
    <a href="/all">Refresh</a> | <a href="/">Home</a><hr>
    <h2>1. Patients</h2><iframe src="/patients" width="100%" height="400" style="border:1px solid #ccc;"></iframe><hr>
    <h2>2. Workflow</h2><iframe src="/workflow" width="100%" height="400" style="border:1px solid #ccc;"></iframe><hr>
    <h2>3. QTC</h2><iframe src="/qtc" width="100%" height="400" style="border:1px solid #ccc;"></iframe><hr>
    <h2>4. Prescriptions</h2><iframe src="/prescriptions" width="100%" height="400" style="border:1px solid #ccc;"></iframe><hr>
    <h2>5. Smart Workload</h2><iframe src="/smart-workload" width="100%" height="400" style="border:1px solid #ccc;"></iframe><hr>
    <h2>6. Burnout Meter</h2><iframe src="/burnout-meter" width="100%" height="400" style="border:1px solid #ccc;"></iframe><hr>
    <h2>7. SOS Mode</h2><iframe src="/sos-mode" width="100%" height="400" style="border:1px solid #ccc;"></iframe>
    </body></html>
    """

# ============ RUN - SOBAR SESHE THAKBE ============
if __name__=="__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)