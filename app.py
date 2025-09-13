from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import google.generativeai as genai
from transformers import pipeline
import PyPDF2
from gtts import gTTS
import tempfile
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, origins=['https://voice-accessibility-frontend.netlify.app', 'http://localhost:3000', 'http://127.0.0.1:5000'])
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    # Try reading from .env file
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('GOOGLE_API_KEY='):
                    GOOGLE_API_KEY = line.split('=', 1)[1].strip().strip('"')
                    break
    except FileNotFoundError:
        pass

if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY not found. Please set it in environment variables or .env file")
    GOOGLE_API_KEY = "dummy_key"  # Fallback to prevent crashes

genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Global variables to store session data
sessions = {}

class VoiceAssistant:
    def __init__(self, session_id):
        self.session_id = session_id
        self.pdf_content = ""
        self.summary = ""
        self.quiz_questions = []
        self.current_question_index = 0
        self.score = 0
        self.state = "waiting_for_pdf"
        
    def extract_pdf_text(self, pdf_path):
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                # Clean up text
                text = text.strip()
                print(f"Extracted text length: {len(text)}")
                print(f"First 200 characters: {text[:200]}")
                
                if not text:
                    print("No text extracted from PDF")
                    return "No readable text found in the PDF file."
                
                return text
        except Exception as e:
            print(f"Error extracting PDF: {e}")
            return ""

    def generate_summary(self, text):
        """Generate summary using Gemini"""
        try:
            if not text or len(text.strip()) < 10:
                return "The document appears to be empty or contains very little text."
            
            print(f"Generating summary for text of length: {len(text)}")
            print(f"Using API key: {GOOGLE_API_KEY[:10]}...")
            
            # Test API connection first
            try:
                test_chat = gemini_model.start_chat()
                test_response = test_chat.send_message("Hello, can you respond with 'API working'?")
                print(f"API test response: {test_response.text}")
            except Exception as api_error:
                print(f"API connection test failed: {api_error}")
                return self.create_fallback_summary(text)
            
            prompt = f"""
            Create a comprehensive summary of the following document. 
            Make it suitable for audio presentation - clear, well-structured, and easy to understand when spoken aloud.
            Focus on key concepts, main ideas, and important details.
            Keep the summary concise but informative, around 3-5 paragraphs.
            
            Document text:
            {text[:8000]}
            """
            
            chat = gemini_model.start_chat()
            response = chat.send_message(prompt)
            
            summary_text = response.text.strip()
            print(f"Generated summary length: {len(summary_text)}")
            print(f"Summary preview: {summary_text[:100]}...")
            
            return summary_text
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            import traceback
            traceback.print_exc()
            return self.create_fallback_summary(text)

    def create_fallback_summary(self, text):
        """Create a basic summary when AI fails"""
        try:
            # Extract first few sentences as a basic summary
            sentences = text.split('.')[:5]  # First 5 sentences
            basic_summary = '. '.join(sentences).strip()
            
            if len(basic_summary) > 500:
                basic_summary = basic_summary[:500] + "..."
            
            return f"Here's a basic summary of the document: {basic_summary}. The document contains approximately {len(text.split())} words covering various topics and concepts."
            
        except Exception as e:
            print(f"Error creating fallback summary: {e}")
            return "I was able to process your PDF file, but encountered difficulties generating a detailed summary. The document has been uploaded successfully and contains readable text content."

    def generate_quiz_questions(self, text, num_questions=5):
        """Generate quiz questions from the document"""
        try:
            prompt = f"""
            Based on the following document, create {num_questions} multiple choice questions.
            Each question should have 4 options (A, B, C, D) with only one correct answer.
            Format as JSON array with this structure:
            [
                {{
                    "question": "Question text here?",
                    "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
                    "correct_answer": "A",
                    "explanation": "Brief explanation of why this is correct"
                }}
            ]
            
            Make sure questions test understanding of key concepts.
            
            Document text:
            {text[:6000]}
            """
            
            chat = gemini_model.start_chat()
            response = chat.send_message(prompt)
            
            # Extract JSON from response
            response_text = response.text
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                questions = json.loads(json_str)
                return questions
            else:
                return self.create_fallback_questions()
                
        except Exception as e:
            print(f"Error generating quiz: {e}")
            return self.create_fallback_questions()

    def create_fallback_questions(self):
        """Create fallback questions if AI generation fails"""
        return [
            {
                "question": "Based on the document summary, what was the main topic discussed?",
                "options": ["A. Science", "B. History", "C. Mathematics", "D. Literature"],
                "correct_answer": "A",
                "explanation": "This is a general question about the document content."
            }
        ]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        
        file = request.files['pdf']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.lower().endswith('.pdf'):
            # Create session
            session_id = str(uuid.uuid4())
            assistant = VoiceAssistant(session_id)
            
            # Save uploaded file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
            file.save(filepath)
            
            print(f"Processing PDF: {filepath}")
            
            # Extract text
            assistant.pdf_content = assistant.extract_pdf_text(filepath)
            
            if assistant.pdf_content and len(assistant.pdf_content.strip()) > 10:
                assistant.state = "summary_ready"
                sessions[session_id] = assistant
                
                # Automatically generate summary
                print("Auto-generating summary...")
                assistant.summary = assistant.generate_summary(assistant.pdf_content)
                assistant.state = "summary_generated"
                
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'message': 'PDF processed successfully! Here is the summary:',
                    'summary': assistant.summary,
                    'state': 'summary_generated'
                })
            else:
                return jsonify({'error': 'Could not extract readable text from PDF. Please ensure the PDF contains text content.'}), 400
        else:
            return jsonify({'error': 'Please upload a valid PDF file'}), 400
            
    except Exception as e:
        print(f"Error in upload_pdf: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500

@app.route('/generate_summary', methods=['POST'])
def generate_summary():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if session_id not in sessions:
            return jsonify({'error': 'Invalid session'}), 400
        
        assistant = sessions[session_id]
        
        if assistant.state != "summary_ready":
            return jsonify({'error': 'Not ready for summary generation'}), 400
        
        # Generate summary
        assistant.summary = assistant.generate_summary(assistant.pdf_content)
        assistant.state = "summary_generated"
        
        return jsonify({
            'success': True,
            'summary': assistant.summary,
            'message': 'Do you understand the summary?',
            'state': 'summary_generated'
        })
        
    except Exception as e:
        return jsonify({'error': f'Error generating summary: {str(e)}'}), 500

@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if session_id not in sessions:
            return jsonify({'error': 'Invalid session'}), 400
        
        assistant = sessions[session_id]
        
        # Generate quiz questions
        assistant.quiz_questions = assistant.generate_quiz_questions(assistant.pdf_content)
        assistant.current_question_index = 0
        assistant.score = 0
        assistant.state = "quiz_active"
        
        if assistant.quiz_questions:
            first_question = assistant.quiz_questions[0]
            return jsonify({
                'success': True,
                'question': first_question,
                'question_number': 1,
                'total_questions': len(assistant.quiz_questions),
                'state': 'quiz_active'
            })
        else:
            return jsonify({'error': 'Could not generate quiz questions'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Error starting quiz: {str(e)}'}), 500

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    try:
        data = request.json
        session_id = data.get('session_id')
        user_answer = data.get('answer', '').upper()
        
        if session_id not in sessions:
            return jsonify({'error': 'Invalid session'}), 400
        
        assistant = sessions[session_id]
        
        if assistant.state != "quiz_active":
            return jsonify({'error': 'Quiz not active'}), 400
        
        current_question = assistant.quiz_questions[assistant.current_question_index]
        correct_answer = current_question['correct_answer']
        
        is_correct = user_answer == correct_answer
        if is_correct:
            assistant.score += 1
        
        feedback = f"{'Correct!' if is_correct else f'Incorrect. The right answer is {correct_answer}.'} {current_question['explanation']}"
        
        assistant.current_question_index += 1
        
        # Check if quiz is complete
        if assistant.current_question_index >= len(assistant.quiz_questions):
            assistant.state = "quiz_complete"
            total_questions = len(assistant.quiz_questions)
            percentage = (assistant.score / total_questions) * 100
            
            performance_message = ""
            if percentage >= 80:
                performance_message = "Excellent work! You have a great understanding of the material."
            elif percentage >= 60:
                performance_message = "Good job! You understood most of the key concepts."
            else:
                performance_message = "You might want to review the material again."
            
            return jsonify({
                'success': True,
                'feedback': feedback,
                'quiz_complete': True,
                'final_score': assistant.score,
                'total_questions': total_questions,
                'percentage': percentage,
                'performance_message': performance_message,
                'state': 'quiz_complete'
            })
        else:
            # Get next question
            next_question = assistant.quiz_questions[assistant.current_question_index]
            return jsonify({
                'success': True,
                'feedback': feedback,
                'quiz_complete': False,
                'next_question': next_question,
                'question_number': assistant.current_question_index + 1,
                'total_questions': len(assistant.quiz_questions),
                'current_score': assistant.score,
                'state': 'quiz_active'
            })
            
    except Exception as e:
        return jsonify({'error': f'Error processing answer: {str(e)}'}), 500

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate speech
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        
        return send_file(temp_file.name, as_attachment=True, download_name='speech.mp3', mimetype='audio/mpeg')
        
    except Exception as e:
        return jsonify({'error': f'Error generating speech: {str(e)}'}), 500

# Testing and Debug Routes
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': str(datetime.now()),
        'service': 'Voice Accessibility Learning Assistant'
    })

@app.route('/api/status')
def api_status():
    """Check API dependencies status"""
    status = {
        'google_api': 'configured' if GOOGLE_API_KEY and GOOGLE_API_KEY != "dummy_key" else 'missing',
        'upload_folder': 'exists' if os.path.exists(app.config['UPLOAD_FOLDER']) else 'missing',
        'sessions_active': len(sessions),
        'service': 'Voice Accessibility Learning Assistant'
    }
    
    # Test Google API connection
    try:
        test_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        status['google_api_connection'] = 'working'
    except Exception as e:
        status['google_api_connection'] = f'error: {str(e)}'
    
    return jsonify(status)

@app.route('/test/tts')
def test_tts():
    """Test text-to-speech functionality"""
    try:
        test_text = "This is a test of the text-to-speech system."
        tts = gTTS(text=test_text, lang='en', slow=False)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        
        return send_file(temp_file.name, as_attachment=True, download_name='tts_test.mp3', mimetype='audio/mpeg')
        
    except Exception as e:
        return jsonify({'error': f'TTS test failed: {str(e)}'}), 500

@app.route('/test/ai', methods=['POST'])
def test_ai():
    """Test AI text generation"""
    try:
        test_prompt = request.json.get('prompt', 'Hello, this is a test prompt.')
        
        response = gemini_model.generate_content(test_prompt)
        
        return jsonify({
            'success': True,
            'prompt': test_prompt,
            'response': response.text,
            'timestamp': str(datetime.now())
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'AI test failed: {str(e)}'
        }), 500

@app.route('/test/session')
def test_session():
    """Create a test session for debugging"""
    try:
        test_session_id = str(uuid.uuid4())
        assistant = VoiceAssistant(test_session_id)
        sessions[test_session_id] = assistant
        
        return jsonify({
            'success': True,
            'session_id': test_session_id,
            'state': assistant.state,
            'message': 'Test session created successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Session test failed: {str(e)}'
        }), 500

@app.route('/debug/sessions')
def debug_sessions():
    """Debug endpoint to view active sessions"""
    session_info = {}
    for session_id, assistant in sessions.items():
        session_info[session_id] = {
            'state': assistant.state,
            'has_pdf_content': bool(assistant.pdf_content),
            'has_summary': bool(assistant.summary),
            'quiz_questions_count': len(assistant.quiz_questions),
            'current_question_index': assistant.current_question_index,
            'score': assistant.score
        }
    
    return jsonify({
        'total_sessions': len(sessions),
        'sessions': session_info
    })

@app.route('/test/upload-form')
def test_upload_form():
    """Simple HTML form for testing file uploads"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test PDF Upload</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .container { max-width: 500px; margin: 0 auto; }
            .form-group { margin: 20px 0; }
            input[type="file"] { padding: 10px; }
            button { background: #ff8c00; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .result { margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Test PDF Upload</h2>
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="pdf">Select PDF file:</label><br>
                    <input type="file" id="pdf" name="pdf" accept=".pdf" required>
                </div>
                <button type="submit">Upload and Test</button>
            </form>
            <div id="result" class="result" style="display:none;"></div>
        </div>
        
        <script>
            document.getElementById('uploadForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData();
                const fileInput = document.getElementById('pdf');
                formData.append('pdf', fileInput.files[0]);
                
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = 'Uploading...';
                
                try {
                    const response = await fetch('/upload_pdf', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    resultDiv.innerHTML = 'Error: ' + error.message;
                }
            });
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    from datetime import datetime
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
