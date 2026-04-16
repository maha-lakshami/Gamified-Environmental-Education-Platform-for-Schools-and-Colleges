from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

def slug_to_category(slug):

    mapping = {
        "water_conservation": "Water Conservation",
        "waste_reduction": "Waste Reduction",
        "energy_saving": "Energy Saving",
        "transportation": "Transportation",
        "biodiversity": "Biodiversity",
        "plastic_free_living": "Plastic-Free Living",
        "sustainable_food": "Sustainable Food",
        "air_pollution": "Air Pollution",
        "green_lifestyle": "Green Lifestyle",
        "recycling": "Recycling"
    }

    return mapping.get(slug)


# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # ✅ SAFE FIX
        role = request.form.get("role", "student")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=? AND role=?",
            (email, password, role)
        ).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["name"]
            session["role"] = user["role"]

            return redirect("/dashboard")

        else:
            return render_template("login.html", error="Invalid Login")

    return render_template("login.html")


# ================= SIGNUP =================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        name = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        # ✅ GET ROLE
        role = request.form.get("role", "student")

        conn = get_db()

        conn.execute("""
        INSERT INTO users (name, email, password, role, school_id, status, verification_status, points)
        VALUES (?, ?, ?, ?, 1, 'active', 'pending', 0)
        """, (name, email, password, role))   # ✅ FIXED

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("signup.html")


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    # ✅ ADD THIS (ONLY ADDITION)
    if "role" in session and session["role"] == "student":
        return redirect("/student_dashboard")

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # ================= STATS =================

    # Total students
    cur.execute("SELECT COUNT(*) FROM users")
    total_students = cur.fetchone()[0]

    # Active participants (students with points > 0)
    cur.execute("SELECT COUNT(*) FROM users WHERE points > 0")
    active_participants = cur.fetchone()[0]

    # Total challenges completed
    cur.execute("SELECT COUNT(*) FROM completed_levels")
    challenges_completed = cur.fetchone()[0]

    # Total points earned
    cur.execute("SELECT SUM(points) FROM users")
    result = cur.fetchone()[0]
    total_points = result if result else 0

    conn.close()

    # ================= FINAL =================

    return render_template(
        "dashboard.html",
        total_students=total_students,
        active_participants=active_participants,
        challenges_completed=challenges_completed,
        total_points=total_points
    )


@app.route("/student_dashboard")
def student_dashboard():

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    activities = conn.execute("SELECT * FROM activities").fetchall()
    challenges = conn.execute("SELECT * FROM challenges").fetchall()

    conn.close()

    return render_template(
        "student_dashboard.html",
        activities=activities,
        challenges=challenges
    )

# ================= MANAGE ACTIVITIES =================
@app.route("/manage_activities")
def manage_activities():

    # ✅ ADD THIS LINE
    if session.get("role") != "teacher":
        return "Access Denied"

    conn = get_db()
    activities = conn.execute("SELECT * FROM activities").fetchall()
    conn.close()

    return render_template("manage_activities.html", activities=activities)

@app.route("/create_activity", methods=["GET", "POST"])
def create_activity():

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        points = request.form["points"]
        total_students = request.form["total_students"]
        difficulty = request.form["difficulty"]
        status = request.form["status"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        # ✅ NEW FIELDS
        video = request.files.get("video")
        materials = request.form.get("materials")
        steps = request.form.get("steps")

        import os, time

        video_filename = ""

        if video:
            if not os.path.exists("static/videos"):
                os.makedirs("static/videos")

            video_filename = str(int(time.time())) + "_" + video.filename
            video.save("static/videos/" + video_filename)

        conn = get_db()

        conn.execute("""
        INSERT INTO activities
        (title, description, category, points, total_students,
         difficulty, status, start_date, end_date,
         video, materials, steps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, category, points, total_students,
              difficulty, status, start_date, end_date,
              video_filename, materials, steps))

        conn.commit()
        conn.close()

        return redirect("/manage_activities")

    # ✅ GET request
    return render_template("create_activity.html")

@app.route("/activity/<int:id>")
def activity_view(id):

    conn = get_db()

    activity = conn.execute("""
        SELECT * FROM activities WHERE id=?
    """, (id,)).fetchone()

    conn.close()

    # 🔥 IMPORTANT: handle empty case
    if not activity:
        return "Activity not found"

    return render_template("activity_view.html", activity=activity)

@app.route("/mark_learned/<int:id>")
def mark_learned(id):

    conn = get_db()

    # example: add points
    conn.execute("""
        UPDATE users
        SET points = points + 10
        WHERE id = ?
    """, (session["user_id"],))

    conn.commit()
    conn.close()

    return redirect("/manage_activities")


@app.route("/delete_activity/<int:id>")
def delete_activity(id):

    conn = get_db()
    conn.execute("DELETE FROM activities WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/manage_activities")



@app.route('/reports')
def reports():

    # ✅ ADD THIS LINE
    if session.get("role") != "teacher":
        return "Access Denied"

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    # ================= OVERVIEW =================
    total_students = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    active_students = conn.execute("""
SELECT COUNT(*) FROM users WHERE points > 0
""").fetchone()[0]

    total_points = conn.execute("SELECT SUM(points) FROM users").fetchone()[0] or 0

    total_activities = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]

    # ================= QUIZ =================
    total_quiz_attempts = conn.execute("SELECT COUNT(*) FROM quiz_attempts").fetchone()[0]

    avg_score = conn.execute("SELECT AVG(score) FROM quiz_attempts").fetchone()[0] or 0

    highest_score = conn.execute("SELECT MAX(score) FROM quiz_attempts").fetchone()[0] or 0

    total_correct = conn.execute("SELECT SUM(correct_answers) FROM quiz_attempts").fetchone()[0] or 0
    total_questions = conn.execute("SELECT SUM(total_questions) FROM quiz_attempts").fetchone()[0] or 0

    accuracy = (total_correct / total_questions * 100) if total_questions else 0

    # ================= CHALLENGES =================
    total_challenges = conn.execute("SELECT COUNT(*) FROM challenges").fetchone()[0]

    total_levels = total_challenges * 3   # your logic

    completed_challenges = conn.execute("""
        SELECT COUNT(*) FROM submissions WHERE status='completed'
    """).fetchone()[0]

    pending_challenges = conn.execute("""
        SELECT COUNT(*) FROM submissions WHERE status='pending'
    """).fetchone()[0]

    # ================= ECO / ACTIVITIES =================
    trees = conn.execute("""
    SELECT COUNT(*) FROM activities WHERE category='tree'
""").fetchone()[0]

    activities_done = total_activities

    participation = (active_students / total_students * 100) if total_students else 0

    # ================= LEADERBOARD =================
    top_students = conn.execute("""
        SELECT name, points FROM users
        ORDER BY points DESC LIMIT 5
    """).fetchall()

    # ================= WEAK STUDENTS =================
    weak_students = conn.execute("""
        SELECT name, points FROM users
        WHERE points < 50
        LIMIT 5
    """).fetchall()

    conn.close()

    return render_template("reports.html",
        total_students=total_students,
        active_students=active_students,
        total_points=total_points,
        total_activities=total_activities,

        total_quiz_attempts=total_quiz_attempts,
        avg_score=round(avg_score,2),
        highest_score=highest_score,
        accuracy=round(accuracy,2),

        total_challenges=total_challenges,
        total_levels=total_levels,
        completed_challenges=completed_challenges,
        pending_challenges=pending_challenges,

        trees=trees,
        activities_done=activities_done,
        participation=round(participation,2),

        top_students=top_students,
        weak_students=weak_students
    )

# ================= STUDENT VERIFICATION =================
@app.route("/verify")
def student_verification():

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    pending = conn.execute("""
        SELECT * FROM users
        WHERE role='student' AND verification_status='pending'
    """).fetchall()

    verified = conn.execute("""
        SELECT * FROM users
        WHERE role='student' AND verification_status='verified'
    """).fetchall()

    rejected = conn.execute("""
        SELECT * FROM users
        WHERE role='student' AND verification_status='rejected'
    """).fetchall()

    conn.close()

    return render_template(
        "student_verification.html",
        pending=pending,
        verified=verified,
        rejected=rejected
    )


@app.route("/approve_submission/<int:id>")
def approve_submission(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE challenge_submissions
        SET status='approved'
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/view_submissions")


@app.route("/reject_submission/<int:id>")
def reject_submission(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE challenge_submissions
        SET status='rejected'
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/view_submissions")

# ================= CHALLENGE LEVEL PAGE =================
@app.route("/challenge/<category_slug>")
def challenge_levels(category_slug):

    category_map = {
    "water_conservation": "Water Conservation",
    "waste_reduction": "Waste Reduction",
    "energy_saving": "Energy Saving",
    "transportation": "Transportation",
    "biodiversity": "Biodiversity",
    "plastic_free_living": "Plastic-Free Living",
    "sustainable_food": "Sustainable Food",
    "air_pollution": "Air Pollution",
    "green_lifestyle": "Green Lifestyle",
    "recycling": "Recycling"
}

    category_name = category_map.get(category_slug)

    print("SLUG =", category_slug)
    print("CATEGORY NAME =", category_name)

    return render_template(
        "levels.html",
        category_slug=category_slug,
        category_name=category_name
    )

@app.route("/start_challenge/<int:id>")
def start_challenge(id):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    challenge = conn.execute(
        "SELECT * FROM challenges WHERE id=?",
        (id,)
    ).fetchone()

    tasks = conn.execute(
        "SELECT * FROM challenge_tasks WHERE challenge_id=?",
        (id,)
    ).fetchall()

    return render_template("start_challenge.html", c=challenge, tasks=tasks)

@app.route("/submit_challenge/<int:id>", methods=["POST"])
def submit_challenge(id):

    import time
    import os

    if not os.path.exists("static/uploads"):
        os.makedirs("static/uploads")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    uploaded_images = []   # existing
    data = []              # ✅ ADD THIS

    tasks = conn.execute("""
        SELECT * FROM challenge_tasks WHERE challenge_id=?
    """, (id,)).fetchall()

    for t in tasks:
        file = request.files.get(f"photo{t[0]}")

        if file:
            filename = str(int(time.time())) + "_" + file.filename
            file.save("static/uploads/" + filename)

            uploaded_images.append(filename)

            data.append((filename, t[2]))   # ✅ ADD THIS (VERY IMPORTANT)

            cursor.execute("""
                INSERT INTO challenge_submissions (user_id, challenge_id, image)
                VALUES (?, ?, ?)
            """, (session["user_id"], id, filename))

    conn.commit()
    conn.close()

    # ✅ CHANGE THIS LINE
    return render_template("challenge_result.html", images=uploaded_images, data=data)


@app.route("/view_submissions")
def view_submissions():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    data = conn.execute("""
        SELECT cs.*, c.title 
        FROM challenge_submissions cs
        JOIN challenges c ON cs.challenge_id = c.id
    """).fetchall()

    return render_template("submissions.html", data=data)

# ================= QUIZ LEVEL =================
@app.route("/quiz/<category>/<level>")
def quiz(category, level):

    # ✅ ADD THIS LINE
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    category_map = {
        "water_conservation": "Water Conservation",
        "waste_reduction": "Waste Reduction",
        "energy_saving": "Energy Saving",
        "transportation": "Transportation",
        "biodiversity": "Biodiversity",
        "plastic_free_living": "Plastic-Free Living",
        "sustainable_food": "Sustainable Food",
        "air_pollution": "Air Pollution",
        "green_lifestyle": "Green Lifestyle",
        "recycling": "Recycling"
    }

    category_name = category_map.get(category, category).strip()
    level = level.capitalize().strip()

    print("CATEGORY:", category_name)
    print("LEVEL:", level)

    questions = conn.execute("""
        SELECT * FROM quiz_questions
        WHERE LOWER(category)=LOWER(?) AND LOWER(level)=LOWER(?)
        ORDER BY id DESC
    """, (category_name, level)).fetchall()

    if not questions:
        print("❌ No questions found in DB!")

    session["quiz_qids"] = [q["id"] for q in questions]

    conn.close()

    return render_template(
        "quiz.html",
        questions=questions,
        category=category_name,
        level=level,
        submitted=False
    )



# ================= SUBMIT QUIZ =================
@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():

    conn = get_db()
    cur = conn.cursor()

    category = request.form.get("category")
    level = request.form.get("level")

    qids = session.get("quiz_qids", [])

    if not qids:
        return "Error: No quiz session found"

    placeholders = ",".join(["?"] * len(qids))

    questions = conn.execute(f"""
        SELECT * FROM quiz_questions
        WHERE id IN ({placeholders})
    """, qids).fetchall()

    score = 0

    for q in questions:
        selected = request.form.get(str(q['id']))
        correct = q["correct_answer"]

        if selected == correct:
            score += 1

    # ✅ Update points
    cur.execute("""
        UPDATE users SET points = points + ?
        WHERE id=?
    """, (score, session["user_id"]))

    # ✅ Save completed level
    cur.execute("""
        INSERT INTO completed_levels (user_id, category, level)
        VALUES (?, ?, ?)
    """, (session["user_id"], category, level))

    # ✅ ADD THIS BLOCK (VERY IMPORTANT 🔥)
    cur.execute("""
        INSERT INTO quiz_attempts (user_id, score, total_questions, correct_answers)
        VALUES (?, ?, ?, ?)
    """, (
        session["user_id"],
        score,
        len(questions),
        score
    ))

    conn.commit()
    conn.close()

    session.pop("quiz_qids", None)

    return redirect(url_for("quiz_result", score=score, total=len(questions)))


@app.route("/quiz_result")
def quiz_result():
    score = request.args.get("score")
    total = request.args.get("total")

    print("DEBUG:", score, total)

    return render_template("quiz_result.html", score=score, total=total)


@app.route("/create-challenge", methods=["GET","POST"])
def create_challenge():

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        points = request.form["points"]
        time_limit = request.form["time_limit"]
        difficulty = request.form["difficulty"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        # ✅ split tasks
        tasks = request.form["tasks"].split("\n")

        # ✅ connect DB
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # ✅ insert challenge FIRST
        cursor.execute("""
            INSERT INTO challenges 
            (title, description, category, points, time_limit, difficulty, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, category, points, time_limit, difficulty, start_date, end_date))

        # ✅ get challenge id
        challenge_id = cursor.lastrowid

        # ✅ insert tasks
        for t in tasks:
            if t.strip():
                cursor.execute("""
                    INSERT INTO challenge_tasks (challenge_id, task)
                    VALUES (?, ?)
                """, (challenge_id, t.strip()))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("create_challenge.html")


@app.route('/create-quiz', methods=['GET', 'POST'])
def create_quiz():

    message = ""

    if request.method == 'POST':
        category = request.form['category']
        level = request.form['level']
        question = request.form['question']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form['option3']
        option4 = request.form['option4']
        correct = request.form['correct']

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO quiz_questions
            (category, level, question, option1, option2, option3, option4, correct_answer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (category, level, question, option1, option2, option3, option4, correct))

        conn.commit()
        conn.close()

        message = "✅ Question added successfully!"

    return render_template('create_quiz.html', msg=message)

@app.route("/start_quiz", methods=["GET", "POST"])
def start_quiz():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ✅ Fetch random questions (like video)
    cursor.execute("""
        SELECT * FROM quiz_questions
        ORDER BY RANDOM()
        LIMIT 5
    """)

    questions = cursor.fetchall()

    # ✅ When student submits
    if request.method == "POST":

        score = 0

        for q in questions:
            selected = request.form.get(str(q["id"]))

            if selected == q["correct_answer"]:
                score += 1

        return render_template(
            "quiz_result.html",
            score=score,
            total=len(questions)
        )

    return render_template(
        "quiz.html",
        questions=questions,
        category="Ecoplay",
        level="Random"
    )

import random

@app.route("/play_quiz/<int:qno>", methods=["GET", "POST"])
def play_quiz(qno):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM quiz_questions
        ORDER BY id ASC
        LIMIT 10
    """)
    questions = cursor.fetchall()

    total = len(questions)

    # ✅ Reset score at start
    if qno == 0:
        session["score"] = 0

    # ✅ Quiz finished
    if qno >= total:
        score = session.get("score", 0)
        session["score"] = 0
        return render_template("quiz_result.html", score=score, total=total)

    current_q = questions[qno]

    # ✅ POST BLOCK (ONLY HERE selected exists)
    if request.method == "POST":

        selected = request.form.get("answer")

        # ✅ DEBUG (INSIDE POST ONLY)
        print("Selected:", selected)
        print("Correct:", current_q["correct_answer"])

        # ✅ SAFE CHECK
        if selected:
            selected = selected.strip()
            correct = current_q["correct_answer"].strip()

            if selected == correct:
                session["score"] += 1

        return redirect(f"/play_quiz/{qno + 1}")

    return render_template(
        "play_quiz.html",
        q=current_q,
        qno=qno,
        total=total
    )

@app.route("/delete-challenge/<int:id>")
def delete_challenge(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM challenges WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/challenges")

@app.route("/challenges")
def challenges():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM challenges ORDER BY id DESC")
    challenges = cursor.fetchall()

    conn.close()

    return render_template("challenges.html", challenges=challenges)

@app.route('/leaderboard')
def leaderboard():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # Fetch students ordered by points
    cur.execute("""
        SELECT name, points
        FROM users
        ORDER BY points DESC
    """)

    students = cur.fetchall()
    conn.close()

    return render_template('leaderboard.html', students=students)

@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/add-account")
def add_account():
    return render_template("signup.html")  # reuse signup page

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/student_activities")
def student_activities():

    # ✅ Only students allowed
    if session.get("role") != "student":
        return "Access Denied"

    conn = get_db()
    activities = conn.execute("SELECT * FROM activities").fetchall()
    conn.close()

    return render_template("student_activities.html", activities=activities)


if __name__ == "__main__":
    app.run(debug=True)