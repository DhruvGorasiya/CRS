import pandas as pd
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("recommendation_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_subject_data(filename='subjects_df.csv'):
    '''
    Load and process subject data
    Params:
        Filename: Subject data for a given course
    '''
    try:
        df = pd.read_csv(filename)
        # Rename columns for consistency
        subjects_df = df[['Subject', 'Subject Names', 'Course Outcomes', 'Weekly Workload (hours)', 
                      'Assignments #', 'Hours per Assignment', 'Assignment Weight', 
                      'Avg Assignment Grade', 'Project Weight', 'Avg Project Grade', 
                      'Exam #', 'Avg Exam Grade', 'Exam Weight', 'Avg Final Grade', 
                      'Seats', 'Enrollments']].rename(columns={
            'Subject': 'subject_code',
            'Subject Names': 'name',
            'Course Outcomes': 'course_outcomes',
            'Weekly Workload (hours)': 'hours_per_week',
            'Assignments #': 'num_assignments',
            'Hours per Assignment': 'hours_per_assignment',
            'Assignment Weight': 'assignment_weight',
            'Avg Assignment Grade': 'avg_assignment_grade',
            'Project Weight': 'project_weight',
            'Avg Project Grade': 'avg_project_grade',
            'Exam #': 'exam_count',
            'Avg Exam Grade': 'avg_exam_grade',
            'Exam Weight': 'exam_weight',
            'Avg Final Grade': 'avg_final_grade',
            'Seats': 'Seats',
            'Enrollments': 'Enrollments'
        })
        
        # Convert numeric columns
        for col in ['hours_per_week', 'num_assignments', 'hours_per_assignment', 'assignment_weight', 
                    'avg_assignment_grade', 'project_weight', 'avg_project_grade', 'exam_count', 
                    'avg_exam_grade', 'exam_weight', 'avg_final_grade', 'Seats', 'Enrollments']:
            subjects_df[col] = pd.to_numeric(subjects_df[col], errors='coerce')
        
        # Extract outcomes
        outcomes = []
        for _, row in df.iterrows():
            course_outcomes = row['Course Outcomes']
            if pd.isna(course_outcomes) or not isinstance(course_outcomes, str):
                continue
            for outcome in course_outcomes.split(', '):
                outcomes.append({'subject_code': row['Subject'], 'outcome': outcome.strip()})
        outcomes_df = pd.DataFrame(outcomes)
        
        # Extract prerequisites
        prereqs = df[df['Prerequisite'] != 'None'][['Subject', 'Prerequisite']].rename(columns={
            'Subject': 'subject_code', 'Prerequisite': 'prereq_subject_code'
        }).dropna()
        
        # Extract corequisites
        coreqs = df[df['Corequisite'] != 'None'][['Subject', 'Corequisite']].rename(columns={
            'Subject': 'subject_code', 'Corequisite': 'coreq_subject_code'
        }).dropna()
        
        # Extract requirements
        requirements = []
        for _, row in df.iterrows():
            # Process programming requirements
            prog_reqs = row['Programming Knowledge Needed']
            if not pd.isna(prog_reqs) and isinstance(prog_reqs, str) and prog_reqs != 'None':
                for req in prog_reqs.split(', '):
                    requirements.append({
                        'subject_code': row['Subject'],
                        'requirement': req.strip(),
                        'type': 'programming'
                    })
            
            # Process math requirements
            math_reqs = row['Math Requirements']
            if not pd.isna(math_reqs) and isinstance(math_reqs, str) and math_reqs != 'None':
                for req in math_reqs.split(', '):
                    requirements.append({
                        'subject_code': row['Subject'],
                        'requirement': req.strip(),
                        'type': 'math'
                    })
        
        requirements_df = pd.DataFrame(requirements)
        
        return subjects_df, outcomes_df, prereqs, coreqs, requirements_df
        
    except Exception as e:
        logger.error(f"Error loading subject data: {e}")
        # Re-raise to allow caller to handle
        raise

def prerequisites_satisfied(course_code, student_data, prereqs_df):
    """Check if prerequisites for a course are satisfied"""
    prereqs = set(prereqs_df[prereqs_df['subject_code'] == course_code]['prereq_subject_code'])
    
    # Handle different formats of completed_courses in a robust way
    completed = set()
    if isinstance(student_data.get('completed_courses'), dict):
        completed = set(student_data['completed_courses'].keys())
    elif isinstance(student_data.get('completed_courses'), (set, list)):
        completed = set(student_data['completed_courses'])
    elif isinstance(student_data.get('completed_courses'), str):
        completed = {c.strip().upper() for c in student_data['completed_courses'].split(',') if c.strip()}
    
    # Check prerequisites
    return all(p in completed for p in prereqs)

def standardize_student_data(student_data, for_burnout=True):
    """Standardize student data format between modules"""
    result = {
        'NUid': student_data.get('NUid', ''),
        'desired_outcomes': student_data.get('desired_outcomes', ''),
        'core_subjects': student_data.get('core_subjects', '')
    }
    
    # For programming and math experience
    result['programming_experience'] = student_data.get('programming_experience', {})
    result['math_experience'] = student_data.get('math_experience', {})
    
    # Handle completed courses based on target module
    completed_courses = student_data.get('completed_courses', {})
    if for_burnout:
        # Burnout calculator expects a dictionary
        if isinstance(completed_courses, (list, set)):
            result['completed_courses'] = {course: {} for course in completed_courses}
        else:
            result['completed_courses'] = completed_courses
    else:
        # GA recommender expects a set
        if isinstance(completed_courses, dict):
            result['completed_courses'] = set(completed_courses.keys())
        elif isinstance(completed_courses, list):
            result['completed_courses'] = set(completed_courses)
        else:
            result['completed_courses'] = completed_courses
    
    # Copy any other fields that might be present
    for key in ['interests', 'semester']:
        if key in student_data:
            result[key] = student_data[key]
    
    return result

def load_burnout_scores(nuid):
    """Load burnout scores from CSV file"""
    try:
        scores_df = pd.read_csv(f'burnout_scores_{nuid}.csv')
        # Remove any duplicates if present
        scores_df = scores_df.drop_duplicates(subset=['subject_code'])
        return scores_df
    except FileNotFoundError:
        logger.warning(f"No burnout scores found for student {nuid}")
        return None
    except Exception as e:
        logger.error(f"Error loading burnout scores: {e}")
        return None