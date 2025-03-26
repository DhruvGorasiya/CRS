import pandas as pd
import json
from burnout_calculator import calculate_burnout
from utils import load_subject_data, prerequisites_satisfied, standardize_student_data, load_burnout_scores

def jaccard_similarity(set1, set2):
    '''
    Calculate Jaccard similarity between two sets 
    '''
    # Handle empty sets
    if not set1 or not set2:
        return 0
        
    # Calculate intersection and union
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    # Prevent division by zero
    if union == 0:
        return 0
        
    return intersection / union

def calculate_outcome_alignment_score(student_data, subject_code, outcomes_df):
    '''
    Calculate outcome alignment score (OAS) using Jaccard similarity
    OAS = similarity(User Desired Outcomes, Course Outcomes)
    '''
    # If no desired outcomes, return 0
    if not student_data.get('desired_outcomes') or not isinstance(student_data['desired_outcomes'], str):
        return 0
    
    # Get student's desired outcomes as a set
    student_outcomes = set([outcome.strip() for outcome in student_data['desired_outcomes'].split(',')])
    
    # Get subject outcomes as a set
    subject_outcomes = set(outcomes_df[outcomes_df['subject_code'] == subject_code]['outcome'])
    
    # Calculate Jaccard similarity
    return jaccard_similarity(student_outcomes, subject_outcomes)

def calculate_utility(student_data, subject_code, subjects_df, requirements_df, prereqs_df, outcomes_df, utility_weights=None):
    '''
    Calculate the overall utility function with prerequisite penalty
    U = α·OAS + β·(1-Pfinal) - δ·PrereqPenalty
    '''
    # Default utility weights
    if utility_weights is None:
        utility_weights = {
            'alpha': 0.5,  # Weight for outcome alignment
            'beta': 0.5,   # Weight for burnout avoidance
            'delta': 0.5   # Weight for prerequisite penalty
        }
    
    burnout_student_data = standardize_student_data(student_data, for_burnout=True)

    # Calculate burnout probability
    burnout_prob = calculate_burnout(burnout_student_data, subject_code, subjects_df, requirements_df, prereqs_df, outcomes_df)
    
    # Calculate outcome alignment score
    oas = calculate_outcome_alignment_score(student_data, subject_code, outcomes_df)
    
    # Check prerequisites
    prereq_courses = list(prereqs_df[prereqs_df['subject_code'] == subject_code]['prereq_subject_code'])
    prereq_penalty = 0
    
    if prereq_courses:
        prereqs_satisfied = all(prereq in student_data.get('completed_courses', {}) for prereq in prereq_courses)
        if not prereqs_satisfied:
            prereq_penalty = 1  # Apply full penalty if prerequisites are not satisfied
    
    # Calculate overall utility
    utility = (
        utility_weights['alpha'] * oas + 
        utility_weights['beta'] * (1 - burnout_prob) - 
        utility_weights['delta'] * prereq_penalty
    )
    
    return utility

def calculate_enrollment_likelihood(semester, is_core, seats, enrollments):
    # Base likelihood from seats availability
    seats_ratio = (seats - enrollments) / seats if seats > 0 else 0
    if seats_ratio <= 0:
        base_likelihood = 0.1  # Very low chance but not impossible due to potential drops
    else:
        base_likelihood = seats_ratio

    # Semester priority multiplier (higher semester = higher priority)
    semester_multiplier = min(semester / 4, 1.0)  # Caps at 1.0 after 4th semester
    
    # Core requirement multiplier
    core_multiplier = 1.5 if is_core else 1.0
    
    final_likelihood = base_likelihood * semester_multiplier * core_multiplier
    return min(final_likelihood, 1.0)  # Cap at 100%
    
def find_matching_courses(student_data, subjects_df, outcomes_df, prereqs_df, coreqs_df, burnout_scores_df=None):
    """Find courses that match student interests and skills"""
    matching_courses = []
    student_interests = [interest.lower().strip() for interest in student_data['interests'].split(',')]
    
    # Add default interests if none provided
    if not student_interests or (len(student_interests) == 1 and not student_interests[0]):
        student_interests = ['computer science', 'data science', 'programming']
    
    for _, course in subjects_df.iterrows():
        score = 0
        reasons = []
        
        # Skip courses that have already been completed
        if course['subject_code'] in student_data['completed_courses']:
            continue
            
        # 1. Check course name and outcomes for interest matches
        course_name = str(course['name']).lower()
        course_outcomes = str(course['course_outcomes']).lower() if pd.notna(course['course_outcomes']) else ""
        
        for interest in student_interests:
            # Check if interest appears in course name
            if interest in course_name:
                score += 0.4
                reasons.append(f"Course title matches your interest in {interest}")
            
            # Check if interest appears in course outcomes
            if interest in course_outcomes:
                score += 0.3
                reasons.append(f"Course covers topics in {interest}")
        
        # 2. Check for specific keywords based on interests
        interest_keywords = {
            'ai': ['artificial intelligence', 'machine learning', 'deep learning', 'neural', 'nlp'],
            'web': ['web', 'javascript', 'frontend', 'backend', 'full-stack', 'react', 'node'],
            'data': ['data', 'analytics', 'database', 'sql', 'big data', 'visualization'],
            'security': ['security', 'cryptography', 'cyber', 'network security'],
            'mobile': ['mobile', 'ios', 'android', 'app development'],
            'systems': ['operating system', 'distributed', 'parallel', 'architecture'],
            'programming': ['python', 'java', 'c++', 'algorithms', 'software engineering'],
            'computer science': ['algorithms', 'data structures', 'programming', 'software']
        }
        
        for interest in student_interests:
            if interest in interest_keywords:
                for keyword in interest_keywords[interest]:
                    if keyword in course_outcomes:
                        score += 0.2
                        reasons.append(f"Course includes {keyword} technologies")
        
        # 3. Calculate enrollment likelihood
        try:
            likelihood = calculate_enrollment_likelihood(
                student_data['semester'],
                course['subject_code'] in student_data['core_subjects'].split(','),
                course['Seats'] if pd.notna(course['Seats']) else 0,
                course['Enrollments'] if pd.notna(course['Enrollments']) else 0
            )
        except:
            likelihood = 0.5  # Default likelihood if calculation fails
        
        # 4. Check prerequisites
        if not prerequisites_satisfied(course['subject_code'], student_data, prereqs_df):
            score *= 0.5  # Reduce score if prerequisites not met
            reasons.append("⚠️ Prerequisites not completed")
        
        # 5. Add burnout utility score if available
        burnout_score = None
        utility_score = None
        if burnout_scores_df is not None:
            burnout_row = burnout_scores_df[burnout_scores_df['subject_code'] == course['subject_code']]
            if not burnout_row.empty:
                burnout_score = float(burnout_row['burnout_score'].iloc[0])
                utility_score = float(burnout_row['utility'].iloc[0])
                
                # Integrate utility score into the overall score
                if utility_score > 0:
                    score_boost = utility_score * 0.5  # Scale factor to balance with other scores
                    score += score_boost
                    if utility_score > 0.15:
                        reasons.append(f"✅ Low burnout risk (utility: {utility_score:.2f})")
                    else:
                        reasons.append(f"Low-moderate burnout risk (utility: {utility_score:.2f})")
                elif utility_score < 0:
                    # Negative utility reduces score
                    score *= (1 + utility_score)  # Multiplicative penalty
                    reasons.append(f"⚠️ High burnout risk (utility: {utility_score:.2f})")
        
        # If course has a reasonable match score or is a core subject
        is_core = course['subject_code'] in student_data['core_subjects'].split(',')
        if score > 0.3 or is_core:  # Include core subjects regardless of match score
            if is_core:
                score += 0.5  # Boost score for core subjects
                reasons.append("📚 This is a core subject requirement")
            
            matching_courses.append({
                'subject_code': course['subject_code'],
                'name': course['name'],
                'match_score': score,
                'likelihood': likelihood,
                'seats': course['Seats'] if pd.notna(course['Seats']) else 0,
                'enrollments': course['Enrollments'] if pd.notna(course['Enrollments']) else 0,
                'burnout_score': burnout_score,
                'utility_score': utility_score,
                'reasons': reasons,
                'is_core': is_core
            })
    
    # Sort by combination of match score, utility score, and enrollment likelihood
    matching_courses.sort(key=lambda x: (
        x['is_core'],  # Core subjects first
        x['match_score'] * 0.5 +  # 50% weight to interest match
        (x['utility_score'] if x['utility_score'] is not None else 0) * 0.3 +  # 30% weight to burnout utility
        x['likelihood'] * 0.2  # 20% weight to enrollment likelihood
    ), reverse=True)
    
    return matching_courses

def get_student_data(nuid, semester):
    try:
        student_df = pd.read_csv(f'student_{nuid}.csv')
        
        # Create basic structure with raw data
        raw_student_data = {
            'NUid': student_df['NUid'].iloc[0],
            'semester': semester,
            'completed_courses': set(str(course).upper() for course in 
                str(student_df['completed_courses'].iloc[0]).split(',') 
                if pd.notna(student_df['completed_courses'].iloc[0]) and str(student_df['completed_courses'].iloc[0]).strip()),
            'core_subjects': str(student_df['core_subjects'].iloc[0]).upper(),
            'interests': (
                str(student_df['desired_outcomes'].iloc[0]) if pd.notna(student_df['desired_outcomes'].iloc[0]) 
                else 'computer science'
            ),
            'desired_outcomes': (
                str(student_df['desired_outcomes'].iloc[0]) if pd.notna(student_df['desired_outcomes'].iloc[0]) 
                else 'computer science'
            )
        }
        
        return standardize_student_data(raw_student_data, for_burnout=False)
    except FileNotFoundError:
        return None

def generate_recommendations(nuid, semester, additional_interests=None):
    subjects_df, outcomes_df, prereqs_df, coreqs_df, _ = load_subject_data()
    burnout_scores_df = load_burnout_scores(nuid)
    
    student_data = get_student_data(nuid, semester)
    if student_data is None:
        return None, None
    
    # Add additional interests if provided
    if additional_interests:
        student_data['interests'] += ',' + ','.join(additional_interests)
    
    # Find matching courses
    matching_courses = find_matching_courses(
        student_data, subjects_df, outcomes_df, prereqs_df, coreqs_df, burnout_scores_df
    )
    
    # Separate into recommended and highly competitive
    recommended_courses = []
    highly_competitive_courses = []
    
    for course in matching_courses:
        if course['likelihood'] < 0.3:  # Very competitive
            highly_competitive_courses.append(course)
        else:
            recommended_courses.append(course)
    
    return recommended_courses, highly_competitive_courses

def save_schedule(nuid, recommended_courses, subjects_df, burnout_scores_df):
    # Format recommendations into final schedule format
    top_recommendations = []
    for course in recommended_courses:
        course_code = course if isinstance(course, str) else course['subject_code']
        
        # Extract course details
        name = subjects_df[subjects_df['subject_code'] == course_code]['name'].iloc[0] if course_code in subjects_df['subject_code'].values else "Unknown course"
        utility = ""
        if burnout_scores_df is not None:
            utility_row = burnout_scores_df[burnout_scores_df['subject_code'] == course_code]
            if not utility_row.empty:
                utility = utility_row['utility'].iloc[0]
        
        top_recommendations.append({
            'subject_code': course_code,
            'name': name,
            'utility': utility
        })
    
    # Save final selections in schedule format
    subject_list = {}
    for i, course in enumerate(top_recommendations[:5], 1):
        subject_list[f"Subject {i}"] = f"{course['subject_code']}: {course['name']} (Utility: {course['utility']})"
    
    schedule_df = pd.DataFrame([{
        'NUid': nuid,
        'schedule': json.dumps(subject_list)
    }])
    
    schedule_df.to_csv(f'schedule_{nuid}.csv', index=False)
    return subject_list