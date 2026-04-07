# 🚀 AI Hiring Agent: Smart Resume Screener

![hrsytumouput1](https://github.com/user-attachments/assets/3ca5185f-eca5-4977-8e8d-2f0b56e29ea1)












![hrsytumouput2](https://github.com/user-attachments/assets/d48b5f99-b5a9-40ae-b3da-0129a0a43d59)















![hrsytumouput3](https://github.com/user-attachments/assets/9a2d4f7c-c1d5-41d9-bf4d-0c7d0ca30c78)














 
An intelligent, fully automated recruitment dashboard that acts as an AI Hiring Assistant. This application allows HR professionals to upload bulk PDF resumes, uses Large Language Models (LLMs) to extract structured data, and mathematically ranks candidates based on a weighted scoring system—all wrapped in a premium, animated UI.

## ✨ Key Features

- **Multi-File Processing:** Upload and process up to 20 PDF resumes at once.
- **LLM-Powered Extraction:** Uses `Llama 3.3 70B` (via Groq) to intelligently read and extract key metrics (CGPA, Experience, Projects) regardless of the resume format.
- **Smart Scoring Formula:** Normalizes global GPA scales (e.g., 3.2/4.0 becomes 8.0/10) and ranks candidates based on a weighted algorithm (Experience and Projects matter just as much as grades!).
- **Enterprise UI:** A custom, deep-red aesthetic featuring CSS `@keyframes` animations, hover effects, and glowing status badges.
- **Bot Protection:** Integrated Google reCAPTCHA v2 to secure the application.
- **Deduplication:** Automatically identifies and removes duplicate uploads using candidate emails.

![hrsytumouput4](https://github.com/user-attachments/assets/a304719a-56af-4a78-a904-b3d6e81e24ac)














![hrsytumouput5](https://github.com/user-attachments/assets/38bd1676-f096-41c4-8c26-6fd35f430d79)















## 🧠 How the AI Ranks Candidates (The Formula)

Unlike traditional ATS systems that just look for keywords, this agent calculates a comprehensive score out of 100 based on the following weights:

* **College CGPA:** 30%
* **Years of Experience:** 30% *(Capped at 5+ years for scaling)*
* **Total Projects:** 25% *(Capped at 5+ projects)*
* **12th Grade Marks:** 10%
* **10th Grade Marks:** 5%

**Badges Assigned:**
* 🟢 **TOP MATCH:** Ranks 1–3
* 🟡 **GOOD FIT:** Ranks 4–7
* ⚪ **ACCEPTABLE:** Ranks 8–10
* 🔴 **NON-ACCEPTABLE:** Ranks 11+ (Displayed below the fold)

## 🛠️ Tech Stack

* **Frontend:** Streamlit (with Custom injected HTML/CSS)
* **Backend:** Python
* **LLM Engine:** Groq API (`llama-3.3-70b-versatile` & `llama-3.1-8b-instant`)
* **PDF Parsing:** `pdfplumber`
* **Security:** Google reCAPTCHA v2 (`streamlit-javascript`)

## 🚀 Installation & Setup

### 1. Clone the repository
```bash
git clone [https://github.com/yourusername/ai-hiring-agent.git](https://github.com/yourusername/ai-hiring-agent.git)
cd ai-hiring-agent
