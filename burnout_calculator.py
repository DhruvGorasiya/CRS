import pandas as pd
import numpy as np
import json
from utils import (
    load_subject_data, prerequisites_satisfied, standardize_student_data
)

def get_subject(subjects_df, subject_code):
    '''
    Get subject data
    '''
    subject_rows = subjects_df[subjects_df['subject_code'] == subject_code]
    return subject_rows.iloc[0] if not subject_rows.empty else None

def workload_factor(subject_code, subjects_df, max_values):
    '''
    Calculate workload factor W' with the following equation:
     W' = ln(1 + H/Hmax) + A/Amax + P/Pmax + E/Emax
    '''
    subject_rows = get_subject(subjects_df, subject_code)
        
    subject = subject_rows.iloc[0]
    
    # Handle missing values with defaults
    H = subject['hours_per_week'] if pd.notna(subject['hours_per_week']) else 0
    num_assignments = subject['num_assignments'] if pd.notna(subject['num_assignments']) else 0
    hours_per_assignment = subject['hours_per_assignment'] if pd.notna(subject['hours_per_assignment']) else 0
    assignment_weight = subject['assignment_weight'] if pd.notna(subject['assignment_weight']) else 0
    avg_project_grade = subject['avg_project_grade'] if pd.notna(subject['avg_project_grade']) else 0
    project_weight = subject['project_weight'] if pd.notna(subject['project_weight']) else 0
    exam_count = subject['exam_count'] if pd.notna(subject['exam_count']) else 0
    avg_exam_grade = subject['avg_exam_grade'] if pd.notna(subject['avg_exam_grade']) else 0
    exam_weight = subject['exam_weight'] if pd.notna(subject['exam_weight']) else 0
    
    # Calculate components
    A = num_assignments * hours_per_assignment * assignment_weight
    P = (100 - avg_project_grade) * project_weight
    E = exam_count * (100 - avg_exam_grade) * exam_weight

    # Calculate workload factor
    W_prime = np.log(1 + H/max_values['Hmax']) + A/max_values['Amax'] + P/max_values['Pmax'] + E/max_values['Emax']
    
    return W_prime
        
def calculate_prerequisite_mismatch_factor(student_data, subject_code, requirements_df, prereqs_df):
    '''
    Calculate modified prerequisite mismatch factor M':
    M' = (1/T) * Σ(1 - proficiency(i))
    '''
    # Get subject requirements
    subject_reqs = requirements_df[requirements_df['subject_code'] == subject_code]
    
    T = len(subject_reqs)

    # If no prereqs / requirements, then no mismatch
    if T == 0:
        return 0 
    
    total_mismatch = 0

    for _, req in subject_reqs.iterrows():
        req_type = req['type']
        req_name = req['requirement']
        
        # Check if student has proficiency in programming requirement
        if req_type == 'programming' and req_name in student_data.get('programming_experience', {}):
            proficiency = min(max(student_data['programming_experience'][req_name] / 3.0, 0), 1)
            total_mismatch += (1 - proficiency)
        # Check if student has proficiency in math requirement
        elif req_type == 'math' and req_name in student_data.get('math_experience', {}):
            proficiency = min(max(student_data['math_experience'][req_name] / 3.0, 0), 1)
            total_mismatch += (1 - proficiency)
        else:
            # Is not proficient
            total_mismatch += 1

    M_prime = (1/T) * (total_mismatch)
    return M_prime

def calculate_stress_factor(student_data, subject_code, subjects_df):
    '''
    Calculate modified stress factor S':
    S' = ((100-GA)/100)² * Aw + ((100-GE)/100)² * Ew + ((100-GP)/100)² * Pw) / (Aw + Ew + Pw)
    '''
    subject_rows = get_subject(subjects_df, subject_code)

    subject = subject_rows.iloc[0]
    
    # Default values from subject data (with safety checks)
    default_GA = subject['avg_assignment_grade'] if pd.notna(subject['avg_assignment_grade']) else 70
    default_GE = subject['avg_exam_grade'] if pd.notna(subject['avg_exam_grade']) else 70
    default_GP = subject['avg_project_grade'] if pd.notna(subject['avg_project_grade']) else 70
    
    # Get weights with defaults
    Aw = subject['assignment_weight'] if pd.notna(subject['assignment_weight']) else 0
    Ew = subject['exam_weight'] if pd.notna(subject['exam_weight']) else 0
    Pw = subject['project_weight'] if pd.notna(subject['project_weight']) else 0
    
    # Use student's actual performance if available, with proper validation
    if subject_code in student_data.get('completed_courses', {}):
        completed_course = student_data['completed_courses'][subject_code]
        if isinstance(completed_course, dict):
            GA = completed_course.get('Avg Assignment Grade', default_GA)
            GE = completed_course.get('Avg Exam Grade', default_GE)
            GP = completed_course.get('Avg Project Grade', default_GP)
        else:
            # If completed course entry isn't a dict, use defaults
            GA, GE, GP = default_GA, default_GE, default_GP
    else:
        # Use average grades from subject data
        GA, GE, GP = default_GA, default_GE, default_GP

    # Handle division by zero
    total_weight = Aw + Ew + Pw
    if total_weight == 0:
        return 0
    
    # Calculate stress components with bounds checking (ensure values between 0-100)
    GA = max(0, min(100, GA))
    GE = max(0, min(100, GE))
    GP = max(0, min(100, GP))
    
    stress_assignments = ((100 - GA) / 100) ** 2 * Aw
    stress_exams = ((100 - GE) / 100) ** 2 * Ew
    stress_projects = ((100 - GP) / 100) ** 2 * Pw
    
    S_prime = (stress_assignments + stress_exams + stress_projects) / total_weight
    
    return S_prime

def precalculate_max_values(subjects_df):
    '''
    Calculate maximum values for workload normalization
    Params:
        Subjects_df: Subject data information
    Returns: Max values for 
    '''
    max_values = {
        'Hmax': max(subjects_df['hours_per_week'].max(), 1),
        'Amax': max((subjects_df['num_assignments'] * subjects_df['hours_per_assignment'] * subjects_df['assignment_weight']).max(), 1),
        'Pmax': max(((100 - subjects_df['avg_project_grade']) * subjects_df['project_weight']).max(), 1),
        'Emax': max((subjects_df['exam_count'] * (100 - subjects_df['avg_exam_grade']) * subjects_df['exam_weight']).max(), 1)
    }
    return max_values

def calculate_burnout(student_data, subject_code, subjects_df, requirements_df, prereqs_df, outcomes_df, max_values=None, weights=None):
    '''
    Calculate the normalized burnout probability
    P' = w1*W' + w2*M' + w3*S'
    Pfinal = 1 / (1 + e^-k(P'-P0))
    '''
    # Default weights if not provided
    if weights is None:
        weights = {
            'w1': 0.4,  # Weight for workload factor
            'w2': 0.3,  # Weight for prerequisite mismatch
            'w3': 0.3,  # Weight for stress factor
            'k': 4.0,   # Scaling factor for sigmoid
            'P0': 0.5   # Baseline burnout level
        }
    
    # Ensure student data is in correct format
    student_data = standardize_student_data(student_data, for_burnout=True)
    
    # Calculate or use provided max values
    if max_values is None:
        max_values = precalculate_max_values(subjects_df)
    
    # Calculate individual factors
    W_prime = workload_factor(subject_code, subjects_df, max_values)
    M_prime = calculate_prerequisite_mismatch_factor(student_data, subject_code, requirements_df, prereqs_df)
    S_prime = calculate_stress_factor(student_data, subject_code, subjects_df)
        
    # Calculate combined burnout score
    P_prime = weights['w1'] * W_prime + weights['w2'] * M_prime + weights['w3'] * S_prime
    
    # Normalize to [0,1] using sigmoid function
    P_final = 1 / (1 + np.exp(-weights['k'] * (P_prime - weights['P0'])))
    
    return P_final

def calculate_scores(nuid):
    '''
    Calculate burnout scores for all subjects for a given student
    '''
    # Load all necessary data
    subjects_df, outcomes_df, prereqs_df, _, requirements_df = load_subject_data()
    
    # Precalculate max values once for efficiency
    max_values = precalculate_max_values(subjects_df)
    
    # Load student data
    student_df = pd.read_csv(f'student_{nuid}.csv')
    
    # Parse student data with proper error handling
    student_data = {
        'NUid': student_df['NUid'].iloc[0],
        'programming_experience': {},
        'math_experience': {},
        'completed_courses': {},
        'core_subjects': '',
        'desired_outcomes': ''
    }
    
    if 'programming_experience' in student_df.columns:
        prog_exp = student_df['programming_experience'].iloc[0]
        if pd.notna(prog_exp):
            student_data['programming_experience'] = json.loads(prog_exp)
    if 'math_experience' in student_df.columns:
        math_exp = student_df['math_experience'].iloc[0]
        if pd.notna(math_exp):
            student_data['math_experience'] = json.loads(math_exp)

    if 'completed_courses_details' in student_df.columns:
        completed = student_df['completed_courses_details'].iloc[0]
        if pd.notna(completed):
            student_data['completed_courses'] = json.loads(completed)
    if 'completed_courses' in student_df.columns:
        completed = student_df['completed_courses'].iloc[0]
        if pd.notna(completed):
            courses = [c.strip().upper() for c in str(completed).split(',') if c.strip()]
            student_data['completed_courses'] = {code: {} for code in courses}

    if 'core_subjects' in student_df.columns:
        student_data['core_subjects'] = student_df['core_subjects'].iloc[0]
        
    if 'desired_outcomes' in student_df.columns:
        student_data['desired_outcomes'] = student_df['desired_outcomes'].iloc[0]
    
    # Calculate scores for each subject
    scores = []
    for subject_code in subjects_df['subject_code']:
        # Skip subjects the student has already completed
        if subject_code in student_data['completed_courses']:
            continue
            
        # Calculate burnout probability
        burnout = calculate_burnout(
            student_data, subject_code, subjects_df, 
            requirements_df, prereqs_df, outcomes_df, max_values
        )
        
        # Get prerequisite info for this subject
        prereqs = list(prereqs_df[prereqs_df['subject_code'] == subject_code]['prereq_subject_code'])
        
        # Check if prerequisites are satisfied
        prereqs_satisfied_val = prerequisites_satisfied(subject_code, student_data, prereqs_df)
        
        # For burnout scores, we don't yet calculate utility (that's done in ga_recommender)
        # But we include a placeholder to maintain file structure compatibility
        scores.append({
            'subject_code': subject_code,
            'subject_name': get_subject(subjects_df, subject_code).iloc[0]['name'] if not get_subject(subjects_df, subject_code).empty else "Unknown course",
            'burnout_score': round(burnout, 3),
            'prerequisites': prereqs,
            'prerequisites_satisfied': prereqs_satisfied_val,
            'utility': 0  # Placeholder - will be calculated in ga_recommender
        })

    # Create DataFrame and sort by burnout (ascending - lower burnout is better)
    scores_df = pd.DataFrame(scores)
    scores_df = scores_df.sort_values(by='burnout_score', ascending=True)
    
    # Save to CSV
    scores_df.to_csv(f'burnout_scores_{nuid}.csv', index=False)
    
    return scores_df
    
if __name__ == "__main__":
    nuid = input("Enter NUid to calculate burnout scores: ")
    result = calculate_scores(nuid)
    
    if result is not None:
        print(f"Calculated burnout scores for {len(result)} subjects.")
        print("Top 5 subjects with lowest burnout risk:")
        for i, (_, row) in enumerate(result.head(5).iterrows()):
            print(f"{i+1}. {row['subject_code']}: {row['subject_name']} (Burnout: {row['burnout_score']})")
    else:
        print("Failed to calculate burnout scores. Check logs for details.")