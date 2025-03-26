from ga_recommender import generate_recommendations, save_schedule, load_burnout_scores
from utils import load_subject_data

def get_enrollment_status(seats, enrollments):
    '''
    Get enrollment messages based on the given seats and enrollments
    Params:
        Seats: Number of seats for a class
        Enrollments: Number of enrollments
    Returns:
        Enrollment user friendly status
    '''
    if seats <= 0 or enrollments <= 0:
        return "⚠️ Enrollment data not available"
    
    enrollment_ratio = enrollments / seats
    
    if enrollment_ratio >= 1:
        return "🔴 This class is currently full. Very difficult to enroll - consider for future semesters"
    elif enrollment_ratio >= 0.9:
        return "🟠 Limited seats available (>90% full). Enroll immediately if interested"
    elif enrollment_ratio >= 0.75:
        return "🟡 Class is filling up quickly (>75% full). Enroll soon to secure your spot"
    else:
        return "🟢 Good availability. Enroll at your convenience but don't wait too long"

def get_burnout_status(burnout_score, utility_score):
    '''
    Get the burnout status based on utility and burnout
    Params:
        Burnout_Score: Computed burnout score
        utility_Score: Computed utility score
    Returns:
        User-friendly brunout status
    '''
    if burnout_score is None or utility_score is None:
        return "⚠️ Burnout data not available"
    
    if burnout_score > 0.8:
        return "🔴 High burnout risk. Consider careful time management if taking this course"
    elif burnout_score > 0.6:
        return "🟠 Moderate-high burnout risk. May require significant time commitment"
    elif burnout_score > 0.4:
        return "🟡 Moderate burnout risk. Typical workload for your program"
    else:
        return "🟢 Low burnout risk. Should be manageable with your current skills"

def get_additional_interests():
    '''
    User input for users additional interests
    Returns:
        List of interests inputted by user
    '''
    print("\nWhat other areas are you interested in? (Select one or more numbers, separated by commas)")
    interests = {
        1: "artificial intelligence",
        2: "web development",
        3: "data science",
        4: "cybersecurity",
        5: "mobile development",
        6: "systems programming",
        7: "cloud computing",
        8: "software engineering",
        9: "database systems",
        10: "computer vision",
        11: "natural language processing",
        12: "algorithms",
        13: "networking",
        14: "robotics"
    }
    
    for num, interest in interests.items():
        print(f"{num}. {interest}")
    
    try:
        choices = input("\nEnter numbers (e.g., 1,3,5) or 'skip' to continue: ").strip()
        if choices.lower() == 'skip':
            return []
        
        selected = [interests[int(num.strip())] for num in choices.split(',')]
        return selected
    except:
        print("Invalid input. Continuing with current recommendations.")
        return []

def display_recommendations(recommended_courses, highly_competitive_courses, round_num=1):
    '''
    Formatting the recommendations for the user
    Params:
        Recommended_courses: Filtered out courses for a given user.
        Highly_Competetive_Courses: Courses that are highly competitive
        Round_Num: Integer
    Returns:
        User friendly recommended courses
    '''
    print(f"\n=== Round {round_num} Recommendations ===")
    
    # Display recommendations
    print("\n🎯 Recommended Courses:")
    if recommended_courses:
        for i, course in enumerate(recommended_courses, 1):
            seats = course['seats']
            enrollments = course['enrollments']
            
            print(f"\n{i}. {course['subject_code']}: {course['name']}")
            print(f"   Match Score: {course['match_score']:.1%}")
            
            # Burnout information if available
            if course['burnout_score'] is not None and course['utility_score'] is not None:
                burnout_status = get_burnout_status(course['burnout_score'], course['utility_score'])
                print(f"   Burnout Risk: {course['burnout_score']:.2f}")
                print(f"   Academic Utility: {course['utility_score']:.2f}")
                print(f"   {burnout_status}")
            
            print(f"   Reasons for recommendation:")
            for reason in course['reasons']:
                print(f"   • {reason}")
            
            # Enrollment status
            print(f"   Current Status: {seats - enrollments} seats remaining ({enrollments}/{seats} filled)")
            enrollment_status = get_enrollment_status(seats, enrollments)
            print(f"   {enrollment_status}")
            
            # Show likelihood only if relevant
            if seats > enrollments:
                likelihood_percent = course['likelihood'] * 100
                print(f"   Enrollment Likelihood: {likelihood_percent:.1f}%")
    else:
        print("No new courses found matching your immediate criteria.")
    
    # Display highly competitive courses
    if highly_competitive_courses:
        print("\n⚠️ Highly Competitive Courses:")
        for i, course in enumerate(highly_competitive_courses, 1):
            seats = course['seats']
            enrollments = course['enrollments']
            
            print(f"\n{i}. {course['subject_code']}: {course['name']}")
            print(f"   Match Score: {course['match_score']:.1%}")
            
            # Burnout information if available
            if course['burnout_score'] is not None and course['utility_score'] is not None:
                burnout_status = get_burnout_status(course['burnout_score'], course['utility_score'])
                print(f"   Burnout Risk: {course['burnout_score']:.2f}")
                print(f"   Academic Utility: {course['utility_score']:.2f}")
                print(f"   {burnout_status}")
            
            print(f"   Reasons for recommendation:")
            for reason in course['reasons']:
                print(f"   • {reason}")
            
            # Enrollment status
            print(f"   Current Status: {seats - enrollments} seats remaining ({enrollments}/{seats} filled)")
            enrollment_status = get_enrollment_status(seats, enrollments)
            print(f"   {enrollment_status}")
            
            # Additional warning for highly competitive courses
            print("   ⚠️ Note: This is a highly competitive course due to high demand")
            if seats <= enrollments:
                print("   💡 Tip: Consider registering for this course in a future semester when you'll have higher priority")
            else:
                print("   💡 Tip: If interested, prepare to register immediately when registration opens")
    return len(recommended_courses) + len(highly_competitive_courses) > 0

def recommend_schedule(nuid):
    '''
    Main function for recommending a schedule for a user
    Params:
        Nuid: Student id
    Returns:
        Reccomendation
    '''
    subjects_df, _, _, _, _ = load_subject_data()
    burnout_scores_df = load_burnout_scores(nuid)
    
    semester = int(input("Which semester are you in? "))
    
    # Keep track of recommended courses to avoid repetition
    recommended_history = set()
    
    # Initial recommendations
    round_num = 1
    recommended_courses, highly_competitive_courses = generate_recommendations(nuid, semester)
    
    if recommended_courses is None:
        print(f"Error: Could not generate recommendations for NUID: {nuid}")
        return None
    
    # Filter out previously recommended courses
    new_recommended = [course for course in recommended_courses 
                     if course['subject_code'] not in recommended_history][:5]
    new_competitive = [course for course in highly_competitive_courses 
                      if course['subject_code'] not in recommended_history][:5]
    
    # Add recommended courses to history
    for course in new_recommended + new_competitive:
        recommended_history.add(course['subject_code'])
    
    has_recommendations = display_recommendations(new_recommended, new_competitive, round_num)
    
    # Continue recommending until user is satisfied or no more courses
    while has_recommendations:
        choice = input("\nWould you like to see more recommendations? (yes/no): ").lower().strip()
        if choice != 'yes':
            break
            
        # Get additional interests
        print("\nLet's find more courses based on additional interests!")
        additional_interests = get_additional_interests()
        
        # Get new recommendations
        round_num += 1
        recommended_courses, highly_competitive_courses = generate_recommendations(
            nuid, semester, additional_interests
        )
        
        # Filter out previously recommended courses
        new_recommended = [course for course in recommended_courses 
                         if course['subject_code'] not in recommended_history][:5]
        new_competitive = [course for course in highly_competitive_courses 
                          if course['subject_code'] not in recommended_history][:5]
        
        # Add new recommendations to history
        for course in new_recommended + new_competitive:
            recommended_history.add(course['subject_code'])
        
        has_recommendations = display_recommendations(new_recommended, new_competitive, round_num)
        
        if not has_recommendations:
            print("\nNo more courses available matching your criteria.")
    
    # Save the final schedule
    schedule = save_schedule(nuid, recommended_history, subjects_df, burnout_scores_df)
    print(f"\nFinal schedule saved to schedule_{nuid}.csv")
    
    # Display final schedule summary
    print("\n=== Final Recommended Schedule ===")
    for subject_key, subject_value in schedule.items():
        print(f"{subject_key}: {subject_value}")
    
    return recommended_history

if __name__ == "__main__":
    nuid = input("Enter NUid to recommend schedule: ")
    recommend_schedule(nuid)