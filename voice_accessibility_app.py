import os
import time
import json
import random
import sounddevice as sd
import numpy as np
import torchaudio
import torch
import google.generativeai as genai
from transformers import pipeline
from gtts import gTTS
import PyPDF2
from io import BytesIO
import re

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAw2NboM9zg9YYgJH_icLo2RWSpYIOP19s")
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

# Audio settings
DURATION = 5  # Recording duration in seconds
SAMPLE_RATE = 16000
AUDIO_FILE = "user_input.wav"
TTS_FILE = "bot_response.mp3"

class VoiceAccessibilityApp:
    def __init__(self):
        print("Initializing Voice Accessibility App...")
        self.asr = pipeline("automatic-speech-recognition", model="openai/whisper-small")
        self.pdf_content = ""
        self.summary = ""
        self.quiz_questions = []
        self.current_question_index = 0
        self.score = 0
        self.state = "waiting_for_pdf"  # States: waiting_for_pdf, summary_ready, quiz_active, quiz_complete
        
        print("Voice Accessibility App ready!")
        self.speak("Hello! I'm your voice assistant for document learning. Please upload a PDF file to get started.")

    def speak(self, text):
        """Convert text to speech and play it"""
        try:
            print(f"Bot: {text}")
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(TTS_FILE)
            
            # Play audio based on OS
            if os.name == "nt":  # Windows
                os.system(f"start {TTS_FILE}")
            elif os.uname().sysname == "Darwin":  # macOS
                os.system(f"afplay {TTS_FILE}")
            else:  # Linux
                os.system(f"mpg123 {TTS_FILE}")
            
            # Wait for audio to finish playing
            time.sleep(min(8, len(text.split()) * 0.2))
            
        except Exception as e:
            print(f"Error in text-to-speech: {e}")

    def listen(self):
        """Record audio and convert to text"""
        try:
            print("Listening... Please speak now!")
            self.speak("I'm listening. Please speak now.")
            
            # Record audio
            audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            
            # Save audio
            waveform = torch.from_numpy(audio.T)
            torchaudio.save(AUDIO_FILE, waveform, SAMPLE_RATE)
            
            # Transcribe
            result = self.asr(AUDIO_FILE)
            user_text = result["text"].strip()
            print(f"User: {user_text}")
            
            return user_text.lower()
            
        except Exception as e:
            print(f"Error in speech recognition: {e}")
            return ""

    def extract_pdf_text(self, pdf_path):
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                # Clean up text
                text = re.sub(r'\s+', ' ', text)
                text = text.strip()
                
                return text
        except Exception as e:
            print(f"Error extracting PDF: {e}")
            return ""

    def generate_summary(self, text):
        """Generate summary using Gemini"""
        try:
            prompt = f"""
            Please create a comprehensive summary of the following document. 
            Make it suitable for audio presentation - clear, well-structured, and easy to understand when spoken aloud.
            Focus on key concepts, main ideas, and important details.
            
            Document text:
            {text[:8000]}  # Limit text to avoid token limits
            """
            
            chat = gemini_model.start_chat()
            response = chat.send_message(prompt)
            return response.text
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "I couldn't generate a summary. Please try again."

    def generate_quiz_questions(self, text, num_questions=5):
        """Generate quiz questions from the document"""
        try:
            prompt = f"""
            Based on the following document, create {num_questions} multiple choice questions.
            Each question should have 4 options (A, B, C, D) with only one correct answer.
            Format each question as JSON with this structure:
            {{
                "question": "Question text here?",
                "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
                "correct_answer": "A",
                "explanation": "Brief explanation of why this is correct"
            }}
            
            Return a JSON array of questions. Make sure questions test understanding of key concepts.
            
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
                # Fallback: create simple questions
                return self.create_fallback_questions()
                
        except Exception as e:
            print(f"Error generating quiz: {e}")
            return self.create_fallback_questions()

    def create_fallback_questions(self):
        """Create fallback questions if AI generation fails"""
        return [
            {
                "question": "Based on what you heard in the summary, what was the main topic discussed?",
                "options": ["A. Science", "B. History", "C. Mathematics", "D. Literature"],
                "correct_answer": "A",
                "explanation": "This is a general question about the document content."
            }
        ]

    def ask_quiz_question(self, question_data):
        """Ask a quiz question and get user response"""
        question_text = f"Question {self.current_question_index + 1}: {question_data['question']}"
        
        # Add options to the question
        for option in question_data['options']:
            question_text += f" {option}."
        
        question_text += " Please say your answer as 'option A', 'option B', 'option C', or 'option D'."
        
        self.speak(question_text)
        user_response = self.listen()
        
        return user_response

    def process_quiz_answer(self, user_response, correct_answer, explanation):
        """Process user's quiz answer"""
        # Extract option from user response
        user_option = ""
        if "option a" in user_response or " a " in user_response:
            user_option = "A"
        elif "option b" in user_response or " b " in user_response:
            user_option = "B"
        elif "option c" in user_response or " c " in user_response:
            user_option = "C"
        elif "option d" in user_response or " d " in user_response:
            user_option = "D"
        
        if user_option == correct_answer:
            self.score += 1
            feedback = f"Correct! {explanation}"
        else:
            feedback = f"That's not correct. The right answer is option {correct_answer}. {explanation}"
        
        self.speak(feedback)
        return user_option == correct_answer

    def run_conversation(self):
        """Main conversation loop"""
        while True:
            if self.state == "waiting_for_pdf":
                self.speak("Please tell me the path to your PDF file, or say 'quit' to exit.")
                user_input = self.listen()
                
                if "quit" in user_input or "exit" in user_input:
                    self.speak("Goodbye! Have a great day!")
                    break
                
                # For demo purposes, use the demo PDF we created
                pdf_path = "demo_machine_learning.pdf"
                print(f"Using demo PDF: {pdf_path}")
                
                if os.path.exists(pdf_path):
                    self.speak("Processing your PDF file. This may take a moment.")
                    self.pdf_content = self.extract_pdf_text(pdf_path)
                    
                    if self.pdf_content:
                        self.speak("PDF processed successfully! Shall I make a summary of this document?")
                        self.state = "summary_ready"
                    else:
                        self.speak("I couldn't read the PDF file. Please try again with a different file.")
                else:
                    self.speak("File not found. Please check the path and try again.")
            
            elif self.state == "summary_ready":
                user_input = self.listen()
                
                if "yes" in user_input or "okay" in user_input or "sure" in user_input:
                    self.speak("Creating summary now. Please wait.")
                    self.summary = self.generate_summary(self.pdf_content)
                    
                    self.speak("Here's the summary of your document:")
                    self.speak(self.summary)
                    
                    self.speak("Do you understand the summary?")
                    user_response = self.listen()
                    
                    if "yes" in user_response or "okay" in user_response:
                        self.speak("Great! Shall we have a quiz session to test your understanding?")
                        quiz_response = self.listen()
                        
                        if "yes" in quiz_response or "okay" in quiz_response or "sure" in quiz_response:
                            self.speak("Excellent! I'm preparing quiz questions based on the document.")
                            self.quiz_questions = self.generate_quiz_questions(self.pdf_content)
                            self.state = "quiz_active"
                            self.current_question_index = 0
                            self.score = 0
                        else:
                            self.speak("No problem! Would you like to hear the summary again or upload a new PDF?")
                            self.state = "waiting_for_pdf"
                    else:
                        self.speak("Would you like me to explain any part of the summary in more detail, or shall I read it again?")
                        detail_response = self.listen()
                        if "again" in detail_response or "repeat" in detail_response:
                            self.speak(self.summary)
                else:
                    self.speak("No problem! What would you like to do instead?")
                    self.state = "waiting_for_pdf"
            
            elif self.state == "quiz_active":
                if self.current_question_index < len(self.quiz_questions):
                    question = self.quiz_questions[self.current_question_index]
                    user_answer = self.ask_quiz_question(question)
                    
                    self.process_quiz_answer(user_answer, question['correct_answer'], question['explanation'])
                    self.current_question_index += 1
                    
                    if self.current_question_index < len(self.quiz_questions):
                        self.speak("Ready for the next question?")
                        ready_response = self.listen()
                        if "no" in ready_response or "stop" in ready_response:
                            self.state = "quiz_complete"
                else:
                    self.state = "quiz_complete"
            
            elif self.state == "quiz_complete":
                total_questions = len(self.quiz_questions)
                percentage = (self.score / total_questions) * 100 if total_questions > 0 else 0
                
                final_message = f"Quiz completed! You scored {self.score} out of {total_questions} questions correct. That's {percentage:.1f} percent!"
                
                if percentage >= 80:
                    final_message += " Excellent work! You have a great understanding of the material."
                elif percentage >= 60:
                    final_message += " Good job! You understood most of the key concepts."
                else:
                    final_message += " You might want to review the material again to improve your understanding."
                
                self.speak(final_message)
                self.speak("Would you like to try another PDF or take the quiz again?")
                
                continue_response = self.listen()
                if "another" in continue_response or "new" in continue_response:
                    self.state = "waiting_for_pdf"
                elif "again" in continue_response or "retry" in continue_response:
                    self.state = "quiz_active"
                    self.current_question_index = 0
                    self.score = 0
                else:
                    self.speak("Thank you for using the Voice Accessibility App! Goodbye!")
                    break
                

def main():
    """Main function to run the voice accessibility app"""
    try:
        app = VoiceAccessibilityApp()
        app.run_conversation()
    except KeyboardInterrupt:
        print("\nApp interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
