import streamlit as st
import requests
import pdfplumber
from docx import Document

BACKEND_BASE = "http://127.0.0.1:8000"
RECOMMEND_URL = f"{BACKEND_BASE}/recommend"
HEALTH_URL = f"{BACKEND_BASE}/health"

st.set_page_config(page_title="Resume Job Matcher", layout="wide")
st.title("📄 Resume-Based Job Recommendation")

# --- Backend health check ---
with st.sidebar:
    st.header("Backend Status")
    try:
        health = requests.get(HEALTH_URL, timeout=5)
        if health.status_code == 200:
            st.success("Backend is running ✅")
        else:
            st.warning("Backend responded but with issues ⚠️")
    except:
        st.error("Backend is NOT running ❌")

# --- Resume extraction function ---
def extract_text(file):
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)
    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")
    return ""

uploaded_file = st.file_uploader("Upload Resume (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"])
experience_years = st.number_input("Experience (years)", min_value=0, max_value=40, step=1)

if uploaded_file:
    resume_text = extract_text(uploaded_file)

    st.subheader("Extracted Resume Text (Preview)")
    st.text_area(
        "Extracted Resume Text",
        resume_text[:3000],
        height=200,
        label_visibility="collapsed"
    )

    if st.button("🔍 Analyze Resume"):
        if not resume_text.strip():
            st.warning("Could not extract text from resume.")
        else:
            payload = {
                "resume_text": resume_text,
                "experience_years": experience_years
            }

            with st.spinner("Analyzing resume..."):
                try:
                    res = requests.post(RECOMMEND_URL, json=payload, timeout=15)

                    if res.status_code == 200:
                        data = res.json()
                        if data:
                            best = data[0]
                            st.success(f"Best matched role: {best['job_role']} ({best['trade']})")
                            st.subheader("Top Matching Jobs")
                            st.table(data)
                        else:
                            st.info("No matching jobs found.")
                    else:
                        st.error(f"Backend error {res.status_code}")
                        st.code(res.text)

                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Cannot connect to backend: {e}")
