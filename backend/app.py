from flask import Flask, jsonify,render_template,request
from db import get_connection
from flask_cors import CORS
import base64
import os
import mysql.connector
import random
import string
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
os.makedirs("static/faces", exist_ok=True)

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return "Smart Attendance System Running"


# ----------------------------
# GENERATE TOKEN
# ----------------------------
def generate_token():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ----------------------------
# START SESSION (TEACHER)
# ----------------------------
@app.route("/start_session/<int:teacher_id>/<int:class_id>")
def start_session(teacher_id, class_id):

    token = generate_token()
    start_time = datetime.now()
    expiry_time = start_time + timedelta(minutes=3)
    status = "active"

    try:
        conn=get_connection()
        cursor=conn.cursor()
        cursor.execute("""
            INSERT INTO sessions
            (teacher_id, token, start_time, expiry_time, status, class_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (teacher_id, token, start_time, expiry_time, status, class_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Session Started",
            "teacher_id": teacher_id,
            "class_id": class_id,
            "token": token,
            "expiry_time": str(expiry_time),
            "status": status
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# ----------------------------
# MARK ATTENDANCE (STUDENT)
# ----------------------------
@app.route("/mark_attendance/<int:student_id>/<int:class_id>/<token>")
def mark_attendance(student_id, class_id, token):

    try:
        

        # Check student exists
        conn=get_connection()
        cursor=conn.cursor()
        cursor.execute(
            "SELECT * FROM students WHERE student_id = %s",
            (student_id,)
        )
        student = cursor.fetchone()

        if not student:
            return jsonify({"error": "Student not found"})

        # Check class exists
        cursor.execute(
            "SELECT * FROM classes WHERE class_id = %s",
            (class_id,)
        )
        cls = cursor.fetchone()

        if not cls:
            return jsonify({"error": "Class not found"})

        # Check session valid
        cursor.execute("""
            SELECT * FROM sessions
            WHERE class_id = %s
            AND token = %s
            AND status = 'active'
        """, (class_id, token))

        session = cursor.fetchone()

        if not session:
            return jsonify({"error": "Invalid session or token"})

        # Duplicate attendance check
        cursor.execute("""
            SELECT * FROM attendance
            WHERE student_id = %s
            AND class_id = %s
            AND date = CURDATE()
        """, (student_id, class_id))

        existing = cursor.fetchone()

        if existing:
            return jsonify({
                "message": "Attendance already marked"
            })

        # Insert attendance
        cursor.execute("""
            INSERT INTO attendance
            (student_id, class_id, date, status)
            VALUES (%s, %s, CURDATE(), %s)
        """, (student_id, class_id, "Present"))

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Attendance Marked Successfully",
            "student_id": student_id,
            "class_id": class_id,
            "status": "Present"
        })

    except Exception as e:
        return jsonify({"error": str(e)})
# ----------------------------
# PRESENT STUDENTS COUNT
# ----------------------------
@app.route("/present/<int:class_id>")
def present_students(class_id):

    try:
        
        conn=get_connection()
        cursor=conn.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM attendance
            WHERE class_id = %s
            AND date = CURDATE()
            AND status = 'Present'
        """, (class_id,))

        count = cursor.fetchone()[0]

        return jsonify({
            "class_id": class_id,
            "present_students": count
        })

    except Exception as e:
        return jsonify({"error": str(e)})
# ----------------------------
# ABSENT STUDENTS COUNT
# ----------------------------
@app.route("/absent/<int:class_id>")
def absent_students(class_id):

    try:


        # Total students
        conn=get_connection()
        cursor=conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]

        # Present students today
        cursor.execute("""
            SELECT COUNT(*)
            FROM attendance
            WHERE class_id = %s
            AND date = CURDATE()
            AND status = 'Present'
        """, (class_id,))

        present_students = cursor.fetchone()[0]

        absent_students = total_students - present_students

        return jsonify({
            "class_id": class_id,
            "total_students": total_students,
            "present_students": present_students,
            "absent_students": absent_students
        })

    except Exception as e:
        return jsonify({"error": str(e)})
# ----------------------------
# ATTENDANCE REPORT
# ----------------------------
@app.route("/report/<int:class_id>")
def attendance_report(class_id):

    try:
        conn=get_connection()
        cursor=conn.cursor(dictionary=True)

        cursor.execute("""
SELECT
    s.student_id,
    s.name,
    %s AS class_id,
    CURDATE() AS date,
    COALESCE(a.status,'Absent') AS status
FROM students s
LEFT JOIN attendance a
ON s.student_id = a.student_id
AND a.class_id = %s
AND a.date = CURDATE()
""",(class_id,class_id))

        records = cursor.fetchall()

        return jsonify(records)

    except Exception as e:
        return jsonify({"error": str(e)})
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")
@app.route("/test_db")
def test_db():
    try:
        conn=get_connection()
        cursor=conn.cursor()
        cursor.execute("SELECT 1")
        return "Database Connected Successfully"
    except Exception as e:
        return str(e)


# ----------------------------
# REGISTER PAGE
# ----------------------------
@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


# ----------------------------
# REGISTER API
# ----------------------------
@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json()

    name = data.get("name")
    roll = data.get("roll")
    image = data.get("image")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
    """
    INSERT INTO students
    (name, roll_no, image)
    VALUES (%s,%s,%s)
    """,
    (name, roll, image)
)

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Saved successfully"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })
@app.route("/students")
def students():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT student_id,
               name,
               roll_no,
               image
        FROM students
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "students.html",
        students=data
    )
@app.route("/attendance")
def attendance_page():
    return render_template("attendance.html")
@app.route("/verify_student", methods=["POST"])
def verify_student():

    try:

        data = request.get_json()

        name = data.get("name")
        roll = data.get("roll")
        class_id = data.get("class_id")
        token = data.get("token")

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check student
        cursor.execute("""
            SELECT *
            FROM students
            WHERE name=%s
            AND roll_no=%s
        """,(name,roll))

        student = cursor.fetchone()

        if not student:

            return jsonify({
                "message":"Invalid Name or Roll Number"
            })

        student_id = student["student_id"]

        # Check class
        cursor.execute("""
            SELECT *
            FROM classes
            WHERE class_id=%s
        """,(class_id,))

        cls = cursor.fetchone()

        if not cls:

            return jsonify({
                "message":"Invalid Class ID"
            })

        # Check active token
        cursor.execute("""
            SELECT *
            FROM sessions
            WHERE class_id=%s
            AND token=%s
            AND status='active'
        """,(class_id,token))

        session = cursor.fetchone()

        if not session:

            return jsonify({
                "message":"Invalid Token"
            })

        # Check duplicate attendance
        cursor.execute("""
            SELECT *
            FROM attendance
            WHERE student_id=%s
            AND class_id=%s
            AND date=CURDATE()
        """,(student_id,class_id))

        existing = cursor.fetchone()

        if existing:

            return jsonify({
                "message":"Attendance Already Marked"
            })

        # Insert attendance
        cursor.execute("""
            INSERT INTO attendance
            (student_id,class_id,date,status)
            VALUES(%s,%s,CURDATE(),'Present')
        """,(student_id,class_id))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "message":"Attendance Marked Successfully ✅"
        })

    except Exception as e:

        return jsonify({
            "message":str(e)
        })

# RUN SERVER
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)









