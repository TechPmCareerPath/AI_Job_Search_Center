# AI_Job_Search_Center

You have probably seen job search tools that can help you search for jobs, update your resume, and apply for jobs. Rather than a tool to automate the boring 
"Find job posting -> Apply for job -> Repeat" loop, what about a job search **PLAN** with dynamic, weekly goals **YOU CHOOSE** and **DETAILED ADVICE** to keep you motivated along the way?

**I created AI Job Search Center since it mirrors the job search plan I've been giving my coaching clients.** It also includes elements of **gamification** to offer job seekers ongoing encouragement and support their momentum.

<img width="1825" height="780" alt="AI_Job_Search_Center_homepage" src="https://github.com/user-attachments/assets/e9419d51-7d4b-411f-9873-b9e476a665c9" />

**AI Job Search Center:**

a) You can organize and execute a job search plan using pre-defined **tasks and goals YOU choose.** This keeps the job hunt fresh and variable and yet intentional. 

b) Allows you to set WHEN your job search week begins and ends. You want to do a job search Tuesday through Sunday? No problem! A Job Search Dashboard **shows your progress** and what needs to be completed by a due date you chose.

c) You can select a resume from among **several of your resumes**. Once a resume is chosen, the resume is not only compared to job descriptions but also considers the industry domain fit, mandatory hard skills, technical tools, experience leveling and more. These factors are used to generate an estimated **Job Match Score**. You can easily adjust the minimum Job Match Score in the UI so that you don't see positions that don't fully align with your skills and experience. With the default API integration, you can **search for jobs across 30+ ATS sources!**

d) Choose a job in the results, then use the **Resume Tailor** to automatically customize and draft your chosen resume to more closely align with that job. The tailored resume will also show knowledge and experience gaps to address before you submit it for an open position.

e) The **Job Application Tracker** shows your overall job hunting status at a glance. It tracks jobs applied over weeks/months in the past. Jobs tracked can be those found using the AI Job Search Center or jobs found and applied **outside of this app**, like a former co-worker mentioned a job opening to you. 

f) Get job hunting advice from the **Weekly Plan Advisor**. The Advisor analyzes YOUR notes in the Job Application Tracker and additional results to bridge the gap between your historical job search patterns and upcoming goals to spot misalignments and suggest improvements. One example of misalignment: you chose to submit 20 job applications this week when you have 7 overdue, warm follow-ups from last week that are pending.

g) Use the **System Configuration Editor** to easily update each of the AI prompts used by this app to more closely meet your needs. Also, adjust the  temperature\creativity AI uses in its job matches and detailed responses.

h) AI Job Search Center is meant to be **quick, inexpensive, and run locally** on your machine. You keep your data (except for data passed in API calls). **Gamification* has been implemented through granular progress indicators, supportive messaging, and celebration for each completed weekly job search plan!

**Why did I make this app available on Github?** 

Having access to the source code means you can learn more about the technology behind the scenes, improve current features or add more features to improve your job search. Also, you can mention these learnings as 'hands-on' AI Python experience in a future job interview like "I ran my own AI job hunting plan. I used Python to implement feature X because..."

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg) 

[LinkedIn](https://www.linkedin.com/in/craig-guarraci/)


# Getting Started

## Prerequisites
Python 3.13+

## Installation

1. Clone the repository Open your terminal and run

```bash
git clone https://github.com/TechPmCareerPath/AI_Job_Search_Center.git

cd AI_Job_Search_Center
```

2. Recommended to set up a virtual environment

```bash
python -m venv myenv
```

On Windows:

```bash
.\myenv\Scripts\activate
```
 
On macOS/Linux:

```bash
source myenv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Get API keys

* Get a free JobsPipe API key [here.](https://jobspipe.dev/pricing) (I'm not affiliated with JobsPipe, just a happy customer.)

* Get a free Gemini API key in [Google AI Studio.](https://aistudio.google.com) See [Google Gemini pricing.](https://ai.google.dev/gemini-api/docs/pricing) (I'm not affiliated with Google, just a happy customer.)

* **ALWAYS secure your API keys.** The AI Job Search Center will only use your keys for duration of the session. Once you close the browser tab and kill Streamlit in the console, the keys are no longer remembered. You'll need to add the keys in the Global Setup box on the left side of the app UI each time you want to use it.

## Usage
From a command prompt showing the virtual environment created above and within the project directory containing app.py, run: 

```bash
streamlit run app.py
```

In a few seconds, a new browser window will open with a URL pointing to your localhost like: http://localhost:8501/ 

## Feature walkthrough

### Global Setup
Add your JobsPipe API and Gemini API keys on the left.

<img width="266" height="330" alt="AI_Job_Search_Center_GlobalSetup" src="https://github.com/user-attachments/assets/a867fa1d-383c-4eda-852e-b82982ccddb6" />


### Job Search Plan

Go to the Job Search Plan tab, choose the start and end dates for your weekly job search. Also, choose the job hunting tasks you want to do that week along with a goal for each (ex: Job Applications, 6 job applications, etc.)

Note the help "?" bubble next to each job hunting task will give more info.

When done, choose the "Launch weekly plan" button.

Log your progress on the Active Job Search Dashboard. Under the tab "Job Search & Resume Tailor", any positions that you apply for (ex: "Did you apply for this position?", if you choose "YES") will **automatically increment** the number of Applications in the Active Job Search Dashboard (if you previously created an active job search and the "Applications" task was added for that week). 

<img width="842" height="717" alt="AI_Job_Search_Center_Create_Job_Search_Plan" src="https://github.com/user-attachments/assets/ca97888c-a327-49d1-a68d-8944b6137366" />


### Job Search Plan --> Weekly Plan Advisor

After using the AI Job Search Center for a few weeks and adding notes to the Job Application Tracker Notes column, the app has more context to give you suggestions on your overall job hunting approach. In the Job Search Plan tab - Weekly Plan Advisor, simply choose "Analyze Application Tracker & Get Advice" and it will pass your job application tracker and current weekly plan to AI to analyze. The results will come after the header "Strategic Job Search Insights as of YYYY-MM-DD..."

The Weekly Plan Advisor results are saved and available across sessions until you choose to run it again, which is why the last run date is provided.

### Job Search & Resume Tailor

1. Select Active Resume

The resume can be in .PDF, .DOCX or .TXT formats. You may have several resumes for slightly different positions you are pursuing. Each one can be uploaded and selected in the "Choose Active Resume File" drop-down later. This step puts the resume in the root folder for this project with the same filename.

**Note:** The resume you choose here will be sent to Gemini. It's suggested to **remove any personally identifiable information (PII)** before uploading it (ex: name, email, Linked In URL, phone number, etc.).

To try this feature, use the sample resume in .\resume\Sample_resume_my_Program_Mgt_example_v3.txt

An example of the Resume Tailor results using the sample resume above can be found at: .\output\Sample_Tailored_Resume_Output.txt. Note the critique sections at the top, bottom and the "[UPDATED]" text to show which sections AI updated.

2. Select Job Source Query. 

You may be pursuing **several different job titles**, thus a different job query will be needed to retrieve the latest jobs for each job title. Also, you may have different job preferences (ex: location, seniority, etc.). 

Select the JobsPipe YAML file in .\config\query.yaml.

A single query.yaml file can contain multiple JobsPipe job queries. In the drop-down labeled "Choose Job to Query", select a query from that YAML file that matches the resume you just uploaded (ex: I uploaded a program manager resume, so choose the "program manager" query).

You can choose the expand box "View Selected Job Query" to view the selected JobsPipe query. 

Lastly, choose the shiny red button "Find Job Matches with AI". This will call JobsPipe to get the jobs in the selected query. Next the app will send the job results along with the chosen resume to Gemini to compare. Gemini will return the Match Score %, Reasoning, Key Matching Skills and Missing Skills, which are all displayed in the UI. 

### Job Search & Resume Tailor --> Expand one job --> Key Matching Skills

**Note:** AI will infer that you have Key Matching Skills even though they are not explicitly listed on your resume.

Some examples: If you list "SQL" on your resume, AI will infer that you have "ETL" as a Key Matching Skill for you to consider adding to your resume to more closely match the job description. If you mention "ML projects" or completed an "AI Fundamentals" course, AI will infer that you have experience with basic ML models like time series or anomaly detection as a Key Matching Skill for you to consider adding to your resume to more closely match the job description. 

### Job Search & Resume Tailor --> Expand one job --> Generate Tailored Resume

Within each matching job, there's a button that says "Generate Tailored Resume". It does what it says :-) The chosen job and resume are sent to Gemini. After the Tailored Resume has been created, it will display in text below this button. You can also download that tailored resume and use it to update your official resume.

**"Did you apply for this position?"** --> **"Yes"**, will add this position to the Job Application Tracker table and increment Active Job Search Dashboard -> Applications task by one, (if there is an active job search and the "Applications" task was added for that week.). You can **undo** this action by choosing "No".

**"Did you apply for this position?"** --> **"No"**, just marks the status as "Skipped" with no further action needed by the user. You can **undo** this action by choosing "Yes".

<img width="1052" height="552" alt="AI_Job_Search_Center_FindJobMatches" src="https://github.com/user-attachments/assets/70e8b3dc-b8a1-4de0-a34c-9c2b8ef62087" />


### Job Application Tracker
This shows your overall job hunting status at a glance. It's a table to view and edit the jobs you applied for, add your notes and change the application status.

**All of your job applications** can be tracked here. This table includes jobs you found via this app and chose "Did you apply for this position?" --> "Yes". Also, this table supports manually adding jobs you found and applied for **outside** of this app, like a former co-worker mentioned a job that you applied for. 

Based on the Follow-up Date you enter in this table, there will be 2 states as the top. The states are: 
* Follow-ups that are past due or due today.
* Follow-ups to be completed tomorrow.

The **Filter Status** shows the statuses **you create**. I didn't want to force a job hunting process on my users, so I let you decide what follow-up statuses to create. It's suggested to create a few, distinct statuses as possible, and make them meaningful :-) 

Note, you can hover on the table to get a little menu in the top right. Also, choosing a row in the far left column will enable deletion.

<img width="907" height="592" alt="AI_Job_Search_Center_JobApplicationTrackerTable" src="https://github.com/user-attachments/assets/c6eb6ea2-bfc6-4289-96a0-0e70c974da7f" />

After making changes to the table, choose the "Save Tracker Changes" button under this table.


### System Configuration Editor
This allows you to modify AI model settings and system prompts live without touching the code. For convenience, all changes are saved in the .yaml files mentioned on this screen.

Note the "?" bubble explains what each option is for and how to set the range.

<img width="847" height="267" alt="AI_Job_Search_Center_SystemConfigHelpHover" src="https://github.com/user-attachments/assets/86d139c9-2369-4a09-9f9a-508fc879823a" />


# Project Structure

```
AI_job_search_center\
├── app.py                               # Main Streamlit application entry point.
├── .\config\config.yaml                 # Model configs (model names, temperature, etc.), editable via the UI.
├── .\config\prompts.yaml                # AI prompt templates, editable via the UI.
├── .\config\query.yaml                  # Jobs query configurations, currently configured for JobsPipe. You must manually edit this file.
├── .\output\agent_job_analysis.json     # Raw output from choosing "Find Job Matches with AI". The app then compares returned jobs to the selected resume.
├── .\output\agent_weekly_advisor.json   # Raw output from the Weekly Plan Advisor. 
├── .\output\jobs.csv                    # All results from your JobsPipe query above and below Match Threshold%. Has a subset of most useful fields from jobs.json.
├── .\output\jobs.json                   # All results from your JobsPipe query above and below Match Threshold%.
├── .\output\skipped_jobs.json           # Based on job matching results, if the user chooses NOT to pursue a job, that job ID is recorded here.
├── .\output\tracker_db.json             # Stores the Job Application Tracker table.
├── .\output\weekly_plan.json            # Stores the Job Search Plan -> Active Job Search Dashboard.
├── .\output\Sample_Tailored_Resume_Output.txt            # An example of the Resume Tailor results previously run against the sample PgM resume.
├── .\resume\Sample_resume_Program_Mgt_example_v3.txt  # Sample PgM resume to try.
└── .\uploads                            # Any resumes or query.yaml uploads you chose go here.

```

# Features you might consider adding

* Automatic cover letter generation. This will entail at least: a new prompt added to the System Configuration Editor, save that prompt to prompts.yaml, a "Generate cover-letter" button probably near the "Generate Tailored Resume" button and maybe other changes.
* The JobsPipe jobs.json query response has a wealth of info that could be easily added to the results, such as whether the job is remote or hybrid, salary range, clickable company domain to see if that job still exists on the corporate website, list of job benefits, etc.
* Interview prep questions specific to the job and company. This will entail at least: a new prompt added to the System Configuration Editor, save that prompt to prompts.yaml, a "Generate interview questions" button probably near the "Generate Tailored Resume" button and maybe other changes.

# Thanks!

I hope the AI Job Search Center is a worthy addition to your job hunting! Please send me feedback. 

