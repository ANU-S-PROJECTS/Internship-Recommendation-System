import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import hmac
import os
import re
import plotly.express as px

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="InternMatch | AI Internship Portal",
    page_icon="🎓",
    layout="wide"
)


# ==================================================
# PROFESSIONAL FRONTEND DESIGN
# ==================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

.stApp {
    background: linear-gradient(135deg, #080e20, #171c3e, #30205b);
    color: white;
    font-family: 'Poppins', sans-serif;
}

.block-container {
    max-width: 1250px;
    padding-top: 2rem;
}

h1 {
    color: #c5a6ff !important;
    font-weight: 800 !important;
}

h2, h3 {
    color: #e8ddff !important;
}

p, label {
    color: #e2e5f5;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #11162d, #231b46);
}

.stButton > button,
.stFormSubmitButton > button,
.stDownloadButton > button {
    background: linear-gradient(90deg, #7559ff, #a65cff);
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 600;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: #967dff;
    color: white;
}

div[data-testid="stMetric"] {
    background: rgba(117, 89, 255, 0.15);
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #574b86;
}

div[data-testid="stForm"] {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid #574b86;
    padding: 20px;
    border-radius: 15px;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# DATABASE
# ==================================================

def get_connection():
    return sqlite3.connect("internmatch.db")


def create_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            salt TEXT NOT NULL,
            college TEXT,
            department TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_email TEXT NOT NULL,
            internship_id INTEGER NOT NULL,
            UNIQUE(student_email, internship_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_email TEXT NOT NULL,
            internship_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Applied',
            applied_date TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_email, internship_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            skills TEXT NOT NULL,
            location TEXT NOT NULL,
            stipend INTEGER DEFAULT 0,
            description TEXT,
            submitted_by TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    conn.commit()
    conn.close()


create_database()


# ==================================================
# PASSWORD SECURITY
# ==================================================

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200000
    )

    return hashed.hex(), salt.hex()


def verify_password(password, stored_hash, stored_salt):
    try:
        salt = bytes.fromhex(stored_salt)
        new_hash, _ = hash_password(password, salt)
        return hmac.compare_digest(new_hash, stored_hash)
    except (ValueError, TypeError):
        return False


# ==================================================
# STUDENT REGISTRATION AND LOGIN
# ==================================================

def register_student(name, email, password, college, department):
    password_hash, salt = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO students
            (name, email, password, salt, college, department)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            email,
            password_hash,
            salt,
            college,
            department
        ))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def login_student(email, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, password, salt
        FROM students
        WHERE email = ?
    """, (email,))

    student = cursor.fetchone()
    conn.close()

    if student:
        name, stored_hash, stored_salt = student

        if verify_password(password, stored_hash, stored_salt):
            return name

    return None


# ==================================================
# SAMPLE INTERNSHIP DATA - 15 COMPANIES
# ==================================================

internships = [
    {"Company": "Zoho", "Role": "Python Developer Intern", "Skills": "Python SQL Django Flask", "Location": "Chennai", "Stipend": 12000},
    {"Company": "TCS", "Role": "Data Science Intern", "Skills": "Python SQL Machine Learning Pandas", "Location": "Chennai", "Stipend": 15000},
    {"Company": "Infosys", "Role": "Artificial Intelligence Intern", "Skills": "Python AI Deep Learning TensorFlow", "Location": "Bengaluru", "Stipend": 14000},
    {"Company": "KGiSL", "Role": "Software Developer Intern", "Skills": "Java Python SQL", "Location": "Coimbatore", "Stipend": 10000},
    {"Company": "CUSTQ Software Series", "Role": "Full Stack Developer Intern", "Skills": "HTML CSS JavaScript React Node", "Location": "Coimbatore", "Stipend": 12000},
    {"Company": "VMV Systems", "Role": "Web Developer Intern", "Skills": "HTML CSS JavaScript Python", "Location": "Salem", "Stipend": 9000},
    {"Company": "AI Technologies", "Role": "Machine Learning Intern", "Skills": "Python Machine Learning Scikit Learn", "Location": "Erode", "Stipend": 10000},
    {"Company": "Cloud Solutions", "Role": "Cloud Computing Intern", "Skills": "AWS Azure Linux Cloud", "Location": "Tiruppur", "Stipend": 11000},
    {"Company": "Future AI Labs", "Role": "Generative AI Intern", "Skills": "Python Generative AI LLM LangChain", "Location": "Remote", "Stipend": 15000},
    {"Company": "WebNova", "Role": "Frontend Developer Intern", "Skills": "HTML CSS JavaScript React", "Location": "Remote", "Stipend": 8000},
    {"Company": "CyberTech", "Role": "Cybersecurity Intern", "Skills": "Cybersecurity Networking Linux", "Location": "Chennai", "Stipend": 12000},
    {"Company": "DataVision", "Role": "Data Analyst Intern", "Skills": "Python Excel SQL Power BI", "Location": "Bengaluru", "Stipend": 13000},
    {"Company": "Robotix Labs", "Role": "Robotics Intern", "Skills": "Python Robotics Arduino IoT", "Location": "Salem", "Stipend": 9000},
    {"Company": "Design Studio", "Role": "UI UX Design Intern", "Skills": "Figma UI UX Design", "Location": "Coimbatore", "Stipend": 8000},
    {"Company": "AppTech", "Role": "Mobile App Developer Intern", "Skills": "Flutter Dart Firebase", "Location": "Erode", "Stipend": 10000}
]


# ==================================================
# ADD INTERNSHIP
# ==================================================

def add_new_internship(company, role, skills, location, stipend, description, email):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO user_internships
        (company, role, skills, location, stipend, description, submitted_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
    """, (
        company,
        role,
        skills,
        location,
        int(stipend),
        description,
        email
    ))

    conn.commit()
    conn.close()


def get_user_internships():
    conn = get_connection()

    result = pd.read_sql_query(
        "SELECT * FROM user_internships ORDER BY id DESC",
        conn
    )

    conn.close()
    return result


def update_internship_approval(internship_id, status):
    if status not in ["Approved", "Rejected"]:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE user_internships
        SET status = ?
        WHERE id = ?
    """, (status, internship_id))

    conn.commit()
    conn.close()


# ==================================================
# LOAD APPROVED INTERNSHIPS
# ==================================================

def load_internship_data():
    sample_data = pd.DataFrame(internships)

    sample_data.insert(
        0,
        "Internship ID",
        range(1, len(sample_data) + 1)
    )

    conn = get_connection()

    approved = pd.read_sql_query("""
        SELECT
            id,
            company AS Company,
            role AS Role,
            skills AS Skills,
            location AS Location,
            stipend AS Stipend
        FROM user_internships
        WHERE status = 'Approved'
    """, conn)

    conn.close()

    if not approved.empty:
        approved["Internship ID"] = approved["id"] + len(sample_data)

        approved = approved[
            ["Internship ID", "Company", "Role", "Skills", "Location", "Stipend"]
        ]

        sample_data = pd.concat(
            [sample_data, approved],
            ignore_index=True
        )

    return sample_data


data = load_internship_data()


# ==================================================
# SESSION STATE
# ==================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "student_name" not in st.session_state:
    st.session_state.student_name = ""

if "student_email" not in st.session_state:
    st.session_state.student_email = ""

if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

if "recommended_skills" not in st.session_state:
    st.session_state.recommended_skills = ""


# ==================================================
# SAVE INTERNSHIP
# ==================================================

def save_internship(email, internship_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO saved_internships
        (student_email, internship_id)
        VALUES (?, ?)
    """, (email, int(internship_id)))

    added = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return added


def get_saved_internships(email):
    conn = get_connection()

    saved = pd.read_sql_query("""
        SELECT internship_id
        FROM saved_internships
        WHERE student_email = ?
    """, conn, params=(email,))

    conn.close()
    return saved


# ==================================================
# APPLICATION TRACKING
# ==================================================

def apply_internship(email, internship_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO applications
        (student_email, internship_id, status)
        VALUES (?, ?, 'Applied')
    """, (email, int(internship_id)))

    added = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return added


def get_applications(email):
    conn = get_connection()

    result = pd.read_sql_query("""
        SELECT internship_id, status, applied_date
        FROM applications
        WHERE student_email = ?
        ORDER BY applied_date DESC
    """, conn, params=(email,))

    conn.close()
    return result


def update_application_status(email, internship_id, status):
    if status not in ["Applied", "Shortlisted", "Selected", "Rejected"]:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE applications
        SET status = ?
        WHERE student_email = ?
        AND internship_id = ?
    """, (status, email, int(internship_id)))

    updated = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return updated


# ==================================================
# SKILL GAP ANALYSIS
# ==================================================

KNOWN_SKILLS = [
    "Machine Learning", "Deep Learning", "Generative AI",
    "Power BI", "Scikit Learn", "UI UX", "JavaScript",
    "TensorFlow", "LangChain", "Firebase", "Django",
    "Flask", "Python", "SQL", "Pandas", "React",
    "Node", "HTML", "CSS", "Java", "AWS", "Azure",
    "Linux", "Cloud", "Cybersecurity", "Networking",
    "Robotics", "Arduino", "IoT", "Excel", "Figma",
    "Design", "Flutter", "Dart", "LLM", "AI"
]


def extract_skills(text):
    remaining = str(text).lower()
    found = []

    for skill in sorted(KNOWN_SKILLS, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"

        if re.search(pattern, remaining):
            found.append(skill.lower())
            remaining = re.sub(pattern, " ", remaining)

    return list(dict.fromkeys(found))


def analyze_skill_gap(student_skills, required_skills):
    student = set(extract_skills(student_skills))
    required = extract_skills(required_skills)

    matching = [skill for skill in required if skill in student]
    missing = [skill for skill in required if skill not in student]

    percentage = (
        len(matching) / len(required) * 100
        if required else 0
    )

    return matching, missing, percentage


# ==================================================
# AI RECOMMENDATION ENGINE
# ==================================================

def recommend_internships(skills, interest, location, minimum_stipend):
    profile = skills + " " + interest

    internship_text = (
        data["Role"].fillna("") + " " + data["Skills"].fillna("")
    ).tolist()

    vectorizer = TfidfVectorizer(stop_words="english")

    vectors = vectorizer.fit_transform(
        [profile] + internship_text
    )

    similarity = cosine_similarity(
        vectors[0:1],
        vectors[1:]
    ).flatten()

    results = data.copy()
    results["Match Score"] = similarity * 100

    if location != "Any":
        results = results[
            results["Location"] == location
        ].copy()

    results = results[
        results["Stipend"] >= minimum_stipend
    ].copy()

    results = results[
        results["Match Score"] > 0
    ].copy()

    return results.sort_values(
        "Match Score",
        ascending=False
    ).head(10)


# ==================================================
# LOGIN AND REGISTRATION
# ==================================================

if not st.session_state.logged_in:

    st.title("🎓 InternMatch")

    st.markdown("### Your Career. Your Future.")

    st.write("AI-Powered Internship Recommendation System")

    st.divider()

    login_tab, register_tab = st.tabs([
        "🔐 Student Login",
        "📝 Student Registration"
    ])

    with login_tab:
        st.subheader("Welcome Back 👋")

        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

        if login_button:
            email = email.strip().lower()
            student_name = login_student(email, password)

            if student_name:
                st.session_state.logged_in = True
                st.session_state.student_name = student_name
                st.session_state.student_email = email
                st.session_state.recommendations = None
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with register_tab:
        st.subheader("Create Student Account")

        with st.form("register_form"):
            name = st.text_input("Full Name")
            reg_email = st.text_input("Email Address", key="reg_email")
            college = st.text_input("College Name")

            department = st.selectbox(
                "Department",
                [
                    "Artificial Intelligence and Data Science",
                    "Computer Science",
                    "Information Technology",
                    "Electronics and Communication",
                    "Other"
                ]
            )

            reg_password = st.text_input(
                "Create Password",
                type="password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            register_button = st.form_submit_button("Create Account")

        if register_button:
            reg_email = reg_email.strip().lower()

            if not name.strip() or not reg_email or not college.strip():
                st.warning("Please fill all required fields.")

            elif "@" not in reg_email or "." not in reg_email.split("@")[-1]:
                st.warning("Enter a valid email address.")

            elif len(reg_password) < 8:
                st.warning("Password must have at least 8 characters.")

            elif reg_password != confirm_password:
                st.error("Passwords do not match.")

            else:
                success = register_student(
                    name.strip(),
                    reg_email,
                    reg_password,
                    college.strip(),
                    department
                )

                if success:
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Email already registered.")


# ==================================================
# MAIN WEBSITE
# ==================================================

else:

    st.title("🎓 InternMatch Dashboard")

    st.success(
        f"Welcome, {st.session_state.student_name}!"
    )

    st.caption(
        "Logged in as: " + st.session_state.student_email
    )

    # ADMIN EMAIL FROM STREAMLIT SECRETS
    import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import hmac
import os
import re
import plotly.express as px

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="InternMatch | AI Internship Portal",
    page_icon="🎓",
    layout="wide"
)


# ==================================================
# PROFESSIONAL FRONTEND DESIGN
# ==================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

.stApp {
    background: linear-gradient(135deg, #080e20, #171c3e, #30205b);
    color: white;
    font-family: 'Poppins', sans-serif;
}

.block-container {
    max-width: 1250px;
    padding-top: 2rem;
}

h1 {
    color: #c5a6ff !important;
    font-weight: 800 !important;
}

h2, h3 {
    color: #e8ddff !important;
}

p, label {
    color: #e2e5f5;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #11162d, #231b46);
}

.stButton > button,
.stFormSubmitButton > button,
.stDownloadButton > button {
    background: linear-gradient(90deg, #7559ff, #a65cff);
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 600;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: #967dff;
    color: white;
}

div[data-testid="stMetric"] {
    background: rgba(117, 89, 255, 0.15);
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #574b86;
}

div[data-testid="stForm"] {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid #574b86;
    padding: 20px;
    border-radius: 15px;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# DATABASE
# ==================================================

def get_connection():
    return sqlite3.connect("internmatch.db")


def create_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            salt TEXT NOT NULL,
            college TEXT,
            department TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_email TEXT NOT NULL,
            internship_id INTEGER NOT NULL,
            UNIQUE(student_email, internship_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_email TEXT NOT NULL,
            internship_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Applied',
            applied_date TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_email, internship_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            skills TEXT NOT NULL,
            location TEXT NOT NULL,
            stipend INTEGER DEFAULT 0,
            description TEXT,
            submitted_by TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    conn.commit()
    conn.close()


create_database()


# ==================================================
# PASSWORD SECURITY
# ==================================================

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200000
    )

    return hashed.hex(), salt.hex()


def verify_password(password, stored_hash, stored_salt):
    try:
        salt = bytes.fromhex(stored_salt)
        new_hash, _ = hash_password(password, salt)
        return hmac.compare_digest(new_hash, stored_hash)
    except (ValueError, TypeError):
        return False


# ==================================================
# STUDENT REGISTRATION AND LOGIN
# ==================================================

def register_student(name, email, password, college, department):
    password_hash, salt = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO students
            (name, email, password, salt, college, department)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            email,
            password_hash,
            salt,
            college,
            department
        ))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def login_student(email, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, password, salt
        FROM students
        WHERE email = ?
    """, (email,))

    student = cursor.fetchone()
    conn.close()

    if student:
        name, stored_hash, stored_salt = student

        if verify_password(password, stored_hash, stored_salt):
            return name

    return None


# ==================================================
# SAMPLE INTERNSHIP DATA - 15 COMPANIES
# ==================================================

internships = [
    {"Company": "Zoho", "Role": "Python Developer Intern", "Skills": "Python SQL Django Flask", "Location": "Chennai", "Stipend": 12000},
    {"Company": "TCS", "Role": "Data Science Intern", "Skills": "Python SQL Machine Learning Pandas", "Location": "Chennai", "Stipend": 15000},
    {"Company": "Infosys", "Role": "Artificial Intelligence Intern", "Skills": "Python AI Deep Learning TensorFlow", "Location": "Bengaluru", "Stipend": 14000},
    {"Company": "KGiSL", "Role": "Software Developer Intern", "Skills": "Java Python SQL", "Location": "Coimbatore", "Stipend": 10000},
    {"Company": "CUSTQ Software Series", "Role": "Full Stack Developer Intern", "Skills": "HTML CSS JavaScript React Node", "Location": "Coimbatore", "Stipend": 12000},
    {"Company": "VMV Systems", "Role": "Web Developer Intern", "Skills": "HTML CSS JavaScript Python", "Location": "Salem", "Stipend": 9000},
    {"Company": "AI Technologies", "Role": "Machine Learning Intern", "Skills": "Python Machine Learning Scikit Learn", "Location": "Erode", "Stipend": 10000},
    {"Company": "Cloud Solutions", "Role": "Cloud Computing Intern", "Skills": "AWS Azure Linux Cloud", "Location": "Tiruppur", "Stipend": 11000},
    {"Company": "Future AI Labs", "Role": "Generative AI Intern", "Skills": "Python Generative AI LLM LangChain", "Location": "Remote", "Stipend": 15000},
    {"Company": "WebNova", "Role": "Frontend Developer Intern", "Skills": "HTML CSS JavaScript React", "Location": "Remote", "Stipend": 8000},
    {"Company": "CyberTech", "Role": "Cybersecurity Intern", "Skills": "Cybersecurity Networking Linux", "Location": "Chennai", "Stipend": 12000},
    {"Company": "DataVision", "Role": "Data Analyst Intern", "Skills": "Python Excel SQL Power BI", "Location": "Bengaluru", "Stipend": 13000},
    {"Company": "Robotix Labs", "Role": "Robotics Intern", "Skills": "Python Robotics Arduino IoT", "Location": "Salem", "Stipend": 9000},
    {"Company": "Design Studio", "Role": "UI UX Design Intern", "Skills": "Figma UI UX Design", "Location": "Coimbatore", "Stipend": 8000},
    {"Company": "AppTech", "Role": "Mobile App Developer Intern", "Skills": "Flutter Dart Firebase", "Location": "Erode", "Stipend": 10000}
]


# ==================================================
# ADD INTERNSHIP
# ==================================================

def add_new_internship(company, role, skills, location, stipend, description, email):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO user_internships
        (company, role, skills, location, stipend, description, submitted_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
    """, (
        company,
        role,
        skills,
        location,
        int(stipend),
        description,
        email
    ))

    conn.commit()
    conn.close()


def get_user_internships():
    conn = get_connection()

    result = pd.read_sql_query(
        "SELECT * FROM user_internships ORDER BY id DESC",
        conn
    )

    conn.close()
    return result


def update_internship_approval(internship_id, status):
    if status not in ["Approved", "Rejected"]:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE user_internships
        SET status = ?
        WHERE id = ?
    """, (status, internship_id))

    conn.commit()
    conn.close()


# ==================================================
# LOAD APPROVED INTERNSHIPS
# ==================================================

def load_internship_data():
    sample_data = pd.DataFrame(internships)

    sample_data.insert(
        0,
        "Internship ID",
        range(1, len(sample_data) + 1)
    )

    conn = get_connection()

    approved = pd.read_sql_query("""
        SELECT
            id,
            company AS Company,
            role AS Role,
            skills AS Skills,
            location AS Location,
            stipend AS Stipend
        FROM user_internships
        WHERE status = 'Approved'
    """, conn)

    conn.close()

    if not approved.empty:
        approved["Internship ID"] = approved["id"] + len(sample_data)

        approved = approved[
            ["Internship ID", "Company", "Role", "Skills", "Location", "Stipend"]
        ]

        sample_data = pd.concat(
            [sample_data, approved],
            ignore_index=True
        )

    return sample_data


data = load_internship_data()


# ==================================================
# SESSION STATE
# ==================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "student_name" not in st.session_state:
    st.session_state.student_name = ""

if "student_email" not in st.session_state:
    st.session_state.student_email = ""

if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

if "recommended_skills" not in st.session_state:
    st.session_state.recommended_skills = ""


# ==================================================
# SAVE INTERNSHIP
# ==================================================

def save_internship(email, internship_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO saved_internships
        (student_email, internship_id)
        VALUES (?, ?)
    """, (email, int(internship_id)))

    added = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return added


def get_saved_internships(email):
    conn = get_connection()

    saved = pd.read_sql_query("""
        SELECT internship_id
        FROM saved_internships
        WHERE student_email = ?
    """, conn, params=(email,))

    conn.close()
    return saved


# ==================================================
# APPLICATION TRACKING
# ==================================================

def apply_internship(email, internship_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO applications
        (student_email, internship_id, status)
        VALUES (?, ?, 'Applied')
    """, (email, int(internship_id)))

    added = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return added


def get_applications(email):
    conn = get_connection()

    result = pd.read_sql_query("""
        SELECT internship_id, status, applied_date
        FROM applications
        WHERE student_email = ?
        ORDER BY applied_date DESC
    """, conn, params=(email,))

    conn.close()
    return result


def update_application_status(email, internship_id, status):
    if status not in ["Applied", "Shortlisted", "Selected", "Rejected"]:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE applications
        SET status = ?
        WHERE student_email = ?
        AND internship_id = ?
    """, (status, email, int(internship_id)))

    updated = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return updated


# ==================================================
# SKILL GAP ANALYSIS
# ==================================================

KNOWN_SKILLS = [
    "Machine Learning", "Deep Learning", "Generative AI",
    "Power BI", "Scikit Learn", "UI UX", "JavaScript",
    "TensorFlow", "LangChain", "Firebase", "Django",
    "Flask", "Python", "SQL", "Pandas", "React",
    "Node", "HTML", "CSS", "Java", "AWS", "Azure",
    "Linux", "Cloud", "Cybersecurity", "Networking",
    "Robotics", "Arduino", "IoT", "Excel", "Figma",
    "Design", "Flutter", "Dart", "LLM", "AI"
]


def extract_skills(text):
    remaining = str(text).lower()
    found = []

    for skill in sorted(KNOWN_SKILLS, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"

        if re.search(pattern, remaining):
            found.append(skill.lower())
            remaining = re.sub(pattern, " ", remaining)

    return list(dict.fromkeys(found))


def analyze_skill_gap(student_skills, required_skills):
    student = set(extract_skills(student_skills))
    required = extract_skills(required_skills)

    matching = [skill for skill in required if skill in student]
    missing = [skill for skill in required if skill not in student]

    percentage = (
        len(matching) / len(required) * 100
        if required else 0
    )

    return matching, missing, percentage


# ==================================================
# AI RECOMMENDATION ENGINE
# ==================================================

def recommend_internships(skills, interest, location, minimum_stipend):
    profile = skills + " " + interest

    internship_text = (
        data["Role"].fillna("") + " " + data["Skills"].fillna("")
    ).tolist()

    vectorizer = TfidfVectorizer(stop_words="english")

    vectors = vectorizer.fit_transform(
        [profile] + internship_text
    )

    similarity = cosine_similarity(
        vectors[0:1],
        vectors[1:]
    ).flatten()

    results = data.copy()
    results["Match Score"] = similarity * 100

    if location != "Any":
        results = results[
            results["Location"] == location
        ].copy()

    results = results[
        results["Stipend"] >= minimum_stipend
    ].copy()

    results = results[
        results["Match Score"] > 0
    ].copy()

    return results.sort_values(
        "Match Score",
        ascending=False
    ).head(10)


# ==================================================
# LOGIN AND REGISTRATION
# ==================================================

if not st.session_state.logged_in:

    st.title("🎓 InternMatch")

    st.markdown("### Your Career. Your Future.")

    st.write("AI-Powered Internship Recommendation System")

    st.divider()

    login_tab, register_tab = st.tabs([
        "🔐 Student Login",
        "📝 Student Registration"
    ])

    with login_tab:
        st.subheader("Welcome Back 👋")

        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

        if login_button:
            email = email.strip().lower()
            student_name = login_student(email, password)

            if student_name:
                st.session_state.logged_in = True
                st.session_state.student_name = student_name
                st.session_state.student_email = email
                st.session_state.recommendations = None
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with register_tab:
        st.subheader("Create Student Account")

        with st.form("register_form"):
            name = st.text_input("Full Name")
            reg_email = st.text_input("Email Address", key="reg_email")
            college = st.text_input("College Name")

            department = st.selectbox(
                "Department",
                [
                    "Artificial Intelligence and Data Science",
                    "Computer Science",
                    "Information Technology",
                    "Electronics and Communication",
                    "Other"
                ]
            )

            reg_password = st.text_input(
                "Create Password",
                type="password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            register_button = st.form_submit_button("Create Account")

        if register_button:
            reg_email = reg_email.strip().lower()

            if not name.strip() or not reg_email or not college.strip():
                st.warning("Please fill all required fields.")

            elif "@" not in reg_email or "." not in reg_email.split("@")[-1]:
                st.warning("Enter a valid email address.")

            elif len(reg_password) < 8:
                st.warning("Password must have at least 8 characters.")

            elif reg_password != confirm_password:
                st.error("Passwords do not match.")

            else:
                success = register_student(
                    name.strip(),
                    reg_email,
                    reg_password,
                    college.strip(),
                    department
                )

                if success:
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Email already registered.")


# ==================================================
# MAIN WEBSITE
# ==================================================

else:

    st.title("🎓 InternMatch Dashboard")

    st.success(
        f"Welcome, {st.session_state.student_name}!"
    )

    st.caption(
        "Logged in as: " + st.session_state.student_email
    )

    # ADMIN EMAIL FROM STREAMLIT SECRETS
    admin_email = st.secrets.get("ADMIN_EMAIL", "").strip().lower()

    is_admin = (
        bool(admin_email)
        and st.session_state.student_email == admin_email
    )

    # SIDEBAR BRANDING
    st.sidebar.markdown("""
    <div style="text-align:center; padding:20px 10px;">
        <h2 style="color:#c5a6ff;">🎓 InternMatch</h2>
        <p style="color:#cfc5e8;">AI-Powered Internship Portal</p>
    </div>
    """, unsafe_allow_html=True)

    navigation = [
        "🏠 Dashboard",
        "🎯 Find Internships",
        "➕ Add Internship",
        "💾 Saved Internships",
        "👤 My Profile",
        "📝 My Applications",
        "📊 Analytics Dashboard"
    ]

    if is_admin:
        navigation.append("🛡️ Admin Approval")

    page = st.sidebar.radio(
    "Navigation",
    navigation,
    key="main_navigation"
)


    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.student_name = ""
        st.session_state.student_email = ""
        st.session_state.recommendations = None
        st.session_state.recommended_skills = ""
        st.rerun()

    # ==================================================
    # DASHBOARD
    # ==================================================

    if page == "🏠 Dashboard":

        st.markdown("""
        <div style="
            background:linear-gradient(90deg,#6550db,#a35cff);
            padding:30px;
            border-radius:20px;
            margin-bottom:25px;
        ">
            <h2 style="color:white !important;">
                🚀 Discover Your Dream Internship
            </h2>
            <p style="color:#f3edff;">
                Find your perfect internship with AI-powered recommendations.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.header("📊 Internship Overview")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Internships", len(data))

        with col2:
            st.metric("Companies", data["Company"].nunique())

        with col3:
            st.metric("Locations", data["Location"].nunique())

        st.divider()

        st.subheader("💼 Explore Internship Opportunities")

        search = st.text_input("Search Company or Internship Role")

        filtered_data = data.copy()

        if search.strip():
            mask = (
                filtered_data["Company"].str.contains(
                    search, case=False, regex=False
                )
                |
                filtered_data["Role"].str.contains(
                    search, case=False, regex=False
                )
            )

            filtered_data = filtered_data[mask]

        st.dataframe(
            filtered_data,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Initial 15 internships are sample data for academic demonstration."
        )

    # ==================================================
    # ADD INTERNSHIP
    # ==================================================

    elif page == "➕ Add Internship":

        st.title("➕ Add New Internship")

        st.write("Share internship opportunities with other students.")

        with st.form("add_internship_form"):

            company = st.text_input(
                "🏢 Company Name",
                placeholder="Example: Zoho"
            )

            role = st.text_input(
                "💼 Internship Role",
                placeholder="Example: Python Developer"
            )

            skills = st.text_input(
                "🛠 Required Skills",
                placeholder="Python, SQL, Machine Learning"
            )

            location = st.selectbox(
                "📍 Location",
                [
                    "Chennai",
                    "Bengaluru",
                    "Coimbatore",
                    "Salem",
                    "Erode",
                    "Tiruppur",
                    "Remote"
                ]
            )

            stipend = st.number_input(
                "💰 Monthly Stipend (₹)",
                min_value=0,
                step=1000
            )

            description = st.text_area(
                "📝 Internship Description"
            )

            submit = st.form_submit_button(
                "➕ Submit Internship",
                use_container_width=True
            )

        if submit:

            if not company.strip() or not role.strip() or not skills.strip():
                st.error("Please fill Company Name, Role and Skills.")

            else:
                add_new_internship(
                    company.strip(),
                    role.strip(),
                    skills.strip(),
                    location,
                    stipend,
                    description.strip(),
                    st.session_state.student_email
                )

                st.success(
                    "🎉 Internship submitted successfully!"
                )

                st.info(
                    "Your internship is waiting for admin approval."
                )

        st.divider()
        st.subheader("📋 My Submitted Internships")

        user_data = get_user_internships()

        my_submissions = user_data[
            user_data["submitted_by"] == st.session_state.student_email
        ]

        if not my_submissions.empty:
            st.dataframe(
                my_submissions[
                    ["company", "role", "location", "stipend", "status"]
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("You haven't submitted any internships yet.")

    # ==================================================
    # FIND INTERNSHIPS
    # ==================================================

    elif page == "🎯 Find Internships":

        st.header("🎯 AI Internship Recommendation")

        st.write(
            "Enter your skills and preferences to find matching internships."
        )

        col1, col2 = st.columns(2)

        with col1:
            skills = st.text_input(
                "Your Technical Skills",
                placeholder="Python, SQL, Machine Learning"
            )

            interest = st.selectbox(
                "Career Interest",
                [
                    "Data Science",
                    "Artificial Intelligence",
                    "Machine Learning",
                    "Deep Learning",
                    "Generative AI",
                    "Python Development",
                    "Java Development",
                    "Web Development",
                    "Full Stack Development",
                    "Frontend Development",
                    "Backend Development",
                    "Cybersecurity",
                    "Cloud Computing",
                    "Data Analytics",
                    "Business Analytics",
                    "Robotics",
                    "Internet of Things",
                    "UI UX Design",
                    "Mobile App Development",
                    "Software Development",
                    "DevOps",
                    "Database Management"
                ]
            )

        with col2:
            location = st.selectbox(
                "Preferred Location",
                [
                    "Any",
                    "Chennai",
                    "Bengaluru",
                    "Coimbatore",
                    "Salem",
                    "Erode",
                    "Tiruppur",
                    "Remote"
                ]
            )

            stipend = st.selectbox(
                "Minimum Monthly Stipend",
                [0, 5000, 8000, 10000, 12000, 15000],
                format_func=lambda x: (
                    "Any Stipend" if x == 0 else f"₹{x:,}"
                )
            )

        if st.button("✨ Recommend Internships"):

            if not skills.strip():
                st.warning("Please enter your technical skills.")

            else:
                results = recommend_internships(
                    skills,
                    interest,
                    location,
                    stipend
                )

                st.session_state.recommendations = results
                st.session_state.recommended_skills = skills

        if st.session_state.recommendations is not None:

            results = st.session_state.recommendations

            st.divider()
            st.subheader("🏆 Recommended Internships")

            if results.empty:
                st.warning(
                    "No matching internships found. "
                    "Try changing your skills or filters."
                )

            else:
                st.success(
                    f"Found {len(results)} matching internships!"
                )

                for _, row in results.iterrows():

                    with st.container(border=True):

                        st.subheader("💼 " + row["Role"])

                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**Company:**", row["Company"])
                            st.write("**Required Skills:**", row["Skills"])

                        with col2:
                            st.write("**Location:**", row["Location"])
                            st.write(
                                "**Monthly Stipend:**",
                                f"₹{int(row['Stipend']):,}"
                            )

                        score = float(row["Match Score"])

                        st.write(
                            f"**AI Match Score: {score:.1f}%**"
                        )

                        st.progress(
                            min(max(score / 100, 0.0), 1.0)
                        )

                        st.markdown("### 🧠 Skill Gap Analysis")

                        matching, missing, skill_percentage = (
                            analyze_skill_gap(
                                st.session_state.recommended_skills,
                                row["Skills"]
                            )
                        )

                        st.write(
                            f"**Skill Match: {skill_percentage:.1f}%**"
                        )

                        st.progress(
                            min(max(skill_percentage / 100, 0.0), 1.0)
                        )

                        if matching:
                            st.success(
                                "✅ Matching Skills: "
                                + ", ".join(
                                    skill.title() for skill in matching
                                )
                            )

                        if missing:
                            st.warning(
                                "❌ Missing Skills: "
                                + ", ".join(
                                    skill.title() for skill in missing
                                )
                            )

                            st.info(
                                "📚 Skills to Learn: "
                                + ", ".join(
                                    skill.title() for skill in missing
                                )
                            )

                        if not missing:
                            st.success(
                                "🎉 You have all listed required skills!"
                            )

                        internship_id = int(row["Internship ID"])

                        button_col1, button_col2 = st.columns(2)

                        with button_col1:
                            if st.button(
                                "💾 Save Internship",
                                key=f"save_{internship_id}"
                            ):
                                added = save_internship(
                                    st.session_state.student_email,
                                    internship_id
                                )

                                if added:
                                    st.success("Internship saved!")
                                else:
                                    st.info("Already saved.")

                        with button_col2:
                            if st.button(
                                "📝 Add to Application Tracker",
                                key=f"apply_{internship_id}"
                            ):
                                added = apply_internship(
                                    st.session_state.student_email,
                                    internship_id
                                )

                                if added:
                                    st.success("Added to tracker!")
                                else:
                                    st.info("Already tracked.")

                csv = results.to_csv(index=False).encode("utf-8")

                st.download_button(
                    "📥 Download Recommendations",
                    data=csv,
                    file_name="recommendations.csv",
                    mime="text/csv"
                )

                st.caption(
                    "AI match scores are text similarity scores, "
                    "not hiring probabilities."
                )

    # ==================================================
    # SAVED INTERNSHIPS
    # ==================================================

    elif page == "💾 Saved Internships":

        st.header("💾 My Saved Internships")

        saved = get_saved_internships(
            st.session_state.student_email
        )

        if saved.empty:
            st.info("You haven't saved any internships yet.")

        else:
            saved_data = data[
                data["Internship ID"].isin(saved["internship_id"])
            ]

            st.dataframe(
                saved_data,
                use_container_width=True,
                hide_index=True
            )

    # ==================================================
    # STUDENT PROFILE
    # ==================================================

    elif page == "👤 My Profile":

        st.header("👤 My Student Profile")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, email, college, department
            FROM students
            WHERE email = ?
        """, (st.session_state.student_email,))

        student = cursor.fetchone()
        conn.close()

        if student:

            name, email, college, department = student

            st.subheader("🎓 Student Information")

            st.write("**Full Name:**", name)
            st.write("**Email Address:**", email)
            st.write("**College:**", college)
            st.write("**Department:**", department)

            st.divider()
            st.subheader("✏️ Update Profile")

            with st.form("update_profile"):

                new_name = st.text_input(
                    "Full Name",
                    value=name
                )

                new_college = st.text_input(
                    "College Name",
                    value=college or ""
                )

                new_department = st.text_input(
                    "Department",
                    value=department or ""
                )

                update_button = st.form_submit_button(
                    "Save Changes"
                )

            if update_button:

                if not new_name.strip():
                    st.warning("Name cannot be empty.")

                else:
                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE students
                        SET name = ?, college = ?, department = ?
                        WHERE email = ?
                    """, (
                        new_name.strip(),
                        new_college.strip(),
                        new_department.strip(),
                        st.session_state.student_email
                    ))

                    conn.commit()
                    conn.close()

                    st.session_state.student_name = new_name.strip()

                    st.success("Profile updated!")
                    st.rerun()

    # ==================================================
    # APPLICATION TRACKING
    # ==================================================

    elif page == "📝 My Applications":

        st.header("📝 My Internship Applications")

        applications = get_applications(
            st.session_state.student_email
        )

        if applications.empty:
            st.info(
                "You haven't added any internships "
                "to your application tracker yet."
            )

        else:
            application_data = applications.merge(
                data,
                left_on="internship_id",
                right_on="Internship ID",
                how="left"
            )

            st.subheader("📊 Application Overview")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Applications",
                    len(application_data)
                )

            with col2:
                st.metric(
                    "Applied",
                    int((application_data["status"] == "Applied").sum())
                )

            with col3:
                st.metric(
                    "Shortlisted",
                    int((application_data["status"] == "Shortlisted").sum())
                )

            with col4:
                st.metric(
                    "Selected",
                    int((application_data["status"] == "Selected").sum())
                )

            st.divider()
            st.subheader("💼 Application Details")

            status_options = [
                "Applied",
                "Shortlisted",
                "Selected",
                "Rejected"
            ]

            for _, row in application_data.iterrows():

                internship_id = int(row["internship_id"])

                with st.container(border=True):

                    st.subheader("💼 " + str(row["Role"]))

                    st.write("**Company:**", row["Company"])
                    st.write("**Location:**", row["Location"])
                    st.write("**Current Status:**", row["status"])
                    st.write("**Date:**", row["applied_date"])

                    current_status = row["status"]

                    status_index = (
                        status_options.index(current_status)
                        if current_status in status_options
                        else 0
                    )

                    new_status = st.selectbox(
                        "Update Application Status",
                        status_options,
                        index=status_index,
                        key=f"status_{internship_id}"
                    )

                    if st.button(
                        "Update Status",
                        key=f"update_{internship_id}"
                    ):

                        updated = update_application_status(
                            st.session_state.student_email,
                            internship_id,
                            new_status
                        )

                        if updated:
                            st.success("Status updated!")
                            st.rerun()

                        else:
                            st.warning("Unable to update status.")

            st.caption(
                "Statuses are manually updated by students "
                "and are not verified by employers."
            )

    # ==================================================
    # ANALYTICS DASHBOARD
    # ==================================================

    elif page == "📊 Analytics Dashboard":

        st.header("📊 Advanced Analytics Dashboard")

        applications = get_applications(
            st.session_state.student_email
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Internships", len(data))

        with col2:
            st.metric("Total Companies", data["Company"].nunique())

        with col3:
            st.metric("Total Locations", data["Location"].nunique())

        with col4:
            st.metric("My Applications", len(applications))

        st.divider()

        st.subheader("📍 Location-wise Internships")

        location_counts = data["Location"].value_counts().reset_index()
        location_counts.columns = ["Location", "Internships"]

        fig_location = px.bar(
            location_counts,
            x="Location",
            y="Internships",
            color="Location",
            text="Internships",
            title="Internships by Location"
        )

        fig_location.update_layout(
            template="plotly_dark",
            showlegend=False
        )

        st.plotly_chart(fig_location, use_container_width=True)

        st.divider()

        st.subheader("🏢 Company-wise Internships")

        company_counts = data["Company"].value_counts().reset_index()
        company_counts.columns = ["Company", "Internships"]

        fig_company = px.bar(
            company_counts,
            x="Company",
            y="Internships",
            color="Internships",
            title="Internships by Company"
        )

        fig_company.update_layout(
            template="plotly_dark",
            xaxis_tickangle=-45
        )

        st.plotly_chart(fig_company, use_container_width=True)

        st.divider()

        st.subheader("💰 Stipend Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Average Stipend",
                f"₹{data['Stipend'].mean():,.0f}"
            )

        with col2:
            st.metric(
                "Highest Stipend",
                f"₹{data['Stipend'].max():,}"
            )

        with col3:
            st.metric(
                "Lowest Stipend",
                f"₹{data['Stipend'].min():,}"
            )

        fig_stipend = px.histogram(
            data,
            x="Stipend",
            nbins=10,
            title="Monthly Stipend Distribution"
        )

        fig_stipend.update_layout(template="plotly_dark")

        st.plotly_chart(fig_stipend, use_container_width=True)

        st.divider()

        st.subheader("📝 Application Status Analysis")

        if applications.empty:
            st.info(
                "No applications found. Add internships to "
                "your application tracker to see analytics."
            )

        else:
            status_counts = applications["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]

            fig_status = px.pie(
                status_counts,
                names="Status",
                values="Count",
                hole=0.4,
                title="Application Status Distribution"
            )

            fig_status.update_layout(template="plotly_dark")

            st.plotly_chart(fig_status, use_container_width=True)

            st.dataframe(
                status_counts,
                use_container_width=True,
                hide_index=True
            )

        st.caption(
            "Analytics include sample and approved user-submitted internships."
        )

    # ==================================================
    # ADMIN APPROVAL
    # ==================================================

    elif page == "🛡️ Admin Approval" and is_admin:

        st.header("🛡️ Admin Internship Approval")

        st.write(
            "Review internship submissions before publishing them."
        )

        submissions = get_user_internships()

        pending = submissions[
            submissions["status"] == "Pending"
        ]

        if pending.empty:
            st.success("No pending internships!")

        else:
            st.info(
                f"{len(pending)} internship(s) waiting for approval."
            )

            for _, row in pending.iterrows():

                with st.container(border=True):

                    st.subheader("🏢 " + row["company"])

                    st.write("**Role:**", row["role"])
                    st.write("**Skills:**", row["skills"])
                    st.write("**Location:**", row["location"])
                    st.write("**Stipend:**", f"₹{int(row['stipend']):,}")
                    st.write("**Description:**", row["description"])
                    st.write("**Submitted By:**", row["submitted_by"])

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            "✅ Approve",
                            key=f"approve_{row['id']}"
                        ):
                            update_internship_approval(
                                int(row["id"]),
                                "Approved"
                            )
                            st.success("Internship approved!")
                            st.rerun()

                    with col2:
                        if st.button(
                            "❌ Reject",
                            key=f"reject_{row['id']}"
                        ):
                            update_internship_approval(
                                int(row["id"]),
                                "Rejected"
                            )
                            st.warning("Internship rejected!")
                            st.rerun()

    # ==================================================
    # FOOTER
    # ==================================================

    st.divider()

    st.caption(
        "InternMatch | AI-Based Internship Recommendation System "
        "| AI & Data Science Project"
    )

    is_admin = (
        bool(admin_email)
        and st.session_state.student_email == admin_email
    )

    # SIDEBAR BRANDING
    st.sidebar.markdown("""
    <div style="text-align:center; padding:20px 10px;">
        <h2 style="color:#c5a6ff;">🎓 InternMatch</h2>
        <p style="color:#cfc5e8;">AI-Powered Internship Portal</p>
    </div>
    """, unsafe_allow_html=True)

    navigation = [
        "🏠 Dashboard",
        "🎯 Find Internships",
        "➕ Add Internship",
        "💾 Saved Internships",
        "👤 My Profile",
        "📝 My Applications",
        "📊 Analytics Dashboard"
    ]

    if is_admin:
        navigation.append("🛡️ Admin Approval")

    page = st.sidebar.radio("Navigation", navigation)

    if st.sidebar.button("🚪 Logout", key="logout_button_2"):
        st.session_state.logged_in = False
        st.session_state.student_name = ""
        st.session_state.student_email = ""
        st.session_state.recommendations = None
        st.session_state.recommended_skills = ""
        st.rerun()

    # ==================================================
    # DASHBOARD
    # ==================================================

    if page == "🏠 Dashboard":

        st.markdown("""
        <div style="
            background:linear-gradient(90deg,#6550db,#a35cff);
            padding:30px;
            border-radius:20px;
            margin-bottom:25px;
        ">
            <h2 style="color:white !important;">
                🚀 Discover Your Dream Internship
            </h2>
            <p style="color:#f3edff;">
                Find your perfect internship with AI-powered recommendations.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.header("📊 Internship Overview")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Internships", len(data))

        with col2:
            st.metric("Companies", data["Company"].nunique())

        with col3:
            st.metric("Locations", data["Location"].nunique())

        st.divider()

        st.subheader("💼 Explore Internship Opportunities")

        search = st.text_input("Search Company or Internship Role")

        filtered_data = data.copy()

        if search.strip():
            mask = (
                filtered_data["Company"].str.contains(
                    search, case=False, regex=False
                )
                |
                filtered_data["Role"].str.contains(
                    search, case=False, regex=False
                )
            )

            filtered_data = filtered_data[mask]

        st.dataframe(
            filtered_data,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Initial 15 internships are sample data for academic demonstration."
        )

    # ==================================================
    # ADD INTERNSHIP
    # ==================================================

    elif page == "➕ Add Internship":

        st.title("➕ Add New Internship")

        st.write("Share internship opportunities with other students.")

        with st.form("add_internship_form"):

            company = st.text_input(
                "🏢 Company Name",
                placeholder="Example: Zoho"
            )

            role = st.text_input(
                "💼 Internship Role",
                placeholder="Example: Python Developer"
            )

            skills = st.text_input(
                "🛠 Required Skills",
                placeholder="Python, SQL, Machine Learning"
            )

            location = st.selectbox(
                "📍 Location",
                [
                    "Chennai",
                    "Bengaluru",
                    "Coimbatore",
                    "Salem",
                    "Erode",
                    "Tiruppur",
                    "Remote"
                ]
            )

            stipend = st.number_input(
                "💰 Monthly Stipend (₹)",
                min_value=0,
                step=1000
            )

            description = st.text_area(
                "📝 Internship Description"
            )

            submit = st.form_submit_button(
                "➕ Submit Internship",
                use_container_width=True
            )

        if submit:

            if not company.strip() or not role.strip() or not skills.strip():
                st.error("Please fill Company Name, Role and Skills.")

            else:
                add_new_internship(
                    company.strip(),
                    role.strip(),
                    skills.strip(),
                    location,
                    stipend,
                    description.strip(),
                    st.session_state.student_email
                )

                st.success(
                    "🎉 Internship submitted successfully!"
                )

                st.info(
                    "Your internship is waiting for admin approval."
                )

        st.divider()
        st.subheader("📋 My Submitted Internships")

        user_data = get_user_internships()

        my_submissions = user_data[
            user_data["submitted_by"] == st.session_state.student_email
        ]

        if not my_submissions.empty:
            st.dataframe(
                my_submissions[
                    ["company", "role", "location", "stipend", "status"]
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("You haven't submitted any internships yet.")

    # ==================================================
    # FIND INTERNSHIPS
    # ==================================================

    elif page == "🎯 Find Internships":

        st.header("🎯 AI Internship Recommendation")

        st.write(
            "Enter your skills and preferences to find matching internships."
        )

        col1, col2 = st.columns(2)

        with col1:
            skills = st.text_input(
                "Your Technical Skills",
                placeholder="Python, SQL, Machine Learning"
            )

            interest = st.selectbox(
                "Career Interest",
                [
                    "Data Science",
                    "Artificial Intelligence",
                    "Machine Learning",
                    "Deep Learning",
                    "Generative AI",
                    "Python Development",
                    "Java Development",
                    "Web Development",
                    "Full Stack Development",
                    "Frontend Development",
                    "Backend Development",
                    "Cybersecurity",
                    "Cloud Computing",
                    "Data Analytics",
                    "Business Analytics",
                    "Robotics",
                    "Internet of Things",
                    "UI UX Design",
                    "Mobile App Development",
                    "Software Development",
                    "DevOps",
                    "Database Management"
                ]
            )

        with col2:
            location = st.selectbox(
                "Preferred Location",
                [
                    "Any",
                    "Chennai",
                    "Bengaluru",
                    "Coimbatore",
                    "Salem",
                    "Erode",
                    "Tiruppur",
                    "Remote"
                ]
            )

            stipend = st.selectbox(
                "Minimum Monthly Stipend",
                [0, 5000, 8000, 10000, 12000, 15000],
                format_func=lambda x: (
                    "Any Stipend" if x == 0 else f"₹{x:,}"
                )
            )

        if st.button("✨ Recommend Internships"):

            if not skills.strip():
                st.warning("Please enter your technical skills.")

            else:
                results = recommend_internships(
                    skills,
                    interest,
                    location,
                    stipend
                )

                st.session_state.recommendations = results
                st.session_state.recommended_skills = skills

        if st.session_state.recommendations is not None:

            results = st.session_state.recommendations

            st.divider()
            st.subheader("🏆 Recommended Internships")

            if results.empty:
                st.warning(
                    "No matching internships found. "
                    "Try changing your skills or filters."
                )

            else:
                st.success(
                    f"Found {len(results)} matching internships!"
                )

                for _, row in results.iterrows():

                    with st.container(border=True):

                        st.subheader("💼 " + row["Role"])

                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**Company:**", row["Company"])
                            st.write("**Required Skills:**", row["Skills"])

                        with col2:
                            st.write("**Location:**", row["Location"])
                            st.write(
                                "**Monthly Stipend:**",
                                f"₹{int(row['Stipend']):,}"
                            )

                        score = float(row["Match Score"])

                        st.write(
                            f"**AI Match Score: {score:.1f}%**"
                        )

                        st.progress(
                            min(max(score / 100, 0.0), 1.0)
                        )

                        st.markdown("### 🧠 Skill Gap Analysis")

                        matching, missing, skill_percentage = (
                            analyze_skill_gap(
                                st.session_state.recommended_skills,
                                row["Skills"]
                            )
                        )

                        st.write(
                            f"**Skill Match: {skill_percentage:.1f}%**"
                        )

                        st.progress(
                            min(max(skill_percentage / 100, 0.0), 1.0)
                        )

                        if matching:
                            st.success(
                                "✅ Matching Skills: "
                                + ", ".join(
                                    skill.title() for skill in matching
                                )
                            )

                        if missing:
                            st.warning(
                                "❌ Missing Skills: "
                                + ", ".join(
                                    skill.title() for skill in missing
                                )
                            )

                            st.info(
                                "📚 Skills to Learn: "
                                + ", ".join(
                                    skill.title() for skill in missing
                                )
                            )

                        if not missing:
                            st.success(
                                "🎉 You have all listed required skills!"
                            )

                        internship_id = int(row["Internship ID"])

                        button_col1, button_col2 = st.columns(2)

                        with button_col1:
                            if st.button(
                                "💾 Save Internship",
                                key=f"save_{internship_id}"
                            ):
                                added = save_internship(
                                    st.session_state.student_email,
                                    internship_id
                                )

                                if added:
                                    st.success("Internship saved!")
                                else:
                                    st.info("Already saved.")

                        with button_col2:
                            if st.button(
                                "📝 Add to Application Tracker",
                                key=f"apply_{internship_id}"
                            ):
                                added = apply_internship(
                                    st.session_state.student_email,
                                    internship_id
                                )

                                if added:
                                    st.success("Added to tracker!")
                                else:
                                    st.info("Already tracked.")

                csv = results.to_csv(index=False).encode("utf-8")

                st.download_button(
                    "📥 Download Recommendations",
                    data=csv,
                    file_name="recommendations.csv",
                    mime="text/csv"
                )

                st.caption(
                    "AI match scores are text similarity scores, "
                    "not hiring probabilities."
                )

    # ==================================================
    # SAVED INTERNSHIPS
    # ==================================================

    elif page == "💾 Saved Internships":

        st.header("💾 My Saved Internships")

        saved = get_saved_internships(
            st.session_state.student_email
        )

        if saved.empty:
            st.info("You haven't saved any internships yet.")

        else:
            saved_data = data[
                data["Internship ID"].isin(saved["internship_id"])
            ]

            st.dataframe(
                saved_data,
                use_container_width=True,
                hide_index=True
            )

    # ==================================================
    # STUDENT PROFILE
    # ==================================================

    elif page == "👤 My Profile":

        st.header("👤 My Student Profile")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, email, college, department
            FROM students
            WHERE email = ?
        """, (st.session_state.student_email,))

        student = cursor.fetchone()
        conn.close()

        if student:

            name, email, college, department = student

            st.subheader("🎓 Student Information")

            st.write("**Full Name:**", name)
            st.write("**Email Address:**", email)
            st.write("**College:**", college)
            st.write("**Department:**", department)

            st.divider()
            st.subheader("✏️ Update Profile")

            with st.form("update_profile"):

                new_name = st.text_input(
                    "Full Name",
                    value=name
                )

                new_college = st.text_input(
                    "College Name",
                    value=college or ""
                )

                new_department = st.text_input(
                    "Department",
                    value=department or ""
                )

                update_button = st.form_submit_button(
                    "Save Changes"
                )

            if update_button:

                if not new_name.strip():
                    st.warning("Name cannot be empty.")

                else:
                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE students
                        SET name = ?, college = ?, department = ?
                        WHERE email = ?
                    """, (
                        new_name.strip(),
                        new_college.strip(),
                        new_department.strip(),
                        st.session_state.student_email
                    ))

                    conn.commit()
                    conn.close()

                    st.session_state.student_name = new_name.strip()

                    st.success("Profile updated!")
                    st.rerun()

    # ==================================================
    # APPLICATION TRACKING
    # ==================================================

    elif page == "📝 My Applications":

        st.header("📝 My Internship Applications")

        applications = get_applications(
            st.session_state.student_email
        )

        if applications.empty:
            st.info(
                "You haven't added any internships "
                "to your application tracker yet."
            )

        else:
            application_data = applications.merge(
                data,
                left_on="internship_id",
                right_on="Internship ID",
                how="left"
            )

            st.subheader("📊 Application Overview")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Applications",
                    len(application_data)
                )

            with col2:
                st.metric(
                    "Applied",
                    int((application_data["status"] == "Applied").sum())
                )

            with col3:
                st.metric(
                    "Shortlisted",
                    int((application_data["status"] == "Shortlisted").sum())
                )

            with col4:
                st.metric(
                    "Selected",
                    int((application_data["status"] == "Selected").sum())
                )

            st.divider()
            st.subheader("💼 Application Details")

            status_options = [
                "Applied",
                "Shortlisted",
                "Selected",
                "Rejected"
            ]

            for _, row in application_data.iterrows():

                internship_id = int(row["internship_id"])

                with st.container(border=True):

                    st.subheader("💼 " + str(row["Role"]))

                    st.write("**Company:**", row["Company"])
                    st.write("**Location:**", row["Location"])
                    st.write("**Current Status:**", row["status"])
                    st.write("**Date:**", row["applied_date"])

                    current_status = row["status"]

                    status_index = (
                        status_options.index(current_status)
                        if current_status in status_options
                        else 0
                    )

                    new_status = st.selectbox(
                        "Update Application Status",
                        status_options,
                        index=status_index,
                        key=f"status_{internship_id}"
                    )

                    if st.button(
                        "Update Status",
                        key=f"update_{internship_id}"
                    ):

                        updated = update_application_status(
                            st.session_state.student_email,
                            internship_id,
                            new_status
                        )

                        if updated:
                            st.success("Status updated!")
                            st.rerun()

                        else:
                            st.warning("Unable to update status.")

            st.caption(
                "Statuses are manually updated by students "
                "and are not verified by employers."
            )

    # ==================================================
    # ANALYTICS DASHBOARD
    # ==================================================

    elif page == "📊 Analytics Dashboard":

        st.header("📊 Advanced Analytics Dashboard")

        applications = get_applications(
            st.session_state.student_email
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Internships", len(data))

        with col2:
            st.metric("Total Companies", data["Company"].nunique())

        with col3:
            st.metric("Total Locations", data["Location"].nunique())

        with col4:
            st.metric("My Applications", len(applications))

        st.divider()

        st.subheader("📍 Location-wise Internships")

        location_counts = data["Location"].value_counts().reset_index()
        location_counts.columns = ["Location", "Internships"]

        fig_location = px.bar(
            location_counts,
            x="Location",
            y="Internships",
            color="Location",
            text="Internships",
            title="Internships by Location"
        )

        fig_location.update_layout(
            template="plotly_dark",
            showlegend=False
        )

        st.plotly_chart(fig_location, use_container_width=True)

        st.divider()

        st.subheader("🏢 Company-wise Internships")

        company_counts = data["Company"].value_counts().reset_index()
        company_counts.columns = ["Company", "Internships"]

        fig_company = px.bar(
            company_counts,
            x="Company",
            y="Internships",
            color="Internships",
            title="Internships by Company"
        )

        fig_company.update_layout(
            template="plotly_dark",
            xaxis_tickangle=-45
        )

        st.plotly_chart(fig_company, use_container_width=True)

        st.divider()

        st.subheader("💰 Stipend Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Average Stipend",
                f"₹{data['Stipend'].mean():,.0f}"
            )

        with col2:
            st.metric(
                "Highest Stipend",
                f"₹{data['Stipend'].max():,}"
            )

        with col3:
            st.metric(
                "Lowest Stipend",
                f"₹{data['Stipend'].min():,}"
            )

        fig_stipend = px.histogram(
            data,
            x="Stipend",
            nbins=10,
            title="Monthly Stipend Distribution"
        )

        fig_stipend.update_layout(template="plotly_dark")

        st.plotly_chart(fig_stipend, use_container_width=True)

        st.divider()

        st.subheader("📝 Application Status Analysis")

        if applications.empty:
            st.info(
                "No applications found. Add internships to "
                "your application tracker to see analytics."
            )

        else:
            status_counts = applications["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]

            fig_status = px.pie(
                status_counts,
                names="Status",
                values="Count",
                hole=0.4,
                title="Application Status Distribution"
            )

            fig_status.update_layout(template="plotly_dark")

            st.plotly_chart(fig_status, use_container_width=True)

            st.dataframe(
                status_counts,
                use_container_width=True,
                hide_index=True
            )

        st.caption(
            "Analytics include sample and approved user-submitted internships."
        )

    # ==================================================
    # ADMIN APPROVAL
    # ==================================================

    elif page == "🛡️ Admin Approval" and is_admin:

        st.header("🛡️ Admin Internship Approval")

        st.write(
            "Review internship submissions before publishing them."
        )

        submissions = get_user_internships()

        pending = submissions[
            submissions["status"] == "Pending"
        ]

        if pending.empty:
            st.success("No pending internships!")

        else:
            st.info(
                f"{len(pending)} internship(s) waiting for approval."
            )

            for _, row in pending.iterrows():

                with st.container(border=True):

                    st.subheader("🏢 " + row["company"])

                    st.write("**Role:**", row["role"])
                    st.write("**Skills:**", row["skills"])
                    st.write("**Location:**", row["location"])
                    st.write("**Stipend:**", f"₹{int(row['stipend']):,}")
                    st.write("**Description:**", row["description"])
                    st.write("**Submitted By:**", row["submitted_by"])

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            "✅ Approve",
                            key=f"approve_{row['id']}"
                        ):
                            update_internship_approval(
                                int(row["id"]),
                                "Approved"
                            )
                            st.success("Internship approved!")
                            st.rerun()

                    with col2:
                        if st.button(
                            "❌ Reject",
                            key=f"reject_{row['id']}"
                        ):
                            update_internship_approval(
                                int(row["id"]),
                                "Rejected"
                            )
                            st.warning("Internship rejected!")
                            st.rerun()

    # ==================================================
    # FOOTER
    # ==================================================

    st.divider()

    st.caption(
        "InternMatch | AI-Based Internship Recommendation System "
        "| AI & Data Science Project"
    )