from flask import Flask, render_template, request, jsonify
import os
import threading
import ssl
import urllib.request
import config
from utils.detector import TrafficViolationDetector
from utils.database import DatabaseManager
from werkzeug.utils import secure_filename

# Fix SSL certificate issue on Mac
ssl._create_default_https_context = ssl._create_unverified_context
urllib.request.ssl.create_default_context = lambda: ssl._create_unverified_context()

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = config.OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Create folders
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)

# Initialize managers
print("Initializing database...")
db_manager = DatabaseManager()
db_manager.create_database_and_table()

print("Initializing detector...")
detector = TrafficViolationDetector(config.HAARCASCADE_PATH)

# Processing status
processing_status = {}

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_video():
    """Upload video page and handler"""
    if request.method == 'POST':
        # Check file
        if 'video' not in request.files:
            return jsonify({'error': 'No video file'}), 400
        
        file = request.files['video']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed (mp4, avi, mov, mkv)'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        print(f"\n📤 Video uploaded: {filename}")
        
        # Process in background
        thread = threading.Thread(
            target=process_video_background, 
            args=(filepath, filename)
        )
        thread.daemon = True
        thread.start()
        
        processing_status[filename] = {
            'status': 'processing',
            'progress': 0
        }
        
        return jsonify({
            'message': 'Video processing started',
            'video_id': filename
        }), 202
    
    return render_template('upload.html')

@app.route('/status/<video_id>')
def get_status(video_id):
    """Get processing status"""
    if video_id in processing_status:
        return jsonify(processing_status[video_id])
    
    return jsonify({'status': 'not_found'}), 404

@app.route('/violations', methods=['GET'])
def get_violations():
    """Get all violations"""
    violations = db_manager.get_all_violations()
    return jsonify(violations)

@app.route('/clear-violations', methods=['POST'])
def clear_violations():
    """Clear all violations"""
    db_manager.clear_license_plates()
    return jsonify({'message': 'Violations cleared'})

# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    """Check if file type is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

def process_video_background(filepath, video_id):
    """Process video in background thread"""
    try:
        processing_status[video_id] = {
            'status': 'processing',
            'progress': 10
        }
        
        # Process video
        violations = detector.process_video(filepath)
        
        processing_status[video_id] = {
            'status': 'processing',
            'progress': 80
        }
        
        # Save to database
        for plate in violations:
            db_manager.update_database_with_violation(plate)
        
        processing_status[video_id] = {
            'status': 'completed',
            'violations': violations,
            'count': len(violations)
        }
        
        print(f"✓ Processing complete for {video_id}")
    
    except Exception as e:
        print(f"❌ Error processing {video_id}: {str(e)}")
        processing_status[video_id] = {
            'status': 'error',
            'message': str(e)
        }
    
    finally:
        # Clean up
        if os.path.exists(filepath):
            os.remove(filepath)

# ==================== MAIN ====================

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚗 Traffic Violation Detection System")
    print("="*50)
    print("📡 Starting server on http://localhost:5001")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
