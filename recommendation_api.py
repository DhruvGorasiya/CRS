# api.py
import json
from flask import Flask, request, jsonify
from burnout_calculator import calculate_scores
from ga_recommender import generate_recommendations, save_schedule
from utils import load_subject_data, load_burnout_scores

app = Flask(__name__)

@app.route('/api/burnout-scores', methods=['POST'])
def get_burnout_scores():
    data = request.get_json()
    
    # Validate required parameters
    if 'nuid' not in data:
        return jsonify({"error": "Missing required parameter: nuid"}), 400
    
    nuid = data['nuid']
    
    try:
        result = calculate_scores(nuid)
        
        if result is None:
            return jsonify({"error": f"Failed to calculate burnout scores for student {nuid}"}), 500
        
        scores = result.to_dict(orient='records')
        
        return jsonify({
            "nuid": nuid,
            "scores": scores,
            "top_scores": scores[:5] if len(scores) >= 5 else scores
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    data = request.get_json()

    # Validate required parameters
    if 'nuid' not in data:
        return jsonify({"error": "Missing required parameter: nuid"}), 400
    if 'semester' not in data:
        return jsonify({"error": "Missing required parameter: semester"}), 400
    
    nuid = data['nuid']
    semester = data['semester']
    additional_interests = data.get('additional_interests', [])
    
    try:
        recommended_courses, highly_competitive_courses = generate_recommendations(
            nuid, semester, additional_interests
        )
        
        if recommended_courses is None:
            return jsonify({"error": f"Failed to generate recommendations for student {nuid}"}), 500
        
        # Convert course objects to serializable dictionaries
        recommended_json = [course_to_dict(course) for course in recommended_courses]
        competitive_json = [course_to_dict(course) for course in highly_competitive_courses]
        
        return jsonify({
            "nuid": nuid,
            "semester": semester,
            "recommended_courses": recommended_json,
            "highly_competitive_courses": competitive_json
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def course_to_dict(course):
    """Convert course object to JSON-serializable dictionary"""
    # Create a copy of the course dictionary
    course_dict = course.copy()
    
    # Make sure all values are JSON serializable
    for key, value in course_dict.items():
        # Convert numpy types to Python native types
        if hasattr(value, 'item'):
            course_dict[key] = value.item()
    
    return course_dict

if __name__ == '__main__':
    app.run(debug=True, port=5000)