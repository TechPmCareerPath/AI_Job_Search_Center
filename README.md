# AI_Job_Search_Center

You have probably seen job search tools that can help you search for jobs, update your resume, and apply for jobs. What about an end-to-end job search **PLAN** to keep you motivated and **ADVICE** along the way? 

I created AI Job Search Center since it mirrors the job search plan I've been giving my coaching clients. 

<img width="1825" height="780" alt="AI_Job_Search_Center_homepage" src="https://github.com/user-attachments/assets/e9419d51-7d4b-411f-9873-b9e476a665c9" />

**With AI Job Search Center:**

a) You can organize and execute a job search PLAN using pre-defined tasks and goals YOU choose. This keeps the job hunt fresh and variable and yet intentional. 

b) Allows you to set WHEN your job search week begins and ends. You want to do a job search Tuesday through Sunday? No problem! A Job Search Dashboard shows your progress and what needs to be completed by a due date you choose.

c) Select a resume from among several of your resumes to not only compare it to job descriptions but also consider the industry domain fit, mandatory hard skills, technical tools, experience leveling and more. These factors are used to generate a **Job Match Score**. You can easily adjust the minimum Job Match Score in the UI so that you don't see positions that don't fully align with your skills and experience. 

d) Use the **Resume Tailor** to customize and draft one of your resumes to more closely align with the chosen position. The tailored resume will also show knowledge and experience gaps to address before you submit it.

e) The **Job Application Tracker** tracks jobs applied across time. Jobs tracked can be those found using the AI Job Search Center or jobs found and applied outside of the app, like a former co-worker mentioned a job opening to you. 

f) Use the **Weekly Plan Advisor** for job hunting advice. It analyzes your notes in the Job Application Tracker and additional results to bridge the gap between your historical job search patterns and upcoming goals allowing AI to spot misalignments such as aiming for 20 job applications this week when 5 overdue follow-ups from last week are pending.

g) Use the **System Configuration Editor** to easily update each of the AI prompts used by this app in an editable UI to better meet your needs. Also, adjust the AI model to use and the temperature\creativity AI uses in its matches and responses. 

h) AI Job Search Center is meant to be quick, inexpensive, and run locally on your machine. You keep your data (except for data included in API calls). 

i) Why make this app available on Github? Having access to the source code means you can learn more about the technology behind the scenes, improve current features or add more features as you like to improve your job search. You can mention these learnings as 'hands-on' AI Python experience in a future job interview like "I ran my own AI job hunting plan. I used Python to implement feature X because..."

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg) 

[LinkedIn](https://www.linkedin.com/in/craig-guarraci/)


# Getting Started
..

## Prerequisites
...

## Installation
Create a Python virtual environment/create new project subdir? 

> TBD...

Clone the repo

> git clone https://github.com/github_username/repo_name.git

Get required Python packages

> ...my requirements.txt

Get Free JobsPipe API key [here](https://jobspipe.dev/pricing)


**ALWAYS secure your API keys** The AI Job Search Center will only use your keys for duration of the session. Once you close the browser tab and kill streamlit in the console, the keys are no longer used. You'll need to add the keys in the Global Setup box on the left side of the app UI each time you want to use it.

# Usage
Open a command prompt, go to the project directory and run: 

> streamlit run app.py

A new browser window will open with a URL pointing to your localhost like: http://localhost:8501/ 

### Job Search Plan

Go to the Job Search Plan tab, choose the start and end dates for your weekly job search. Also, choose the job hunting tasks for that week, along with the a goal for each (ex: Job Applications, 6 job applications, etc.)

Note the help "?" bubble next to each job hunting task that will give more info on that job hunting task.

When done, choose the "Launch weekly plan" button.

Log your progress on the "Active Job Search Dashboard". Under the tab "Job Search & Resume Tailor", any positions that you apply for (ex: "Did you apply for this position?", if you choose "YES") will **automatically increment** the number of Applications in the "Active Job Search Dashboard".

### Job Search Plan --> Weekly Plan Advisor

After using the AI Job Center for a few weeks and adding notes to the Job Application Tracker Notes column, the app has more context to give you suggestions on your overall job hunting approach. In the Job Search Plan tab, simply choose "Analyze Application Tracker & Get Advice" and it will pass your job application tracker and current weekly plan to AI to analyze. The results will come after the header "Strategic Job Search Insights as of YYYY-MM-DD..."

The Weekly Plan Advisor results will remain until you choose to run it again, which is why the last run date is provided.

### Job Search & Resume Tailor

1. Select Active Resume

The resume can be in .PDF, .DOCX or .TXT formats. You may have several resumes for slightly different positions you are pursuing. Each one can be uploaded and selected in the drop-down later. This step just puts the resume in the to root folder for this project with the filename unchanged.

**Note:** The resume you choose here will be sent to Gemini. It's suggested to remove any personally identifiable information (PII) before submitting it (name, email, Linked In URL, phone number, etc.).

To try this feature, use the sample resume in .\resume\Sample_resume_my_Program_Mgt_example_v3.txt

You can see an example of the Resume Tailor results previously run against the sample resume by viewing the file at: .\resume\Sample_Tailored_Resume_Output.txt. Note the critique sections at the top, bottom and the "[UPDATED]" text to show which sections AI updated.

2. Select Job Source Query. 

You may be pursuing several different job titles, thus a different job query will be needed to retrieve the latest jobs for each job title. Also, there may be other  preferences  between positions (ex: location, seniority, etc.). 

Select the JobsPipe YAML file in .\config\query.yaml.

A single YAML file can contain multiple job queries. In the drop-down labeled "Choose Job to Query" select a query from that YAML file that matches the resume you just uploaded (ex: I uploaded a program manager resume, so choose the "program manager" query).

You can choose the expand box "View Selected Job Query" to view that query. 

Lastly, choose the shiny red button "Find Job Matches with AI". This will... 

### Job Application Tracker
TODO

### System Configuration Editor
TODO

# Acknowledgments
* [Google Gemini](https://ai.google.dev/gemini-api/docs/pricing) (I'm not affiliated with Google, just a happy customer.)
* [JobsPipe](https://jobspipe.dev/pricing) (I'm not affiliated with JobsPipe, just a happy customer.)


