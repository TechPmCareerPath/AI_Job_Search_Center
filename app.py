# Note: All code below written by Gemini. Some user facing text and comments below were written by the author.
# MIT License.
# To run after setup: > streamlit run app.py


# --- Libs ---
import streamlit as st
import json
import yaml
import os
import csv
import requests
import pandas as pd
from datetime import datetime, date, timedelta

# --- GenAI & Pydantic Imports ---
from google import genai
from google.genai import types
from google.genai.errors import APIError

from pydantic import BaseModel, Field
import pdfplumber
import docx

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Job Search Center",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Constants for Local Storage & App Config ---
# Holds all configs the user could update via the UI.
RESUME_DIR = "resume"
CONFIG_DIR = "config"
UPLOADS = "uploads"		# Currently stores the uploaded resume and query.yaml.

# Files to configure the app.
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.yaml")
PROMPTS_FILE = os.path.join(CONFIG_DIR, "prompts.yaml")

# Holds all output from the app and same outputs visibile in the UI.
OUTPUT_DIR = "output"
JOBS_RESPONSE = os.path.join(OUTPUT_DIR, "jobs.json")		# JobsPipe API raw output for this app to use.
JOBS_OUTPUT = os.path.join(OUTPUT_DIR, "jobs.csv")			# Jobsipe API output above converted to CSV.
AGENT_OUTPUT = os.path.join(OUTPUT_DIR, "agent_job_analysis.json")
SKIPPED_DB = os.path.join(OUTPUT_DIR, "skipped_jobs.json") 	# Persist the jobs that were skipped, aka marked as No by the user, across sessions.
TRACKER_DB = os.path.join(OUTPUT_DIR, "tracker_db.json")
PLAN_DB = os.path.join(OUTPUT_DIR, "weekly_plan.json")		# Persist the weekly plan across sessions.
ADVISOR_OUTPUT = os.path.join(OUTPUT_DIR, "agent_weekly_advisor.json")	# The on-demand Application Tracker Output saved across sessions. 


# --- Load and Save configs and output files ---

def load_weekly_plan() -> dict:
    """Loads active weekly plan from local JSON file."""
    if os.path.exists(PLAN_DB):
        try:
            with open(PLAN_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_weekly_plan(plan_data: dict):
    """Saves active weekly plan to local JSON file."""
    with open(PLAN_DB, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, indent=4, ensure_ascii=False)

def load_yaml(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def save_yaml(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)

def load_tracker():
    if os.path.exists(TRACKER_DB):
        with open(TRACKER_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tracker(tracker_data):
    """Saves application tracker data safely to local JSON file."""
    with open(TRACKER_DB, "w", encoding="utf-8") as f:
        json.dump(tracker_data, f, indent=4, default=str, ensure_ascii=False)

def load_skipped() -> list:
    """Loads list of skipped job IDs from local JSON file."""
    if os.path.exists(SKIPPED_DB):
        try:
            with open(SKIPPED_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_skipped(skipped_list: list):
    """Saves list of skipped job IDs to local JSON file."""
    with open(SKIPPED_DB, "w", encoding="utf-8") as f:
        json.dump(skipped_list, f, indent=4, ensure_ascii=False)


def get_weekly_plan_advice(tracker_file_path: str, plan_file_path: str) -> str:
    """
    Analyzes tracker_db.json and weekly_plan.json using AI to provide 
    1-2 high-impact strategic shifts for the user's weekly job search.
    Returns tuple: (advice_text, error_message)
    """

    # Implicit pickup by the SDK when client = genai.Client() is called without passing an explicit api_key parameter.
    if not os.getenv("GEMINI_API_KEY"):
        err_msg = "Gemini API Key missing! Enter it in the sidebar..."
        st.error(f"⚠️ {err_msg}")
        return None, err_msg

    # Load model configs.
    config_data = load_yaml(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else {}
    model_cfg = config_data.get("model_config", {})
    selected_model = model_cfg.get("selected_model", "gemini-2.5-flash")
    temperature = float(model_cfg.get("temperature", 0.2))

    # Read tracker data
    tracker_data = []
    if os.path.exists(tracker_file_path):
        with open(tracker_file_path, "r", encoding="utf-8") as f:
            try:
                tracker_data = json.load(f)
            except Exception:
                tracker_data = []

    # Read weekly plan data
    weekly_plan_data = {}
    if os.path.exists(plan_file_path):
        with open(plan_file_path, "r", encoding="utf-8") as f:
            try:
                weekly_plan_data = json.load(f)
            except Exception:
                weekly_plan_data = {}

    if not tracker_data and not weekly_plan_data:
        return "Enter notes for a few applications or set up your weekly plan to receive strategic advice!"

    # Load prompt from prompts.yaml (with fallback)
    prompts_data = load_yaml(PROMPTS_FILE) if os.path.exists(PROMPTS_FILE) else {}
    advisor_prompt = prompts_data.get("system_prompts", {}).get(
        "weekly_plan_advisor",
        "Analyze the Job Application Tracker data and active weekly plan. Identify 1–2 critical, high-impact strategic shifts to improve interview conversion and response rates. Focus exclusively on actionable moves tied directly to patterns in the user's recent notes, application statuses, or current weekly targets. If no high-impact strategy exists, return only the single most relevant action item. Limit the total output to 3-4 sentences maximum. Avoid generic job search advice or commentary."
    )

    prompt = f"""{advisor_prompt}

--- ACTIVE WEEKLY PLAN ---
{json.dumps(weekly_plan_data, indent=2)}

--- JOB APPLICATION TRACKER DATA ---
{json.dumps(tracker_data, indent=2)}
"""

    client = genai.Client()

    try:
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                # Passing Pydantic schema via MatchAnalysisResponse. Gemini SDK's inspection logic misidentifies the schema as callable function tools, which can lead to unexpected state issues or infinite loops. Resolve by turning it off. 
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            ),
        )
    
        return response.text, None

    except APIError as api_err:
        err_msg = f"Gemini API Error ({api_err.code}): {api_err.message}"
        print(f"❌ Gemini API Error in get_weekly_plan_advice() with selected model {selected_model}. {api_err}")
        return None, err_msg

    except Exception as e:
        err_msg = f"Failed to generate weekly plan advice: {str(e)}"
        print(f"❌ Unexpected Error in get_weekly_plan_advice(): {e}")
        return None, err_msg

    finally:
        if "is_generating_advice" in st.session_state:
            st.session_state.is_generating_advice = False


def generate_tailored_resume(resume_file_path: str, job_info: dict) -> str:
    """
    Generates a tailored resume using AI based on the selected base resume
    and the target job position requirements.
    Returns tuple: (advice_text, error_message)
    """

    # Guard check for API key. Implicit pickup by the SDK when client = genai.Client() is called without passing an explicit api_key parameter.
    if not os.getenv("GEMINI_API_KEY"):
        err_msg = "Gemini API Key missing! Enter it in the sidebar.."
        st.error(f"⚠️ {err_msg}")
        return None, err_msg

    # Read base resume text
    with open(resume_file_path, "r", encoding="utf-8") as f:
        resume_text = f.read()

    # Load model configuration and prompt template
    config_data = load_yaml(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else {}
    model_cfg = config_data.get("model_config", {})
    selected_model = model_cfg.get("selected_model", "gemini-2.5-flash")
    temperature = float(model_cfg.get("temperature", 0.2))

    prompts_data = load_yaml(PROMPTS_FILE) if os.path.exists(PROMPTS_FILE) else {}
    prompts_dict = prompts_data.get("system_prompts", {})
    tailor_system_prompt = prompts_dict.get(
        "resume_tailor",
        "You are an expert resume reviewer. Tailor the candidate's resume to match the selected job description HONESTLY."
    )

    # Construct prompt payload with job details
    prompt = f"""{tailor_system_prompt}

--- CANDIDATE BASE RESUME ---
{resume_text}

--- TARGET JOB DETAILS ---
Title: {job_info.get('title', 'N/A')}
Company: {job_info.get('company', 'Unknown Company')}
Match Reasoning: {job_info.get('reasoning', '')}
Key Matching Skills: {', '.join(job_info.get('key_matching_skills', []))}
Missing Skills to Address: {', '.join(job_info.get('missing_skills', []))}
"""

    client = genai.Client()

    try:
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                # Passing Pydantic schema via MatchAnalysisResponse. Gemini SDK's inspection logic misidentifies the schema as callable function tools, which can lead to unexpected state issues or infinite loops. Resolve by turning it off. 
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            ),
        )

        return response.text, None

    except APIError as api_err:
        err_msg = f"Gemini API Error ({api_err.code}): {api_err.message}"
        print(f"❌ Gemini API Error in generate_tailored_resume() with selected model {selected_model}. {api_err}")
        return None, err_msg

    except Exception as e:
        err_msg = f"Failed to generate tailored resume plan advice: {str(e)}"
        print(f"❌ Unexpected Error in generate_tailored_resume(): {e}")
        return None, err_msg

    finally:
        # Global state flag check
        if "is_tailoring" in st.session_state:
            st.session_state.is_tailoring = False
            
        # Per-job specific state flag check (if tracking buttons by job_id)
        job_id = job_info.get("job_id")
        if job_id and f"is_tailoring_{job_id}" in st.session_state:
            st.session_state[f"is_tailoring_{job_id}"] = False

# -----
# --- Initialize Session State
if "tracker_data" not in st.session_state:
    st.session_state.tracker_data = load_tracker()

if "plan_active" not in st.session_state:
    st.session_state.plan_active = False

if "skipped_data" not in st.session_state:
    st.session_state.skipped_data = load_skipped()

if "weekly_plan" not in st.session_state:
    saved_plan = load_weekly_plan()
    st.session_state.weekly_plan = saved_plan
    st.session_state.plan_active = bool(saved_plan)

    # Restore start and end dates from saved metadata if present
    if saved_plan and "_metadata" in saved_plan:
        st.session_state.plan_start_date = saved_plan["_metadata"].get("start_date")
        st.session_state.plan_end_date = saved_plan["_metadata"].get("end_date")

# ---------------------------------------------------------------------------
# Pydantic Schemas for AI Structured Output
# ---------------------------------------------------------------------------

class JobMatch(BaseModel):
    job_id: str = Field(description="The unique identifier or title of the job")
    title: str
    company: str = Field(default="Unknown Company", description="The hiring company name from the posting")
    match_percentage: float = Field(description="Calculated match percentage (0-100)")
    key_matching_skills: list[str] = Field(description="Skills in resume matching tech/keyword slugs")
    missing_skills: list[str] = Field(description="Required tech/experience missing from resume")
    reasoning: str = Field(description="Brief breakdown of how senior/skills match the score")

class MatchAnalysisResponse(BaseModel):
    matched_positions: list[JobMatch]



def load_resume_text(file_path: str) -> str:
    """
    Extracts text from a .pdf, .docx, or .txt file, saves plain text to a .txt file,
    and returns the path to that .txt file.
    """
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    if ext == ".pdf":
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

    elif ext == ".docx":
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])

    elif ext == ".txt":
        return file_path

    else:
        raise ValueError(f"Unsupported file format: {ext}. Use .pdf, .docx, or .txt")

    base_path = os.path.splitext(file_path)[0]
    txt_file_path = f"{base_path}.txt"

    with open(txt_file_path, "w", encoding="utf-8") as f:
        f.write(text)

    return txt_file_path


def format_date_posted(val):
    """Parses various ISO and localized date formats into standard YYYY-MM-DD."""
    if not val or pd.isna(val):
        return ""
    try:
        # pd.to_datetime automatically handles ISO timestamps, US dates (M/D/YYYY), etc.
        dt = pd.to_datetime(val, errors="coerce")
        return dt.strftime("%Y-%m-%d") if pd.notna(dt) else str(val)
    except Exception:
        return str(val)

def get_jobs(query_payload: dict, jobs_api_key: str, jobs_response_path: str, jobs_output_path: str):
    """
    Query JobsPipe API source for job listings using a dictionary payload.
    """

    try:
        resp = requests.post(
            "https://api.jobspipe.dev/v1/jobs/search",
            headers={"Authorization": "Bearer " + jobs_api_key},
            json=query_payload, 
            timeout=10
        )

        resp.raise_for_status()
        jobs = resp.json()

    except requests.exceptions.RequestException as e:
        # 1. Print detailed technical trace to the console/terminal where Streamlit is running.
        print(f"❌ JobsPipe API request failed: {e}")
        
        # 2. Display a clean UI message to the user
        st.error("⚠️ Couldn't fetch job listings right now. Please check your JobsPipe API key or network connection and try again later.")
        
        # 3. Gracefully stop Streamlit execution here so downstream steps don't crash
        st.stop()
   
    # Save formatted JSON response
    with open(jobs_response_path, "w", encoding="utf-8") as file:
        json.dump(jobs, file, indent=4, ensure_ascii=False)

    jobs_data = jobs.get('data', [])

    # 1. Create DataFrame directly from jobs_data
    df_jobs = pd.DataFrame(jobs_data)

    # 2. Format Date Posted column
    if "date_posted" in df_jobs.columns:
        df_jobs["date_posted"] = df_jobs["date_posted"].apply(format_date_posted)

    # 3. Rename columns and export to CSV
    df_jobs = df_jobs.rename(columns={
        "job_title": "Title",
        "company": "Company",
        "location": "Location",
        "date_posted": "Date Posted",
        "reposted": "Reposted?",
        "employment_statuses": "Employment type",
        "seniority": "Seniority",
        "url": "URL"
    })

    df_jobs[[
        'Title', 'Company', 'Location', 'Date Posted', 
        'Reposted?', 'Employment type', 'Seniority', 'URL'
    ]].to_csv(jobs_output_path, index=False, encoding='utf-8')

    return jobs


def analyze_job_matches(json_file_path, resume_file_path):
    """
    Analyze job descriptions against resume text using AI API (like Gemini) with thresholds 
    from config.yaml and prompts from prompts.yaml.
    Returns tuple: (advice_text, error_message)
    """

    # Implicit pickup by the SDK when client = genai.Client() is called without passing an explicit api_key parameter.
    if not os.getenv("GEMINI_API_KEY"):
        err_msg = "Gemini API Key missing! Enter it in the sidebar."
        st.error(f"⚠️ {err_msg}")
        return None, err_msg

    with open(json_file_path, "r", encoding="utf-8") as f:
        jobspipe_raw = json.load(f)

    with open(resume_file_path, "r", encoding="utf-8") as f:
        resume_text = f.read()

    # 1. Load match_threshold, selected_model, and temperature dynamically from config.yaml
    config_data = load_yaml(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else {}
    model_cfg = config_data.get("model_config", {})
    selected_model = model_cfg.get("selected_model", "gemini-2.5-flash")
    temperature = float(model_cfg.get("temperature", 0.2))
    raw_threshold = model_cfg.get("match_threshold", config_data.get("match_threshold", 75))

    # Format threshold string (e.g., handles numeric 75 -> "75%")
    match_threshold_str = f"{raw_threshold}%" if not str(raw_threshold).endswith("%") else str(raw_threshold)

    # 2. Load prompt template from prompts.yaml
    prompts_data = load_yaml(PROMPTS_FILE) if os.path.exists(PROMPTS_FILE) else {}
    prompt_template = prompts_data.get("system_prompts", {}).get("match_analyzer", "")

    # Fallback default template if prompts.yaml is missing or empty
    if not prompt_template:
        prompt_template = "Candidate Resume:\n{resume_text}\n\nJobs Payload:\n{jobspipe_data}\n\nFilter Threshold: {match_threshold}"

    # 3. Format template with dynamic runtime values
    prompt = prompt_template.format(
        match_threshold=match_threshold_str,
        resume_text=resume_text,
        jobspipe_data=json.dumps(jobspipe_raw, indent=2)
    )

    client = genai.Client()

    try:
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MatchAnalysisResponse,
                temperature=temperature,
                seed=42,     # For consistent Job Match Results, a fixed seed forces reproducible token generation along with temperature = 0.0.
                # Passing Pydantic schema via MatchAnalysisResponse. Gemini SDK's inspection logic misidentifies the schema as callable function tools, which can lead to unexpected state issues or infinite loops. Resolve by turning it off. 
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True) 	
            ),
        )

        # The JSON parsing is inside the try block so decode errors are caught.
        analysis_data = json.loads(response.text)
        matched_positions = analysis_data.get("matched_positions", [])

        matched_positions.sort(
            key=lambda job: job.get("match_percentage", 0), 
            reverse=True
        )

        output_payload = {
            "metadata": {
                "resume_path": resume_file_path,
                "jobs_source_path": json_file_path,
                "match_threshold": match_threshold_str
            },
            "matched_positions": matched_positions
        }

        # 2. Return payload and None for error_message
        return output_payload, None

    except APIError as api_err:
        err_msg = f"Gemini API Error ({api_err.code}): {api_err.message}"
        print(f"❌ Gemini API Error in analyze_job_matches() with selected model {selected_model}. {api_err}")
        return None, err_msg

    except Exception as e:
        err_msg = f"Failed to analyze job matches: {str(e)}"
        print(f"❌ Unexpected Error in analyze_job_matches(): {e}")
        return None, err_msg

    finally:
        if "is_analyzing_matches" in st.session_state:
            st.session_state.is_analyzing_matches = False



# ----------------------------------------------------
# --- Render the UI and handle UI interaction ---

# Sidebar: Global Settings & State 
with st.sidebar:
    st.title("⚙️ Global Setup")
    
    st.subheader("🔑 API Keys")
    jobspipe_key = st.text_input("JobsPipe API Key", value=os.getenv("JOBSPIPE_API_KEY", ""), type="password")
    gemini_key = st.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
      
    st.divider()

    # Section C Quick Stats in Sidebar
    st.subheader("🏆 Your Progress")
    
    tracker_data = st.session_state.get("tracker_data", [])
    applied_count = len(tracker_data)

    # Extract all non-empty application dates
    app_dates = [
        item["date_applied"] 
        for item in tracker_data 
        if item.get("date_applied") and str(item["date_applied"]).strip()
    ]

    # Set dynamic label based on the oldest date found
    if app_dates:
        oldest_date = min(app_dates)  # Standard YYYY-MM-DD strings sort naturally with min()
        metric_label = f"Total Jobs Applied since {oldest_date}"
    else:
        metric_label = "Total Jobs Applied"

    st.metric(label=metric_label, value=applied_count)
    
    if applied_count > 0:
        st.caption("🔥 Keep the momentum going!")




# --- Main Header ---
st.title("🚀 Job Search Center")
st.caption("Your local, AI-powered career assistant")

# --- Tabs Navigation (Easy to expand by adding new tab variables!) ---
tab_plan, tab_recruiter, tab_tracker, tab_config = st.tabs([
    "📅 Job Search Plan", 
    "🎯 Job Search & Resume Tailor", 
    "📊 Job Application Tracker",
    "🛠️ System Configuration Editor"
])


# ==============================================================================
# TAB A: WEEKLY JOB SEARCH PLAN
# ==============================================================================
with tab_plan:

    # --------------------------------------------------------------------------
    # SCREEN 1: PLAN SETUP SCREEN (When no active plan exists)
    # --------------------------------------------------------------------------
    if not st.session_state.get("plan_active", False):
        st.header("📅 Create Your Weekly Job Search Plan")
        st.markdown("Choose the specific job hunting activities and goals for this week.")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_date = st.date_input("Week Start Date", value=date.today())
        with col_d2:
            end_date = st.date_input(
                "Week End Date", 
                value=max(start_date, date.today() + pd.Timedelta(days=6)),
                min_value=start_date
            )

        # Date Validation Flag
        is_date_invalid = end_date < start_date

        if is_date_invalid:
            st.error("🚨 **Invalid Date Range:** Week End Date cannot be earlier than Week Start Date. Please fix the dates above to continue.")

        st.subheader("Select Activities for This Week")
        
        # Activity 1: Networking
        opt_net = st.checkbox("🤝 **Networking Outreach:** Contact 1st or 2nd degree connections at your target companies", help= "Create a list of the **Top 20** companies you would LOVE to work at. Next, make connections at those companies. For example, ask your 1st degree connections working at your Top 20 companies to introduce you to people who work on the same team as the job you are pursuing. Or ask your 1st degree connections to refer you for the job. Or send a cold introduction to someone who works in the same team/group as the job you desire. Etc.")
        net_target = 5
        if opt_net:
            net_target = st.number_input("Target Outreaches", min_value=1, value=5, step=1, key="setup_net")

        # Activity 2: Applications
        opt_app = st.checkbox("📝 **Job Applications:** Submit job applications", help="Apply for jobs primarily at your **Top 20** companies, then consider jobs at other companies.")
        app_target = 10
        if opt_app:
            app_target = st.number_input("Target Applications", min_value=1, value=10, step=1, key="setup_app")

        # Activity 3: Follow-ups
        opt_follow = st.checkbox("📞 **Follow-ups:** For **each** submitted job application above, find and contact the recruiter or hiring manager", help="Submitting a resume is not enough since the ATS system may likely reject it. Also, some positions are very competitive and receive hundreds or thousands of applications. Work around this situation by contacting a recruiter or hiring manager for **each** of the job applications you submitted.")
        follow_target = 10
        if opt_follow:
            follow_target = st.number_input("Target Follow-ups", min_value=1, value=10, step=1, key="setup_follow")

        # Activity 4: Master Resume Update
        opt_resume = st.checkbox("📈 **Master Resume / LinkedIn Update:** Document newer, measurable business impact from your current job", help="If you are currently working, this is a simple reminder to keep your resume and/or Linked In profile up to date with your most recent accomplishments. This makes it easier to modify your resume for future job applications you submit. Also, recruiters using outbound sourcing on Linked In can see your most recent accomplishments.")
        
        # Activity 5: Interview Prep
        opt_prep = st.checkbox("🗣️ **Interview Practice:** Practice technical or behavioral questions", help="Keep your interviews skills fresh since you never know when you will be invited to a phone screen or in-person interview! Practice interviews by getting sample questions on the web, then practice by yourself, with a friend, an AI interview coach or a real coach. Hint: Look up and use the 'STAR' method for behavioral interviews.")
        prep_target = 30
        if opt_prep:
            prep_target = st.number_input("Target Practice (Minutes)", min_value=15, value=30, step=15, key="setup_prep")

        # Activity 6: Wellness / Recharge
        opt_wellness = st.checkbox("🔋 **Pause & Recharge:** Planned activity to prevent burnout", help="Job hunting can be exhausting. Take some time during the weekly job search to recharge by doing something you really enjoy!")
        wellness_activity = ""
        if opt_wellness:
            wellness_activity = st.text_input("My Wellness Activity", placeholder="e.g., Play piano, 30-min walk, call family/friends, eat ice cream...")

        st.divider()

        if st.button("🚀 Launch Weekly Plan", type="primary", disabled=is_date_invalid):
            new_plan = {}

            if opt_net:
                new_plan["networking"] = {"title": "🤝 Networking Outreaches", "target": net_target, "current": 0, "unit": "contacts", "step": 1, "celebrated": False}

            if opt_app:
                new_plan["applications"] = {"title": "📝 Applications", "target": app_target, "current": 0, "unit": "applications", "step": 1, "celebrated": False}

            if opt_follow:
                new_plan["followups"] = {"title": "📞 Follow-ups", "target": follow_target, "current": 0, "unit": "follow-ups", "step": 1, "celebrated": False}

            if opt_resume:
                new_plan["resume_update"] = {"title": "📈 Master Resume & LinkedIn Update", "target": 1, "current": 0, "unit": "update", "step": 1, "celebrated": False}

            if opt_prep:
                new_plan["practice_mins"] = {"title": "🗣️ Interview Practice", "target": prep_target, "current": 0, "unit": "mins", "step": 15, "celebrated": False}

            if opt_wellness:
                new_plan["wellness"] = {"title": f"🔋 Recharge Activity ({wellness_activity or 'Wellness'})", "target": 1, "current": 0, "unit": "session", "step": 1, "celebrated": False}

            if new_plan:
                # Embed metadata into the plan dictionary so dates persist to disk
                new_plan["_metadata"] = {
                    "start_date": str(start_date),
                    "end_date": str(end_date)
                }

                # Update session state.
                st.session_state.weekly_plan = new_plan
                st.session_state.plan_start_date = start_date  
                st.session_state.plan_end_date = end_date     
                st.session_state.plan_active = True

                # Save full dictionary (including _metadata) to weekly_plan.json
                save_weekly_plan(st.session_state.weekly_plan)

                st.toast("Weekly Plan Created! Let's get to work! 🎯")
                st.rerun()
            else:
                st.warning("Please select at least one activity to create a plan.")

    # --------------------------------------------------------------------------
    # SCREEN 2: ACTIVE DASHBOARD (When plan is live)
    # --------------------------------------------------------------------------
    else:
        # Top Header Bar: Title + Delete Plan Option
        col_header, col_delete = st.columns([4, 1])
        
        with col_header:
            st.header("📅 Active Job Search Dashboard")
            
            # Retrieve saved dates and format nicely (e.g., "Aug 14, 2026")
            meta = st.session_state.weekly_plan.get("_metadata", {})
            start_dt = st.session_state.get("plan_start_date") or meta.get("start_date")
            end_dt = st.session_state.get("plan_end_date") or meta.get("end_date")
            
            if start_dt and end_dt:
                start_str = pd.to_datetime(start_dt).strftime("%b %d, %Y")
                end_str = pd.to_datetime(end_dt).strftime("%b %d, %Y")
                st.markdown(f"Track your live progress and celebrate your wins for **{start_str}** to **{end_str}**.")
            else:
                st.markdown("Track your live progress and celebrate your wins.")
            
        with col_delete:
            with st.popover("🗑️ Delete Plan"):
                st.warning("This will permanently delete this week's plan.")
                if st.button("Confirm Delete Plan", type="primary", key="confirm_delete"):
                    st.session_state.weekly_plan = {}
                    st.session_state.plan_active = False
                    st.session_state.plan_start_date = None
                    st.session_state.plan_end_date = None
                    save_weekly_plan({})
                    st.toast("Plan deleted. Ready to create a new one!", icon="🧹")
                    st.rerun()

        # Calculate Overall Execution Score (excluding _metadata)
        active_goals = [g for k, g in st.session_state.weekly_plan.items() if k != "_metadata"]
        
        total_target = sum(g["target"] for g in active_goals)
        total_current = sum(min(g["current"], g["target"]) for g in active_goals)
        overall_pct = int((total_current / total_target) * 100) if total_target > 0 else 0

        # --------------------------------------------------------------------------
        # AI WEEKLY PLAN ADVISOR
        # --------------------------------------------------------------------------
        if "is_advising" not in st.session_state:
            st.session_state.is_advising = False

        # Load saved advisor analysis on fresh app load if present
        if "advisor_result" not in st.session_state and os.path.exists(ADVISOR_OUTPUT):
            try:
                with open(ADVISOR_OUTPUT, "r", encoding="utf-8") as f:
                    st.session_state.advisor_result = json.load(f)
            except Exception:
                pass

        with st.expander("💡 **Weekly Plan Advisor - AI Strategic Job Search Insights**", expanded=False):
            st.caption("Get AI-powered recommendations based on your recent application statuses and your notes in the Job Application Tracker table.")
            
            col_adv_btn, _ = st.columns([1, 2])
            with col_adv_btn:
                # 1. Render button with state-managed disabled parameter
                if st.button(
                    "Analyze Application Tracker & Get Advice", 
                    key="run_weekly_advisor", 
                    disabled=st.session_state.is_advising
                ):
                    st.session_state.is_advising = True
                    st.rerun()

            # 2. Execution block triggered when is_advising is active
            if st.session_state.get("is_advising", False):
                # Update OS environment variable regardless of whether key is empty or populated
                os.environ["GEMINI_API_KEY"] = gemini_key if gemini_key else ""
                      
                with st.spinner("Analyzing your application history..."):
                    try:
                        advice_text, advice_error = get_weekly_plan_advice(TRACKER_DB, PLAN_DB)

                        if advice_error:
                            # Save error to state so it renders in the UI
                            st.session_state.advisor_error = f"⚠️ {advice_error}"
                            if "advisor_result" in st.session_state:
                                del st.session_state.advisor_result
            
                                # Clean up old output file so stale "None" values aren't loaded
                                if os.path.exists(ADVISOR_OUTPUT):
                                     try:
                                         os.remove(ADVISOR_OUTPUT)
                                     except OSError:
                                         pass

                        elif advice_text:
                            # Clear previous error on success
                            if "advisor_error" in st.session_state:
                                del st.session_state.advisor_error
            
                            run_date = date.today().strftime("%Y-%m-%d")
                            advisor_payload = {
                                "last_run_date": run_date,
                                "advice_text": advice_text
                            }

                            # Save results to agent_weekly_advisor.json
                            with open(ADVISOR_OUTPUT, "w", encoding="utf-8") as f:
                                json.dump(advisor_payload, f, indent=4, ensure_ascii=False)

                            st.session_state.advisor_result = advisor_payload
                            st.toast("Strategic advice updated and saved!", icon="💡")

                    except Exception as e:
                        st.session_state.advisor_error = f"⚠️ Error during execution: {str(e)}"
                    finally:
                        # Re-enable button after completion or error
                        st.session_state.is_advising = False
                        st.rerun()

            # 3. Display Block (Renders errors or results when NOT actively analyzing)
            if st.session_state.get("advisor_error"):
                st.error(st.session_state.advisor_error)

            elif st.session_state.get("advisor_result") or os.path.exists(ADVISOR_OUTPUT):
                # Load from disk if not already in session_state
                if "advisor_result" not in st.session_state and os.path.exists(ADVISOR_OUTPUT):
                    try:
                        with open(ADVISOR_OUTPUT, "r", encoding="utf-8") as f:
                            st.session_state.advisor_result = json.load(f)
                    except Exception:
                        st.session_state.advisor_result = None

                result = st.session_state.get("advisor_result")
                if isinstance(result, dict) and result.get("advice_text"):
                    st.markdown(f"**Strategic Job Search Insights as of {result.get('last_run_date', 'N/A')}:**")
                    st.info(result.get("advice_text"))

        st.metric("🏆 Overall Weekly Execution Score", f"{overall_pct}%")
        st.progress(overall_pct / 100)

        # 100% Completion Workflow -> Returns to Setup Screen
        if overall_pct >= 100:
            # Fire balloons ONCE while the plan is still marked active, then deactivate it so choosing the save button after reaching 100% won't trigger the balloons.
            if st.session_state.plan_active:
                st.balloons()
                st.session_state.plan_active = False

            # This banner and button remain on screen on subsequent reruns without firing balloons again
            st.success("🎉 **CONGRATULATIONS! You completed 100% of your weekly job search plan!**")
            if st.button("🚀 Create New Plan for Next Week", type="primary"):
                st.session_state.weekly_plan = {}
                save_weekly_plan({})
                st.rerun()

        st.divider()

        # Render Active Goal Cards Dynamically
        for key, goal in st.session_state.weekly_plan.items():
            # Skip _metadata dictionary so it isn't rendered as a goal card
            if key == "_metadata":
                continue

            # 4 top-level columns with vertical_alignment="center"
            col_title, col_status, col_add, col_sub = st.columns(
                [4.5, 1.5, 0.5, 0.5], 
                vertical_alignment="center"
            )

            step_val = goal.get("step", 1)

            # Column 1: Activity Title & Progress Bar
            with col_title:
                st.markdown(f"### {goal['title']}")
                st.progress(min(goal["current"] / goal["target"], 1.0))
                st.caption(f"Status: **{goal['current']} of {goal['target']} {goal['unit']}** logged.")

            # Column 2: Status Banner
            with col_status:
                if goal["current"] >= goal["target"]:
                    st.success("🏆 Goal Smashed!")
                else:
                    st.info(f"Need {goal['target'] - goal['current']} more {goal['unit']}")

            # Column 3: Plus / Add Button (+ Log+)
            with col_add:
                if st.button(f"➕ Log +{step_val}", key=f"add_{key}"):
                    goal["current"] += step_val
                    save_weekly_plan(st.session_state.weekly_plan)
                    st.toast(f"Logged +{step_val} {goal['unit']}! 🚀")
                    
                    if goal["current"] >= goal["target"] and not goal["celebrated"]:
                        goal["celebrated"] = True
                        st.balloons()
                        st.toast(f"🎉 Goal Smashed: {goal['title']}!", icon="🏆")
                    st.rerun()

            # Column 4: Minus / Undo Button (- Log-)
            with col_sub:
                is_zero = goal["current"] <= 0
                if st.button(
                    f"➖ Log -{step_val}", 
                    key=f"sub_{key}", 
                    disabled=is_zero,
                    type="secondary"
                ):
                    goal["current"] = max(0, goal["current"] - step_val)
                    
                    # Reset celebration flag if progress drops back below target
                    if goal["current"] < goal["target"]:
                        goal["celebrated"] = False
                        
                    save_weekly_plan(st.session_state.weekly_plan)

                    st.toast(f"Undid log (-{step_val} {goal['unit']}). Current: {goal['current']}", icon="↩️")
                    st.rerun()

            st.divider()


# ==============================================================================
# TAB B: EXPERT AI JOB SEARCH, RESUME MATCH & GENERATE TAILORED RESUME
# ==============================================================================
with tab_recruiter:
    st.header("🎯 Job Search & Resume Tailor")
    
    # --------------------------------------------------------------------------
    # Step 1: Select Active Resume
    # --------------------------------------------------------------------------
    st.subheader("1. Select Active Resume")

    # Target folder for all user uploads. Creates folder if it doesn't exist yet.
    os.makedirs(UPLOADS, exist_ok=True)  

    # File uploader to browse your local hard drive
    uploaded_file = st.file_uploader(
        "Upload a resume from your hard drive (.pdf, .docx, .txt)", 
        type=["pdf", "docx", "txt"]
    )

    # State tracking: Only save and toast ONCE per new file upload
    if "last_uploaded_resume" not in st.session_state:
        st.session_state.last_uploaded_resume = None

    if uploaded_file is not None and st.session_state.last_uploaded_resume != uploaded_file.name:
        # Construct target path inside UPLOADS. 
        save_path = os.path.join(UPLOADS, uploaded_file.name)
        
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        st.session_state.last_uploaded_resume = uploaded_file.name
        st.toast(f"Uploaded '{uploaded_file.name}' to '{UPLOADS}'.", icon="📄")

    # Scan directory for all resume files
    resume_files = [f for f in os.listdir(UPLOADS) if f.endswith((".pdf", ".docx", ".txt"))]
    
    # Automatically select the newly uploaded file in the dropdown if present
    default_index = 0
    if uploaded_file and uploaded_file.name in resume_files:
        default_index = resume_files.index(uploaded_file.name)

    selected_resume = st.selectbox(
        "Choose Active Resume File", 
        resume_files if resume_files else ["No resumes found"],
        index=default_index,
        help="Select the resume version you want AI to compare against the job results query."
    )

    st.divider()

    # --------------------------------------------------------------------------
    # Step 2: Select JobsPipe Query YAML & Target Preset
    # --------------------------------------------------------------------------
    st.subheader("2. Select Job Source Query")

    uploaded_yaml = st.file_uploader(
        "Upload a Query YAML file (.yaml, .yml)", 
        type=["yaml", "yml"],
        key="query_yaml_uploader"
    )

    # State tracking: Only save and toast ONCE per new YAML upload
    if "last_uploaded_yaml" not in st.session_state:
        st.session_state.last_uploaded_yaml = None

    if uploaded_yaml is not None and st.session_state.last_uploaded_yaml != uploaded_yaml.name:
        os.makedirs("config", exist_ok=True)
        save_path = os.path.join(UPLOADS, uploaded_yaml.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_yaml.getbuffer())
        st.session_state.last_uploaded_yaml = uploaded_yaml.name
        st.toast(f"Saved '{uploaded_yaml.name}' to '{UPLOADS}'.", icon="⚙️")

    # Scan both root (.) and config/ subdirectories for query YAML files
    yaml_files = []
    for search_dir in [".", "config"]:
        if os.path.exists(search_dir):
            for f in os.listdir(search_dir):
                if f.endswith((".yaml", ".yml")) and f not in [CONFIG_FILE, PROMPTS_FILE]:
                    full_path = os.path.normpath(os.path.join(search_dir, f))
                    if full_path not in yaml_files:
                        yaml_files.append(full_path)

    default_yaml_idx = 0
    if uploaded_yaml:
        uploaded_norm_path = os.path.normpath(os.path.join("config", uploaded_yaml.name))
        if uploaded_norm_path in yaml_files:
            default_yaml_idx = yaml_files.index(uploaded_norm_path)

    col_y1, col_y2 = st.columns(2)

    with col_y1:
        selected_yaml_file = st.selectbox(
            "Choose Job Query YAML File", 
            yaml_files if yaml_files else ["No YAML query files found"],
            index=default_yaml_idx if yaml_files else 0
        )

    selected_query_payload = None

    if selected_yaml_file and selected_yaml_file != "No YAML query files found":
        yaml_data = load_yaml(selected_yaml_file)
        queries = yaml_data.get("queries", {}) if isinstance(yaml_data, dict) else {}

        with col_y2:
            query_names = list(queries.keys())
            selected_query_name = st.selectbox(
                "Choose Job Title to Query", 
                query_names if query_names else ["No queries found in file"]
            )

        if selected_query_name and selected_query_name != "No queries found in file":
            raw_query = queries[selected_query_name]
            
            if isinstance(raw_query, str):
                selected_query_payload = json.loads(raw_query)
            elif isinstance(raw_query, dict):
                selected_query_payload = raw_query

            with st.expander("👁️ View Selected Job Query", expanded=False):
                st.json(selected_query_payload)

    st.divider()

    # --------------------------------------------------------------------------
    # Step 3: Run Analysis with Single-Container Progress Tracking
    # --------------------------------------------------------------------------
    if "is_analyzing" not in st.session_state:
        st.session_state.is_analyzing = False
    if "last_analysis_logs" not in st.session_state:
        st.session_state.last_analysis_logs = []
    if "last_analysis_error" not in st.session_state:
        st.session_state.last_analysis_error = None

    # Render button (disabled while analysis is active)
    if st.button(
        "🔍 Find Job Matches with AI", 
        type="primary", 
        disabled=st.session_state.is_analyzing
    ):
        st.session_state.is_analyzing = True
        st.session_state.last_analysis_logs = []
        st.session_state.last_analysis_error = None
        st.rerun()

    # --------------------------------------------------------------------------
    # SINGLE CONTAINER SWITCHER (Renders live execution OR prior results)
    # --------------------------------------------------------------------------
    
    # 1. LIVE EXECUTION (Renders ONLY while active processing is happening)
    if st.session_state.is_analyzing:
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key

        if selected_resume == "No resumes found":
            st.session_state.last_analysis_error = "⚠️ Please select or upload a valid resume file."
            st.session_state.is_analyzing = False
            st.rerun()
        elif selected_query_payload is None:
            st.session_state.last_analysis_error = "⚠️ Please select a valid query preset from your Query.YAML file."
            st.session_state.is_analyzing = False
            st.rerun()
        else:
            try:
                with st.status("🚀 Running Job Match Analysis...", expanded=True) as status:
                    
                    # Step 1: Extract Resume Text
                    resume_full_path = os.path.join(UPLOADS, selected_resume)
                    txt_resume_path = load_resume_text(resume_full_path)

                    msg_1 = f"✓ Step 1 of 4: Extracted text from `{txt_resume_path}`"
                    st.write(msg_1)
                    st.session_state.last_analysis_logs.append(msg_1)

                    # Step 2: Fetch Job Listings
                    if jobspipe_key:
                        msg_2 = "🕕 Step 2 of 4: Querying JobsPipe API for job listings..."
                        st.write(msg_2)
                        st.session_state.last_analysis_logs.append(msg_2)

                        get_jobs(selected_query_payload, jobspipe_key, JOBS_RESPONSE, JOBS_OUTPUT)
                        msg_2 = "✓ Step 2 of 4: Retrieved fresh job postings from JobsPipe API."
                    elif os.path.exists(JOBS_RESPONSE):
                        msg_2 = f"ℹ️ Step 2 of 4: No JobsPipe API key provided; reusing local `{JOBS_RESPONSE}`"
                    else:
                        raise FileNotFoundError(f"No JobsPipe API key provided and `{JOBS_RESPONSE}` does not exist yet.")
                    
                    st.write(msg_2)
                    st.session_state.last_analysis_logs.append(msg_2)

                    # Step 3: Run AI Analysis
                    msg_3_start = "🕘 Step 3 of 4: Calculating jobs and resume match scores with Gemini AI..."
                    st.write(msg_3_start)
                    st.session_state.last_analysis_logs.append(msg_3_start)

                    analysis_result, api_error_msg = analyze_job_matches(JOBS_RESPONSE, txt_resume_path)
                    if analysis_result is None:
                        # Append the detailed API error string directly into the expander logs
                        detailed_error = api_error_msg or "Unknown error occurred during API request."
                        st.session_state.last_analysis_logs.append(f"❌ {detailed_error}")

                        raise RuntimeError(f"Gemini AI match analysis failed: {detailed_error}")
                    
                    msg_3_end = "✓ Step 3 of 4: Match evaluation complete"
                    st.write(msg_3_end)
                    st.session_state.last_analysis_logs.append(msg_3_end)

                    # Step 4: Save Analysis Results
                    with open(AGENT_OUTPUT, "w", encoding="utf-8") as f:
                        json.dump(analysis_result, f, indent=4, ensure_ascii=False)
                    
                    msg_4 = f"🎉 Step 4 of 4: Analysis complete! Saved raw results to `{AGENT_OUTPUT}`. See same results below."
                    st.write(msg_4)
                    st.session_state.last_analysis_logs.append(msg_4)

                    status.update(label="🎉 Analysis complete!", state="complete", expanded=False)

            except Exception as e:
                error_msg = f"Error during execution: {str(e)}"
                
                # 1. Update live st.status box to red error state
                status.update(label="❌ Job Match Analysis Failed", state="error", expanded=True)
                st.error(error_msg)
                
                # 2. Save error to session state for persistent expander after rerun
                st.session_state.last_analysis_error = error_msg
                
                # 3. Clean up stale output file so Section 3 doesn't crash on rerun
                if os.path.exists(AGENT_OUTPUT):
                    try:
                        os.remove(AGENT_OUTPUT)
                    except OSError:
                        pass
            finally:
                st.session_state.is_analyzing = False
                st.rerun()

    # 2. HISTORICAL LOGS (Renders ONLY after execution finishes or fails)
    elif st.session_state.last_analysis_logs or st.session_state.last_analysis_error:
        has_error = st.session_state.last_analysis_error is not None
        with st.expander("🚀 **Job Match Analysis Status & Logs**", expanded=has_error):
            for log in st.session_state.last_analysis_logs:
                st.caption(log)
            if st.session_state.last_analysis_error:
                st.error(st.session_state.last_analysis_error)


    # --------------------------------------------------------------------------
    # Step 3: Job Match Results
    # --------------------------------------------------------------------------
    st.subheader("3. Job Match Results", help= "Shows the exact settings used at the moment AI compared your resume to job descriptions. Later, if Model Configurations under System Prompts & Config are changed, then Find Job Matches will need to be chosen again.")
    
    if os.path.exists(AGENT_OUTPUT):
        with open(AGENT_OUTPUT, "r", encoding="utf-8") as f:
            match_results = json.load(f)

        # 1. Map details from jobs.json
        job_details_map = {}
        if os.path.exists(JOBS_RESPONSE):
            try:
                with open(JOBS_RESPONSE, "r", encoding="utf-8") as jf:
                    raw_jobs = json.load(jf).get("data", [])
                    for rj in raw_jobs:
                        jid = str(rj.get("id") or rj.get("job_id") or rj.get("job_title") or "")
                        if jid:
                            job_details_map[jid] = {
                                "url": rj.get("url", ""),
                                "company": rj.get("company", "")
                            }
            except Exception as e:
                st.caption(f"Note: Could not map details from {JOBS_RESPONSE}: {e}")

        st.json(match_results.get("metadata", {}))
        
        matches = match_results.get("matched_positions", [])
        if not matches:
            st.info("No matching jobs found above the Match Threshold (%) set in the System Prompts & Config section.")
            
        # Get active tracking states
        applied_job_ids = [str(item.get("job_id")) for item in st.session_state.tracker_data]
        skipped_job_ids = [str(jid) for jid in st.session_state.skipped_data]

        for idx, job in enumerate(matches):
            job_id_str = str(job.get("job_id", ""))
            
            # Determine 3-state status
            is_applied = job_id_str in applied_job_ids
            is_skipped = job_id_str in skipped_job_ids

            mapped_info = job_details_map.get(job_id_str, {})
            source_url = mapped_info.get("url") or job.get("url", "")
            actual_company = mapped_info.get("company") or job.get("company", "Unknown Company")

            with st.expander(f"⭐ {job.get('match_percentage')}% Match | {job.get('title')} ({actual_company})"):
                
                if source_url:
                    st.markdown(
                        f"**Source URL:** <a href='{source_url}' target='_blank' title='{source_url}' "
                        f"style='color: #1a0dab; text-decoration: underline; word-break: break-all;'>{source_url}</a>",
                        unsafe_allow_html=True
                    )

                # Format key matching skills into Title Case with spaces
                key_skills = [s.replace("-", " ").title() for s in job.get("key_matching_skills", [])]
                key_skills_str = ", ".join(key_skills) if key_skills else "None listed"

                # Format missing skills into Title Case with spaces
                missing_list = [s.replace("-", " ").title() for s in job.get("missing_skills", [])]
                missing_str = (
                    ", ".join(missing_list) 
                    if missing_list 
                    else "There doesn't seem to be any missing skills, however you should double-check the job requirements."
                )

                st.write(f"**Company:** {actual_company}")
                st.write(f"**Reasoning:** {job.get('reasoning')}")
                st.write(f"**Key Matching Skills:** {key_skills_str}")
                st.write(f"**Missing Skills:** {missing_str}")

                col_btn1, col_btn2 = st.columns(2)
                tailored_key = f"tailored_resume_{job_id_str}"
                error_key = f"tailor_error_{job_id_str}"

                with col_btn1:
                    if st.button("✨ Generate Tailored Resume", key=f"tailor_{idx}"):
                        # 1. Clear any previous error message state immediately
                        if error_key in st.session_state:
                            del st.session_state[error_key]

                        # 2. Unconditionally sync API key (passes empty string if missing)
                        os.environ["GEMINI_API_KEY"] = gemini_key if gemini_key else ""

                        resume_full_path = os.path.join(UPLOADS, selected_resume)

                        with st.spinner(f"Tailoring resume for {job.get('title')}..."):
                            try:
                                tailored_text, tailored_error = generate_tailored_resume(resume_full_path, job)
    
                                if tailored_error:
                                    # Save error to state so it renders in your UI error block
                                    st.session_state[error_key] = f"⚠️ {tailored_error}"
                                elif tailored_text:
                                    st.session_state[tailored_key] = tailored_text
                                    st.toast("Tailored resume generated!", icon="✨")

                            except Exception as e:
                                st.session_state[error_key] = f"⚠️ API Error generating tailored resume: {str(e)}"
                                
                with col_btn2:
                    st.write("**Did you apply for this position?**")
                    c1, c2 = st.columns(2)

                    # Dynamic Button States & Labels
                    yes_label = "✅ Applied" if is_applied else "Yes"
                    no_label = "🚫 Skipped" if is_skipped else "No"
                    
                    yes_disabled = is_applied
                    no_disabled = is_skipped

                    # YES BUTTON
                    if c1.button(yes_label, key=f"yes_{idx}", disabled=yes_disabled):
                        # If transition from Skipped -> Applied, clear skipped status
                        if is_skipped:
                            st.session_state.skipped_data = [j for j in st.session_state.skipped_data if str(j) != job_id_str]
                            save_skipped(st.session_state.skipped_data)

                        # Calculate current date and 5-day follow-up target
                        today_dt = date.today()
                        followup_dt = today_dt + timedelta(days=5)

                        # Add to Tracker DB
                        new_app = {
                            "job_id": job_id_str,
                            "title": job.get("title"),
                            "company": actual_company,
                            "date_applied": str(date.today()),
                            "followup_date": str(followup_dt),
                            "status": "Applied",
                            "url": source_url or "Not found.",
                            "notes": f"Matched via Job Search using {selected_resume}"
                        }
                        st.session_state.tracker_data.append(new_app)
                        save_tracker(st.session_state.tracker_data)

                        # Increment Tab A counter (+1)
                        if st.session_state.get("plan_active", False) and "applications" in st.session_state.weekly_plan:
                            app_goal = st.session_state.weekly_plan["applications"]
                            app_goal["current"] += 1
                            save_weekly_plan(st.session_state.weekly_plan)

                            if app_goal["current"] >= app_goal["target"] and not app_goal["celebrated"]:
                                app_goal["celebrated"] = True
                                st.balloons()
                                st.toast("🎉 Goal Smashed: Applications target reached!", icon="🏆")
                            else:
                                st.toast(f"Application logged in the Job Application Tracker! ({app_goal['current']}/{app_goal['target']}) 🎯")

                        st.success(f"Saved {actual_company} application to Application Tracker!")
                        st.rerun()

                    # NO BUTTON
                    if c2.button(no_label, key=f"no_{idx}", disabled=no_disabled):
                        if is_applied:
                            # Revert Applied -> Neutral: Remove from Tracker DB
                            st.session_state.tracker_data = [
                                item for item in st.session_state.tracker_data 
                                if str(item.get("job_id")) != job_id_str
                            ]
                            save_tracker(st.session_state.tracker_data)

                            # Decrement Tab A counter (-1)
                            if st.session_state.get("plan_active", False) and "applications" in st.session_state.weekly_plan:
                                app_goal = st.session_state.weekly_plan["applications"]
                                app_goal["current"] = max(0, app_goal["current"] - 1)
                                save_weekly_plan(st.session_state.weekly_plan)

                                if app_goal["current"] < app_goal["target"]:
                                    app_goal["celebrated"] = False
                                st.toast("Application removed & Weekly Job Search Plan updated ↩️", icon="↩️")

                            st.warning(f"Reverted {actual_company} application.")
                            st.rerun()
                        else:
                            # Move Neutral -> Skipped: Save to skipped_jobs.json
                            st.session_state.skipped_data.append(job_id_str)
                            save_skipped(st.session_state.skipped_data)
                            st.info("Job marked as skipped.")
                            st.rerun()

                # Render active error message if present in state
                if error_key in st.session_state:
                    st.error(st.session_state[error_key])

                # Render Tailored Resume Output & Download Option if generated
                if tailored_key in st.session_state:
                    st.divider()
                    st.markdown("#### 📄 Tailored Resume Output")
                    
                    st.text_area(
                        "Review and copy your tailored resume:",
                        value=st.session_state[tailored_key],
                        height=350,
                        key=f"area_{tailored_key}"
                    )
                    
                    company_clean = actual_company.replace(" ", "_").strip()
                    st.download_button(
                        label="💾 Download Tailored Resume (.txt)",
                        data=st.session_state[tailored_key],
                        file_name=f"Tailored_Resume_{company_clean}.txt",
                        mime="text/plain",
                        key=f"dl_{tailored_key}"
                    )

    else:
        st.info("No match output found. Select your resume and query file above, then click 'Analyze Job Matches'.")


    # ==============================================================================
    # TAB C: APPLICATION TRACKER
    # ==============================================================================

    with tab_tracker:
        st.header("📋 Job Application Tracker")
        st.write("View and edit your logged job applications below.")

        # New code begin

        # --------------------------------------------------------------------------
        # Follow-up Status Summary Banner
        # --------------------------------------------------------------------------
        today_dt = date.today()
        tomorrow_dt = today_dt + timedelta(days=1)

        due_past_or_today = 0
        due_tomorrow = 0

        for item in st.session_state.tracker_data:
            f_val = item.get("followup_date")
            if f_val and not pd.isna(f_val):
                try:
                    # Convert string / Timestamp / date to standard date object
                    f_date = pd.to_datetime(f_val).date()
                
                    if f_date <= today_dt:
                        due_past_or_today += 1
                    elif f_date == tomorrow_dt:
                        due_tomorrow += 1
                except Exception:
                    pass

        # Render dynamic status messages based on counts
        if due_past_or_today == 0 and due_tomorrow == 0:
            st.info("No follow-ups today or tomorrow.")
        else:
            if due_past_or_today > 0:
                unit_str = "follow-up" if due_past_or_today == 1 else "follow-ups"
                st.warning(f"⚠️ You have **{due_past_or_today} {unit_str}** below that are past due or due today.")
        
            if due_tomorrow > 0:
                unit_str = "follow-up" if due_tomorrow == 1 else "follow-ups"
                st.info(f"📅 You have **{due_tomorrow} {unit_str}** below to complete tomorrow.")
            # New code end.


        # 1. Initialize tracker state and original snapshot
        if "tracker_data" not in st.session_state:
            st.session_state.tracker_data = load_tracker()

        if "tracker_original" not in st.session_state:
            st.session_state.tracker_original = json.loads(json.dumps(st.session_state.tracker_data))

        if st.session_state.tracker_data:
            df = pd.DataFrame(st.session_state.tracker_data)

            # Ensure followup_date exists in DataFrame even if legacy records lack it
            if "followup_date" not in df.columns:
                df["followup_date"] = None

            # Convert date columns to date objects for clean calendar widget editing
            if "applied_date" in df.columns:
                df["applied_date"] = pd.to_datetime(df["applied_date"]).dt.date
            if "followup_date" in df.columns:
                df["followup_date"] = pd.to_datetime(df["followup_date"]).dt.date

            # 2. Filtering UI (Multi-Select Status Filter)
            all_statuses = df["status"].unique() if "status" in df.columns else []
            
            col_f1, _ = st.columns([1, 1])
            with col_f1:
                status_filter = st.multiselect("Filter Status", all_statuses, default=all_statuses)

            # Filter dataframe based on multi-select choices
            if "status" in df.columns and status_filter:
                filtered_df = df[df["status"].isin(status_filter)]
            else:
                filtered_df = df

            # 3. Render Data Editor
            # Allow row addition/deletion only when all statuses are visible
            is_full_view = len(status_filter) == len(all_statuses) if len(all_statuses) > 0 else True

            # Render Data Editor with strict DateColumn enforcement
            edited_df = st.data_editor(
                filtered_df,
                height=400,      # Explicitly set pixel height before vertical scrollbar appears.
                column_order=[
                    "company", 
                    "date_applied", 
                    "followup_date", 
                    "status", 
                    "notes", 
                    "url"
                ],
                num_rows="dynamic" if is_full_view else "fixed",
                width='stretch',
                column_config={
                    "company": st.column_config.TextColumn("Company"),
                    "applied_date": st.column_config.DateColumn("Date Applied", format="YYYY-MM-DD"),
                    "followup_date": st.column_config.DateColumn("Follow-up Date", format="YYYY-MM-DD", help="Target date you expect to hear back from the hiring company OR the date you will need to do something. If no further follow-ups, like you got a rejection :-( then delete the Follow-up Date which sill set it to None."),
                    "status": st.column_config.TextColumn("Status", help="Add your own job hunting status here. Suggest to create as few labels as possible. Also, use labels consistently."),
                    "notes": st.column_config.TextColumn("Notes", width="medium", help="Add details like recruiter feedback, key missing skills, or interview progress. The more details you add the richer insights the AI Weekly Plan Advisor will provide!"),
                    "url": st.column_config.LinkColumn("Job Link", help="Click to open the job posting"),
                },
                key="tracker_editor"
            )

            # Convert DataFrame to records
            raw_records = edited_df.to_dict(orient="records")

            # Clean all NaT, NaN, and Timestamp objects across all dictionary keys
            edited_df_clean = []
            for row in raw_records:
                clean_row = {}
                for k, v in row.items():
                    if pd.isna(v) or str(v).strip().lower() in ["nat", "<nat>", "nan", "none"]:
                        clean_row[k] = ""
                    else:
                        clean_row[k] = str(v) if isinstance(v, (date, pd.Timestamp)) else v
                edited_df_clean.append(clean_row)

            # 4. Merge edits back into the full dataset
            if is_full_view:
                current_full_data = edited_df_clean
            else:
                edited_map = {str(r.get("job_id")): r for r in edited_df_clean if r.get("job_id") is not None}

                current_full_data = []
                for item in st.session_state.tracker_data:
                    jid = str(item.get("job_id"))
                    if jid in edited_map:
                        current_full_data.append(edited_map[jid])
                    else:
                        current_full_data.append(item)

            # 5. Check for unsaved changes against original snapshot
            has_changes = current_full_data != st.session_state.tracker_original

            col_save, col_info = st.columns([1, 3])

            with col_save:
                if st.button("💾 Save Tracker Changes", type="primary", disabled=not has_changes):
                    st.session_state.tracker_data = current_full_data
                    save_tracker(current_full_data)
                    st.session_state.tracker_original = json.loads(json.dumps(current_full_data))
                    st.toast("Application Tracker changes saved!", icon="💾")
                    st.rerun()

            with col_info:
                if has_changes:
                    st.caption("⚠️ You have unsaved changes in the table above.")
                else:
                    st.caption("✓ All changes saved.")

        else:
            st.info("No applications tracked yet. Apply for jobs in the Job Search & Resume Tailor tab to automatically record them here or manually add your own!")


# ==============================================================================
# TAB CONFIG: MODEL CONFIGS & PROMPTS MANAGEMENT
# ==============================================================================
with tab_config:
    st.header("🛠️ System Configuration Editor")
    st.markdown("Modify AI model settings and system prompts live without touching Python code.")

    config_data = load_yaml(CONFIG_FILE)
    prompts_data = load_yaml(PROMPTS_FILE)

    col_cfg1, col_cfg2 = st.columns(2)

    with col_cfg1:
        st.subheader("Model Configuration (`config.yaml`)")
        
        # 1. Initialize original baseline snapshot in session state
        if "config_original" not in st.session_state:
            st.session_state.config_original = json.loads(json.dumps(config_data)) if config_data else {}

        if config_data:
            model_cfg = config_data.get("model_config", {})
            
            # Inputs
            selected_m = st.selectbox(
                "AI Model", 
                model_cfg.get("available_models", ["gemini-2.5-flash"]),
                index=model_cfg.get("available_models", ["gemini-2.5-flash"]).index(model_cfg.get("selected_model", "gemini-2.5-flash")) if model_cfg.get("selected_model") in model_cfg.get("available_models", []) else 0
            )
            temp = st.slider(
                "Temperature", 
                0.0, 1.0, 
                float(model_cfg.get("temperature", 0.2)), 
                help="Temperature defines how much creativity AI provides when it creates the % Match, Reasoning, Key Matching Skills, and Missing Skills fields under the Job Match Results. Low Temperature (0.1 to 0.3) makes the model highly deterministic, logical, and focused when writing these fields. It repeatedly chooses the most probable tokens and more precise matching. Setting temperature = 0.2 ensures mostly consistent and objective evaluation text every time you run the analysis against your resume and job listings. Set temperature = 0.0 to get consistent match evaluations across runs."
            )
            threshold = st.slider(
                "Match Threshold (%)", 
                50, 100, 
                int(model_cfg.get("match_threshold", 75)), 
                help="The Match Threshold acts as a quality filter. Set at 75% to instruct AI to strictly discard any job listings where the resume achieves an overall evaluation score below 75% out of 100. Only positions that meet or exceed this 75% benchmark are returned and displayed in the UI and saved to the local file agent_job_analysis.json. This ensures you focus your time and effort exclusively on high-fit opportunities that align with your domain, hard skills, seniority, and qualifications."
            )

            # 2. Build current config dictionary to check against baseline snapshot
            current_config_data = json.loads(json.dumps(config_data))
            current_config_data["model_config"]["selected_model"] = selected_m
            current_config_data["model_config"]["temperature"] = temp
            current_config_data["model_config"]["match_threshold"] = threshold

            has_config_changes = current_config_data != st.session_state.config_original

            # 3. Save Button + Status Message Layout
            col_save, col_info = st.columns([1, 2])

            with col_save:
                if st.button(
                    "💾 Save Model Config",
                    type="primary" if has_config_changes else "secondary",
                    disabled=not has_config_changes,
                    key="btn_save_model_config"
                ):
                    config_data["model_config"]["selected_model"] = selected_m
                    config_data["model_config"]["temperature"] = temp
                    config_data["model_config"]["match_threshold"] = threshold
                    
                    save_yaml(CONFIG_FILE, config_data)
                    st.session_state.config_original = json.loads(json.dumps(config_data))
                    st.toast("Saved model config!", icon="⚙️")
                    st.rerun()

            with col_info:
                if has_config_changes:
                    st.caption("⚠️ You have unsaved changes in the settings above.")
                else:
                    st.caption("✓ All changes saved.")

    with col_cfg2:
        st.subheader("System Prompts (`prompts.yaml`)")

        # 1. Initialize original baseline snapshot in session state
        if "prompts_original" not in st.session_state:
            st.session_state.prompts_original = json.loads(json.dumps(prompts_data)) if prompts_data else {}

        if prompts_data:
            prompts = prompts_data.get("system_prompts", {})
            p_match = st.text_area("Match Analyzer Prompt", prompts.get("match_analyzer", ""), height=150, help="AI prompt to evaluate job postings against your resume.")
            p_tailor = st.text_area("Resume Tailor Prompt", prompts.get("resume_tailor", ""), height=150, help="AI prompt to tailor a resume to your chosen job descriptions.")
            p_advisor = st.text_area("Weekly Plan Advisor", prompts.get("weekly_plan_advisor", ""), height=150, help="AI prompt to generate feedback on your weekly job search plan.")

            # 2. Build current prompts dictionary to check against baseline snapshot
            current_prompts_data = json.loads(json.dumps(prompts_data))
            if "system_prompts" not in current_prompts_data:
                current_prompts_data["system_prompts"] = {}

            current_prompts_data["system_prompts"]["match_analyzer"] = p_match
            current_prompts_data["system_prompts"]["resume_tailor"] = p_tailor
            current_prompts_data["system_prompts"]["weekly_plan_advisor"] = p_advisor

            has_prompt_changes = current_prompts_data != st.session_state.prompts_original

            # 3. Save Button + Status Message Layout
            col_save, col_info = st.columns([1, 2])

            with col_save:
                if st.button(
                    "💾 Save Prompts Config",
                    type="primary" if has_prompt_changes else "secondary",
                    disabled=not has_prompt_changes,
                    key="btn_save_prompts_config"
                ):
                    prompts_data["system_prompts"]["match_analyzer"] = p_match
                    prompts_data["system_prompts"]["resume_tailor"] = p_tailor
                    prompts_data["system_prompts"]["weekly_plan_advisor"] = p_advisor

                    save_yaml(PROMPTS_FILE, prompts_data)
                    st.session_state.prompts_original = json.loads(json.dumps(prompts_data))
                    st.toast("Saved prompts config!", icon="📝")
                    st.rerun()

            with col_info:
                if has_prompt_changes:
                    st.caption("⚠️ You have unsaved changes in the prompts above.")
                else:
                    st.caption("✓ All changes saved.")
