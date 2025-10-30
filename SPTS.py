# student_perf_app.py
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_file
import io, csv, os, statistics, datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SPTS_SECRET", "change_this_secret_for_demo")

# --- Admin credentials (change or use env vars) ---
ADMIN_USERNAME = os.environ.get("SPTS_ADMIN", "admin")
ADMIN_PASSWORD = os.environ.get("SPTS_PASS", "12345")

# --- In-memory data store (Option A) ---
# Each student: {id, name, roll, marks: {"Math":int, "Science":int, ...}, avg, grade, status, created_at}
students = []
next_id = 1

SUBJECTS = ["Math", "Physics", "Chemistry", "English", "Computer"]

# Seed sample data
def seed_sample():
    global next_id
    sample = [
        ("Aishwarya","CSB101",[82,78,75,88,90]),
        ("Bharath","CSB102",[65,59,70,72,68]),
        ("Chitra","CSB103",[92,95,94,90,96]),
        ("Dinesh","CSB104",[45,50,40,55,48]),
    ]
    for name, roll, marks in sample:
        add_student(name, roll, dict(zip(SUBJECTS, marks)))

def compute_metrics(marks_dict):
    scores = list(marks_dict.values())
    avg = round(statistics.mean(scores), 2) if scores else 0
    # Grade logic
    if avg >= 90:
        grade = "A+"
    elif avg >= 80:
        grade = "A"
    elif avg >= 70:
        grade = "B"
    elif avg >= 60:
        grade = "C"
    elif avg >= 50:
        grade = "D"
    else:
        grade = "F"
    status = "Pass" if min(scores) >= 35 and avg >= 35 else "Fail"
    return avg, grade, status

def add_student(name, roll, marks):
    global next_id
    avg, grade, status = compute_metrics(marks)
    student = {
        "id": next_id,
        "name": name,
        "roll": roll,
        "marks": marks,
        "avg": avg,
        "grade": grade,
        "status": status,
        "created_at": datetime.datetime.now().timestamp()
    }
    students.append(student)
    next_id += 1
    return student

def update_student(sid, name, roll, marks):
    for s in students:
        if s["id"] == sid:
            s["name"] = name
            s["roll"] = roll
            s["marks"] = marks
            s["avg"], s["grade"], s["status"] = compute_metrics(marks)
            return s
    return None

def delete_student(sid):
    global students
    students = [s for s in students if s["id"] != sid]

# initialize seed
seed_sample()

# --- Templates (single-file) ---
TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Student Performance Tracking System</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root{--bg:#f4f7fb;--card:#fff;--primary:#1a73e8;--muted:#6b7280}
    body{font-family:Inter,Arial;margin:0;background:var(--bg);color:#111}
    .top{background:var(--card);padding:12px 20px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 1px 3px rgba(0,0,0,0.06)}
    .brand{font-weight:700;color:var(--primary)}
    .layout{display:flex;gap:20px;padding:20px}
    .left{width:360px}
    .card{background:var(--card);border-radius:10px;padding:16px;box-shadow:0 6px 18px rgba(17,24,39,0.06)}
    .h{font-weight:700;margin-bottom:10px}
    input,select,textarea{width:100%;padding:10px;margin:8px 0;border:1px solid #e6e9ef;border-radius:8px}
    button{background:var(--primary);color:#fff;border:none;padding:10px 12px;border-radius:8px;cursor:pointer}
    .muted{color:var(--muted);font-size:13px}
    table{width:100%;border-collapse:collapse;margin-top:10px}
    th,td{padding:8px;border-bottom:1px solid #f0f2f5;text-align:left;font-size:14px}
    tr:hover{background:#f8fbff}
    .actions button{margin-right:6px}
    .badge{padding:6px 8px;border-radius:999px;font-weight:700}
    .Aplus{background:#e6f4ea;color:#137333}
    .A{background:#e8f0fe;color:#1a73e8}
    .F{background:#fdecea;color:#b91c1c}
    .controls{display:flex;gap:8px;align-items:center}
    #chartWrap{margin-top:14px}
    .small{font-size:13px;color:var(--muted)}
    .logout{font-size:13px}
    .top-right{display:flex;gap:10px;align-items:center}
    .csv-btn{background:#fff;border:1px solid #e6e9ef;color:var(--primary);padding:8px 10px;border-radius:8px;cursor:pointer}
  </style>
</head>
<body>
  <div class="top">
    <div class="brand">Student Performance Tracking</div>
    <div class="top-right">
      <div class="small">Admin: <strong>{{ admin }}</strong></div>
      <form method="post" action="/logout" style="margin:0">
        <button type="submit" class="csv-btn">Logout</button>
      </form>
    </div>
  </div>

  <div class="layout">
    <div class="left">
      <div class="card">
        <div class="h">Add / Edit Student</div>
        <form id="studentForm" onsubmit="return submitForm();">
          <input type="hidden" id="sid" value="">
          <label>Name</label>
          <input id="name" required>
          <label>Roll</label>
          <input id="roll" required>
          {% for subj in subjects %}
            <label>{{ subj }}</label>
            <input id="m_{{ loop.index0 }}" type="number" min="0" max="100" required>
          {% endfor %}
          <div style="display:flex;gap:8px;margin-top:6px">
            <button type="submit">Save</button>
            <button type="button" onclick="clearForm()" style="background:#fff;color:var(--primary);border:1px solid #e6e9ef">Clear</button>
          </div>
          <div class="small" style="margin-top:8px">Tip: enter marks 0-100. Pass if each subject ≥ 35.</div>
        </form>
      </div>

      <div class="card" style="margin-top:14px">
        <div class="h">Export / Filters</div>
        <div style="display:flex;gap:8px;margin-bottom:8px">
          <input id="search" placeholder="Search by name or roll">
          <select id="gradeFilter"><option value="">All Grades</option><option value="A+">A+</option><option value="A">A</option><option value="B">B</option><option value="C">C</option><option value="D">D</option><option value="F">F</option></select>
        </div>
        <div style="display:flex;gap:8px">
          <button onclick="applyFilters()">Apply</button>
          <button onclick="resetFilters()" style="background:#fff;color:var(--primary);border:1px solid #e6e9ef">Reset</button>
          <button onclick="exportCSV()" style="margin-left:auto" class="csv-btn">Export CSV</button>
        </div>
        <div class="small" id="countInfo" style="margin-top:8px"></div>
      </div>
    </div>

    <div class="card" style="flex:1">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div class="h">Students</div>
        <div class="small">Records: <span id="recCount">0</span></div>
      </div>

      <div id="tableWrap"></div>

      <div id="chartWrap" class="card" style="margin-top:14px">
        <div class="h">Subject-wise Average</div>
        <canvas id="avgChart" height="120"></canvas>
      </div>
    </div>
  </div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  const subjects = {{ subjects | tojson }};
  let allStudents = []; // cached
  let filters = {q:'', grade:''};

  async function fetchStudents(){
    const resp = await fetch('/api/students');
    allStudents = await resp.json();
    renderTable(allStudents);
    renderChart(allStudents);
  }

  function renderTable(data){
    document.getElementById('recCount').innerText = data.length;
    document.getElementById('countInfo').innerText = 'Showing ' + data.length + ' records';
    if(!data.length){ document.getElementById('tableWrap').innerHTML = '<div class="small">No records</div>'; return; }
    let html = '<table><thead><tr><th>Name</th><th>Roll</th><th>Avg</th><th>Grade</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
    for(const s of data){
      html += `<tr>
        <td><strong>${escape(s.name)}</strong><div class="small">${subjects.map((sub,i)=>sub+': '+s.marks[i]).join(' • ')}</div></td>
        <td>${escape(s.roll)}</td>
        <td>${s.avg}</td>
        <td><span class="badge ${s.grade==='A+'? 'Aplus': s.grade==='F'?'F':'A'}">${s.grade}</span></td>
        <td>${s.status}</td>
        <td class="actions">
          <button onclick="editStudent(${s.id})" class="csv-btn">Edit</button>
          <button onclick="deleteStudent(${s.id})" style="background:#fdecea;color:#b91c1c;border:none;padding:8px 10px;border-radius:8px">Delete</button>
        </td>
      </tr>`;
    }
    html += '</tbody></table>';
    document.getElementById('tableWrap').innerHTML = html;
  }

  function escape(s){ return (s||'').toString().replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  async function submitForm(){
    const sid = document.getElementById('sid').value;
    const name = document.getElementById('name').value.trim();
    const roll = document.getElementById('roll').value.trim();
    const marks = {};
    for(let i=0;i<subjects.length;i++){
      const v = parseFloat(document.getElementById('m_'+i).value);
      marks[subjects[i]] = Number.isFinite(v)? v: 0;
    }
    const payload = {name, roll, marks};
    const url = sid? '/api/student/'+sid : '/api/student';
    const method = sid? 'PUT' : 'POST';
    const resp = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    if(resp.ok){ clearForm(); fetchStudents(); } else { alert('Error saving'); }
    return false;
  }

  function clearForm(){
    document.getElementById('sid').value=''; document.getElementById('name').value=''; document.getElementById('roll').value='';
    for(let i=0;i<subjects.length;i++) document.getElementById('m_'+i).value='';
  }

  async function editStudent(id){
    const resp = await fetch('/api/student/'+id);
    const data = await resp.json();
    if(!data.ok) return alert('Not found');
    const s = data.student;
    document.getElementById('sid').value = s.id;
    document.getElementById('name').value = s.name;
    document.getElementById('roll').value = s.roll;
    subjects.forEach((sub,i)=> document.getElementById('m_'+i).value = s.marks[i]);
    window.scrollTo({top:0,behavior:'smooth'});
  }

  async function deleteStudent(id){
    if(!confirm('Delete this student?')) return;
    const resp = await fetch('/api/student/'+id, {method:'DELETE'});
    if(resp.ok) fetchStudents();
  }

  function applyFilters(){
    filters.q = document.getElementById('search').value.trim().toLowerCase();
    filters.grade = document.getElementById('gradeFilter').value;
    let out = allStudents.filter(s=>{
      const matchQ = !filters.q || s.name.toLowerCase().includes(filters.q) || s.roll.toLowerCase().includes(filters.q);
      const matchG = !filters.grade || s.grade === filters.grade;
      return matchQ && matchG;
    });
    renderTable(out);
    renderChart(out);
  }

  function resetFilters(){ document.getElementById('search').value=''; document.getElementById('gradeFilter').value=''; filters={q:'',grade:''}; renderTable(allStudents); renderChart(allStudents); }

  async function exportCSV(){
    const resp = await fetch('/export?search='+encodeURIComponent(filters.q||'')+'&grade='+encodeURIComponent(filters.grade||''));
    if(resp.ok){
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href=url; a.download='students_export.csv'; document.body.appendChild(a); a.click(); a.remove();
    } else alert('Export failed');
  }

  // Chart: subject-wise average
  let chartInstance = null;
  function renderChart(data){
    const ctx = document.getElementById('avgChart').getContext('2d');
    if(!data.length){
      if(chartInstance){ chartInstance.destroy(); chartInstance=null; }
      ctx.clearRect(0,0,600,300);
      return;
    }
    const avgs = subjects.map((sub,i)=>{
      const vals = data.map(s=> s.marks[i]);
      return (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(2);
    });
    const cfg = {
      type:'bar',
      data:{ labels: subjects, datasets:[{ label:'Average', data: avgs }]},
      options:{ responsive:true, plugins:{ legend:{ display:false } } }
    };
    if(chartInstance) chartInstance.destroy();
    chartInstance = new Chart(ctx, cfg);
  }

  // initial load
  fetchStudents();
</script>
</body>
</html>
"""

# --- API endpoints ---
from flask import abort

@app.route("/login", methods=["GET","POST"])
@app.route("/", methods=["GET","POST"])
def index():
    # login handling
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        if user == ADMIN_USERNAME and pwd == ADMIN_PASSWORD:
            session["admin"] = user
            return redirect(url_for("dashboard"))
        else:
            return render_template_string(LOGIN_TEMPLATE(), error="Invalid credentials")
    # if already logged in redirect
    if session.get("admin"):
        return redirect(url_for("dashboard"))
    return render_template_string(LOGIN_TEMPLATE(), error=None)

def LOGIN_TEMPLATE():
    return """
    <!doctype html><html><head><meta charset="utf-8"><title>Login</title>
    <style>body{font-family:Inter,Arial;background:#f4f7fb;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
    .box{background:#fff;padding:28px;border-radius:12px;box-shadow:0 6px 20px rgba(17,24,39,0.06);width:360px}
    input{width:100%;padding:10px;margin:8px 0;border:1px solid #e6e9ef;border-radius:8px}
    button{background:#1a73e8;color:#fff;padding:10px;border:none;border-radius:8px;width:100%}
    .err{color:#b91c1c;margin-top:6px}</style></head><body>
    <div class="box">
      <h2 style="margin:0 0 8px 0">Admin Login</h2>
      <form method="post">
        <input name="username" placeholder="Username" required>
        <input name="password" placeholder="Password" type="password" required>
        <button type="submit">Login</button>
      </form>
      {% if error %}<div class="err">{{ error }}</div>{% endif %}
    </div>
    </body></html>
    """

@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect(url_for("index"))
    return render_template_string(TEMPLATE, subjects=SUBJECTS, admin=session.get("admin"))

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

# API: CRUD
@app.route("/api/students")
def api_students():
    if not session.get("admin"):
        return jsonify([]), 401
    # return list with marks as list for JS rendering order
    out = []
    for s in students:
        out.append({
            "id": s["id"],
            "name": s["name"],
            "roll": s["roll"],
            "marks": [s["marks"].get(sub,0) for sub in SUBJECTS],
            "avg": s["avg"],
            "grade": s["grade"],
            "status": s["status"],
            "created_at": s["created_at"]
        })
    return jsonify(out)

@app.route("/api/student", methods=["POST"])
def api_add_student():
    if not session.get("admin"):
        return jsonify(ok=False), 401
    data = request.get_json()
    name = data.get("name","").strip()
    roll = data.get("roll","").strip()
    marks = data.get("marks", {})
    # convert marks list/dict to dict by subjects if needed
    if isinstance(marks, list):
        marks = dict(zip(SUBJECTS, [int(m) if m is not None else 0 for m in marks]))
    else:
        marks = {k: int(v) for k,v in marks.items()}
    s = add_student(name, roll, marks)
    return jsonify(ok=True, student=s)

@app.route("/api/student/<int:sid>", methods=["GET","PUT","DELETE"])
def api_student(sid):
    if not session.get("admin"):
        return jsonify(ok=False), 401
    if request.method == "GET":
        for s in students:
            if s["id"] == sid:
                return jsonify(ok=True, student={
                    "id": s["id"],
                    "name": s["name"],
                    "roll": s["roll"],
                    "marks":[s["marks"].get(sub,0) for sub in SUBJECTS],
                    "avg": s["avg"],
                    "grade": s["grade"],
                    "status": s["status"]
                })
        return jsonify(ok=False), 404
    if request.method == "PUT":
        data = request.get_json()
        name = data.get("name","").strip()
        roll = data.get("roll","").strip()
        marks = data.get("marks", {})
        if isinstance(marks, list):
            marks = dict(zip(SUBJECTS, [int(m) if m is not None else 0 for m in marks]))
        else:
            marks = {k: int(v) for k,v in marks.items()}
        s = update_student(sid, name, roll, marks)
        return jsonify(ok=True, student=s)
    if request.method == "DELETE":
        delete_student(sid)
        return jsonify(ok=True)

# export filtered CSV
@app.route("/export")
def export_csv():
    if not session.get("admin"):
        return jsonify(ok=False), 401
    q = request.args.get("search","").lower()
    grade = request.args.get("grade","")
    filtered = []
    for s in students:
        if q and q not in s["name"].lower() and q not in s["roll"].lower(): continue
        if grade and s["grade"] != grade: continue
        filtered.append(s)
    # create CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    header = ["id","name","roll"] + SUBJECTS + ["avg","grade","status"]
    writer.writerow(header)
    for s in filtered:
        row = [s["id"], s["name"], s["roll"]] + [s["marks"].get(sub,0) for sub in SUBJECTS] + [s["avg"], s["grade"], s["status"]]
        writer.writerow(row)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(mem, as_attachment=True, download_name=f"students_{ts}.csv", mimetype="text/csv")

if __name__ == "__main__":
    app.run(debug=True)
