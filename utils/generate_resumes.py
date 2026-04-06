"""
Generates 19 synthetic PDF resumes in /resumes for parser stress-testing.

Edge cases injected:
  - CGPA missing entirely        : Priya Verma, Vikram Singh, Kavya Menon
  - CGPA on 4.0 scale            : Karan Patel, Meera Nair, Manish Yadav
  - Project count shown as "N/A" : Aarav Sharma, Pooja Bansal
  - Project count left blank     : Ritika Sen
  - Messy layout / spacing       : Rohan Mehta, Ananya Gupta, Rahul Das, Arjun Reddy, Deepak Choudhary
  - Section order randomised     : all 19 get a different section sequence
  - Marks format varied          : %, "percent", /100 rotating across candidates
"""

import os
import random
from fpdf import FPDF

random.seed(42)

OUTPUT_DIR = "resumes"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# (name, email, cgpa/10, years_of_exp, project_count, 10th%, 12th%)
CANDIDATES = [
    ("Aarav Sharma",       "aarav.sharma@gmail.com",       8.7, 2,   5, 91, 89),
    ("Priya Verma",        "priya.verma@gmail.com",        9.1, 1,   4, 95, 93),
    ("Rohan Mehta",        "rohan.mehta@gmail.com",        7.8, 3,   6, 85, 82),
    ("Sneha Iyer",         "sneha.iyer@gmail.com",         8.9, 2.5, 5, 92, 90),
    ("Karan Patel",        "karan.patel@gmail.com",        7.5, 4,   7, 80, 78),
    ("Ananya Gupta",       "ananya.gupta@gmail.com",       9.4, 1,   3, 96, 95),
    ("Vikram Singh",       "vikram.singh@gmail.com",       8.2, 3,   6, 88, 86),
    ("Neha Kapoor",        "neha.kapoor@gmail.com",        8.8, 2,   5, 90, 91),
    ("Rahul Das",          "rahul.das@gmail.com",          7.9, 3.5, 6, 84, 83),
    ("Meera Nair",         "meera.nair@gmail.com",         9.0, 1.5, 4, 93, 92),
    ("Aditya Rao",         "aditya.rao@gmail.com",         8.3, 2.5, 5, 89, 87),
    ("Pooja Bansal",       "pooja.bansal@gmail.com",       9.2, 1,   4, 94, 93),
    ("Arjun Reddy",        "arjun.reddy@gmail.com",        7.6, 4,   7, 82, 80),
    ("Kavya Menon",        "kavya.menon@gmail.com",        8.5, 2,   5, 91, 90),
    ("Saurabh Jain",       "saurabh.jain@gmail.com",       8.1, 3,   6, 87, 85),
    ("Isha Khanna",        "isha.khanna@gmail.com",        9.3, 1,   3, 95, 94),
    ("Manish Yadav",       "manish.yadav@gmail.com",       7.7, 3.5, 6, 83, 81),
    ("Ritika Sen",         "ritika.sen@gmail.com",         8.6, 2,   5, 90, 88),
    ("Deepak Choudhary",   "deepak.choudhary@gmail.com",   8.0, 3,   6, 86, 84),
]

# -- Edge case sets (0-based index) -------------------------------------------
CGPA_MISSING  = {1, 6, 13}   # drop CGPA field entirely
CGPA_4_SCALE  = {4, 9, 16}   # report on 4.0 scale
PROJECT_NA    = {0, 11}      # show "N/A"
PROJECT_BLANK = {17}         # leave blank (no text at all)
MESSY_FORMAT  = {2, 5, 8, 12, 18}

# -- Section order variants (contact always first) ----------------------------
SECTION_ORDERS = [
    ["contact", "education", "experience", "projects", "skills"],
    ["contact", "experience", "education", "projects", "skills"],
    ["contact", "projects", "experience", "education", "skills"],
    ["contact", "skills", "education", "experience", "projects"],
    ["contact", "education", "skills", "projects", "experience"],
    ["contact", "experience", "projects", "skills", "education"],
    ["contact", "projects", "skills", "education", "experience"],
]

# -- Pool data -----------------------------------------------------------------
COMPANIES = ["TechCorp", "Infosys", "Wipro", "TCS", "Accenture", "HCL", "Cognizant", "Capgemini"]
ROLES     = ["Software Engineer", "Junior Developer", "Systems Analyst", "Associate Engineer", "Backend Developer"]
PROJECTS  = [
    "E-commerce Platform", "Chat Application", "Image Classifier",
    "Portfolio Website", "Task Manager App", "Weather Forecast App",
    "Student Management System", "Movie Recommendation Engine",
    "Expense Tracker", "Online Quiz Platform", "Blog Engine",
    "Inventory Management Tool", "URL Shortener Service",
]
SKILLS_POOL = ["Python", "Java", "C++", "SQL", "Git", "React", "Django", "TensorFlow",
               "Node.js", "MongoDB", "Docker", "Linux", "Machine Learning"]


def to_4_scale(cgpa10: float) -> float:
    return round(cgpa10 / 10 * 4, 1)


def build_experience_entries(idx: int, yoe: float) -> list[str]:
    """Break yoe into 1-3 role entries (summing to yoe)."""
    if yoe == 0:
        return ["Fresher - No prior work experience"]
    entries = []
    remaining = yoe
    i = 0
    while remaining > 0:
        duration = round(min(remaining, random.choice([0.5, 1.0, 1.5, 2.0])), 1)
        remaining = round(remaining - duration, 1)
        company = COMPANIES[(idx + i) % len(COMPANIES)]
        role    = ROLES[(idx + i) % len(ROLES)]
        yrs     = "year" if duration == 1.0 else "years"
        entries.append(f"{role} at {company} ({duration} {yrs})")
        i += 1
    return entries


# -- PDF builder ---------------------------------------------------------------

def generate_resume(idx: int, candidate: tuple) -> None:
    name, email, cgpa, yoe, proj_count, tenth, twelfth = candidate

    messy   = idx in MESSY_FORMAT
    order   = SECTION_ORDERS[idx % len(SECTION_ORDERS)]

    # -- Determine CGPA text --------------------------------------------------
    if idx in CGPA_MISSING:
        cgpa_line = None                             # omit entirely
    elif idx in CGPA_4_SCALE:
        cgpa_line = f"{to_4_scale(cgpa)}/4.0 GPA"
    else:
        fmt = idx % 3
        if fmt == 0:
            cgpa_line = f"CGPA: {cgpa}/10"
        elif fmt == 1:
            cgpa_line = f"GPA: {cgpa}/10"
        else:
            cgpa_line = f"{cgpa} CGPA"

    # -- Determine marks text -------------------------------------------------
    fmt = idx % 3
    if fmt == 0:
        tenth_str, twelfth_str = f"{tenth}%", f"{twelfth}%"
    elif fmt == 1:
        tenth_str, twelfth_str = f"{tenth} percent", f"{twelfth} percent"
    else:
        tenth_str, twelfth_str = f"{tenth}/100", f"{twelfth}/100"

    # -- Project count display ------------------------------------------------
    if idx in PROJECT_NA:
        proj_display = "N/A"
    elif idx in PROJECT_BLANK:
        proj_display = ""      # blank - will skip the count line
    else:
        proj_display = None    # use actual list

    project_list = [PROJECTS[(idx + j) % len(PROJECTS)] for j in range(proj_count)]
    experience   = build_experience_entries(idx, yoe)
    skills       = (SKILLS_POOL * 2)[idx % 6 : idx % 6 + 4 + idx % 3]

    # -- Init PDF -------------------------------------------------------------
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    L = pdf.l_margin

    # -- Helper renderers -----------------------------------------------------

    def section_header(title: str) -> None:
        if messy:
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(random.randint(1, 7))
            pdf.set_x(L)
            pdf.cell(0, 7, title.upper(), ln=True)
            pdf.ln(1)
        else:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(20, 50, 150)
            pdf.ln(5)
            pdf.set_x(L)
            pdf.cell(0, 8, title.upper(), ln=True, border="B")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

    def line(text: str, indent: int = 5) -> None:
        """Print one line, with optional indent and messy variation."""
        if messy:
            pdf.set_font("Helvetica", size=random.choice([9, 10, 11]))
            pdf.set_x(L + random.randint(0, 12))
        else:
            pdf.set_font("Helvetica", size=10)
            pdf.set_x(L + indent)
        pdf.cell(0, 6, text, ln=True)
        pdf.set_x(L)

    def blank(n: int = 1) -> None:
        pdf.ln(3 * n)

    # -- Section renderers ----------------------------------------------------

    def render_contact() -> None:
        name_size = 14 if messy else 18
        align     = "L" if messy else "C"
        if messy:
            pdf.ln(random.randint(0, 8))
        pdf.set_font("Helvetica", "B", name_size)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, name, ln=True, align=align)
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 6, email, ln=True, align=align)
        blank()

    def render_education() -> None:
        section_header("Education")
        line("B.Tech - Computer Science Engineering")
        line("ABC University | Graduated 2023")
        if cgpa_line:
            line(cgpa_line)
        # if CGPA_MISSING and messy: silently omit (realistic)
        # if CGPA_MISSING and clean: show placeholder
        elif not messy:
            line("CGPA: Not Disclosed")
        line(f"12th (HSC): {twelfth_str}")
        line(f"10th (SSC): {tenth_str}")

    def render_experience() -> None:
        section_header("Work Experience")
        for entry in experience:
            line(f"  {entry}")

    def render_projects() -> None:
        section_header("Projects")
        if proj_display == "N/A":
            line("Projects: N/A")
        elif proj_display == "":
            # blank - header present but nothing listed (edge case)
            pass
        else:
            for p in project_list:
                line(f"- {p}")

    def render_skills() -> None:
        section_header("Skills")
        line(", ".join(skills))

    render_map = {
        "contact":    render_contact,
        "education":  render_education,
        "experience": render_experience,
        "projects":   render_projects,
        "skills":     render_skills,
    }

    for section in order:
        render_map[section]()

    # -- Save -----------------------------------------------------------------
    safe = name.replace(" ", "_")
    path = os.path.join(OUTPUT_DIR, f"{idx + 1:02d}_{safe}.pdf")
    pdf.output(path)
    print(f"  [{idx + 1:02d}] {path}")


# -- Entry point ---------------------------------------------------------------

if __name__ == "__main__":
    print(f"Generating {len(CANDIDATES)} resumes into /{OUTPUT_DIR}/...\n")
    for i, c in enumerate(CANDIDATES):
        generate_resume(i, c)
    print(f"\nDone. {len(CANDIDATES)} PDFs written to /{OUTPUT_DIR}/")
