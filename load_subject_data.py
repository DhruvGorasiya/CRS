import pandas as pd

def load_subject_data():
    # Load your dataset
    df = pd.read_csv('subject_analysis.csv')
    
    # Process into required structures
    subjects_df = df[['Subject', 'Subject Names', 'Weekly Workload (hours)', 'Assignments #', 'Hours per Assignment', 
                      'Assignment Weight', 'Avg Assignment Grade', 'Project Weight', 'Avg Project Grade', 'Exam #', 
                      'Avg Exam Grade', 'Exam Weight', 'Avg Final Grade', 'Seats', 'Enrollments']].rename(columns={
        'Subject': 'subject_code', 'Subject Names': 'name', 'Weekly Workload (hours)': 'hours_per_week', 
        'Assignments #': 'num_assignments', 'Hours per Assignment': 'hours_per_assignment', 
        'Assignment Weight': 'assignment_weight', 'Avg Assignment Grade': 'avg_assignment_grade', 
        'Project Weight': 'project_weight', 'Avg Project Grade': 'avg_project_grade', 'Exam #': 'exam_count', 
        'Avg Exam Grade': 'avg_exam_grade', 'Exam Weight': 'exam_weight', 'Avg Final Grade': 'avg_final_grade', 
        'Seats': 'Seats', 'Enrollments': 'Enrollments'
    })
    
    outcomes = []
    for _, row in df.iterrows():
        # Handle NaN or non-string values in 'Course Outcomes'
        course_outcomes = row['Course Outcomes']
        if pd.isna(course_outcomes) or not isinstance(course_outcomes, str):
            continue  # Skip rows with missing or invalid outcomes
        for outcome in course_outcomes.split(', '):
            outcomes.append({'subject_code': row['Subject'], 'outcome': outcome.strip()})
    outcomes_df = pd.DataFrame(outcomes)
    
    prereqs = df[df['Prerequisite'] != 'None'][['Subject', 'Prerequisite']].rename(columns={
        'Subject': 'subject_code', 'Prerequisite': 'prereq_subject_code'
    }).dropna()
    
    coreqs = df[df['Corequisite'] != 'None'][['Subject', 'Corequisite']].rename(columns={
        'Subject': 'subject_code', 'Corequisite': 'coreq_subject_code'
    }).dropna()
    
    return subjects_df, outcomes_df, prereqs, coreqs

if __name__ == "__main__":
    subjects_df, outcomes_df, prereqs, coreqs = load_subject_data()
    print("Subject data loaded into Pandas DataFrames.")
    # Save for debugging (optional)
    subjects_df.to_csv('subjects_df.csv', index=False)
    outcomes_df.to_csv('outcomes_df.csv', index=False)
    prereqs.to_csv('prereqs_df.csv', index=False)
    coreqs.to_csv('coreqs_df.csv', index=False)