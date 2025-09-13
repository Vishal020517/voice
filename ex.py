import os
import torch
import re
import time
import sounddevice as sd
import numpy as np
import torchaudio
import google.generativeai as genai
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from transformers import pipeline
from gtts import gTTS # Google Text-to-Speech library
import subprocess # NEW: Used to run external commands, like SadTalker

# --- Configuration ---
# IMPORTANT: Replace with your actual GOOGLE_API_KEY if not set as an environment variable
# For Canvas environment, __app_id is automatically provided.
# For local testing, ensure GOOGLE_API_KEY is set in your environment or replace the placeholder.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "") # Leave empty string for Canvas auto-injection
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

# --- SadTalker Specific Configuration (NEW) ---
# IMPORTANT: You MUST set these paths to your actual SadTalker installation and source image.
# Example: SADTALKER_PATH = "/Users/youruser/Desktop/sad_talker/SadTalker"
# Example: SOURCE_IMAGE_PATH = "/Users/youruser/Pictures/my_avatar.jpg"
SADTALKER_PATH = "/path/to/your/SadTalker/directory" # <--- REPLACE THIS WITH YOUR SADTALKER PATH
SOURCE_IMAGE_PATH = "/path/to/your/source_image.jpg" # <--- REPLACE THIS WITH YOUR SOURCE IMAGE PATH
SADTALKER_OUTPUT_DIR = "./sadtalker_output" # Directory where SadTalker will save the video

# --- NLTK Downloads (Run once) ---
# These are necessary for text preprocessing (stopwords, lemmatization)
try:
    nltk.data.find('corpora/stopwords')
except nltk.downloader.DownloadError:
    nltk.download('stopwords')
try:
    nltk.data.find('corpora/wordnet')
except nltk.downloader.DownloadError:
    nltk.download('wordnet')

# --- Audio Recording Parameters ---
DURATION = 5 # Duration of recording in seconds
SAMPLE_RATE = 16000 # Sample rate for audio (Hz)

# --- Text Preprocessing Setup ---
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

def preprocess_text(text):
    """
    Cleans and normalizes text for emotion classification.
    - Converts to lowercase.
    - Removes non-alphabetic characters.
    - Removes stopwords.
    - Applies lemmatization (reduces words to their base form).
    """
    text = text.lower() # Convert to lowercase
    text = re.sub(r'[^a-z\s]', '', text) # Remove non-alphabetic characters
    words = [lemmatizer.lemmatize(word) for word in text.split() if word not in stop_words] # Lemmatize and remove stopwords
    return ' '.join(words) # Join words back into a string

# --- Text-to-Speech Function ---
def text_to_speech_gtts(text, lang='en', filename='ai_response_audio.mp3'):
    """
    Converts text to speech using Google Text-to-Speech (gTTS) and saves it to a file.
    This audio file will be the input for SadTalker.
    """
    try:
        print(f"Generating AI Response Audio to '{filename}'...")
        tts = gTTS(text=text, lang=lang, slow=False) # Create gTTS object
        tts.save(filename) # Save the generated audio to a file
        print(f"AI Response Audio saved successfully to '{filename}'.")
        # Note: We are not playing the audio directly here, as the primary goal
        # is to generate the file for SadTalker. Local playback can be added
        # by the user if needed, but it might not work consistently in all environments.
    except Exception as e:
        print(f"An error occurred during text-to-speech generation: {e}")
        print("Ensure you have an active internet connection for gTTS to work.")

# --- Emotion Classifier Training ---
print("Loading dataset and training emotion classifier...")
# Load a pre-existing emotion dataset from Hugging Face Datasets
dataset = load_dataset("dair-ai/emotion", split="train")
# Preprocess the text data from the dataset
X_train = [preprocess_text(item['text']) for item in dataset]
# Extract the corresponding labels (emotions)
y_train = [item['label'] for item in dataset]
# Get the human-readable names for the emotion labels
label_names = dataset.features['label'].names

# Create a machine learning pipeline for emotion classification
# 1. TfidfVectorizer: Converts text into numerical features (TF-IDF scores)
#    - max_features: Limits the number of features to the top 5000 most frequent words/bigrams.
#    - ngram_range: Considers single words (unigrams) and two-word phrases (bigrams).
# 2. LogisticRegression: A linear model used for classification.
#    - max_iter: Maximum number of iterations for the solver to converge.
#    - solver: Algorithm to use for optimization. 'liblinear' is good for small datasets.
emotion_model = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
    ('classifier', LogisticRegression(max_iter=1000, solver='liblinear'))
])
# Train the emotion classifier on the preprocessed text and labels
emotion_model.fit(X_train, y_train)
print("Emotion classifier ready.\n")

# --- Gemini Response Generation Function ---
def generate_emotional_response(text, emotion):
    """
    Generates a text response from the Gemini model, tailored to the detected emotion.
    """
    # Define system instructions for different emotions
    instructions = {
        "joy": "You are positive and enthusiastic. Respond with excitement.",
        "sadness": "You are empathetic and supportive. Offer comfort.",
        "anger": "You are calm and neutral. De-escalate the emotion.",
        "surprise": "You are curious. Express amazement and interest.",
        "fear": "You are reassuring. Reduce fear and give confidence.",
        "disgust": "You are understanding. React neutrally.",
        # Default instruction if emotion is not in the dictionary
        "neutral": "You are polite and helpful.",
    }
    # Get the specific instruction based on the detected emotion, or use a default
    system_instruction = instructions.get(emotion, "You are polite and helpful.")
    # Craft the user prompt for Gemini, including the detected emotion and original text
    user_prompt = f"The user expressed '{emotion}': '{text}'. Reply in english and appropriately."

    try:
        # Start a chat session with the Gemini model
        chat = gemini_model.start_chat()
        # Send the combined system instruction and user prompt to Gemini
        response = chat.send_message(f"SYSTEM INSTRUCTION: {system_instruction}\nUSER INPUT: {user_prompt}")
        return response.text # Return Gemini's text response
    except Exception as e:
        # Handle potential errors during API call
        return f"Error generating response from Gemini: {e}"

# --- Main Pipeline Execution ---

# 1. Record User's Speech
print("Recording... Speak now!")
# Record audio from the default microphone for a specified duration
audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
sd.wait() # Wait until the recording is finished
print("Recording finished.")

# 2. Save Recorded Audio
# Convert the NumPy array (from sounddevice) to a PyTorch tensor
waveform = torch.from_numpy(audio.T)
# Save the recorded audio to a WAV file
torchaudio.save("live_input.wav", waveform, SAMPLE_RATE)
print("Recorded audio saved to 'live_input.wav'.")

# 3. Transcribe Speech to Text (ASR)
print("Transcribing audio...")
# Initialize a pre-trained Automatic Speech Recognition (ASR) pipeline using Whisper-small model
asr = pipeline("automatic-speech-recognition", model="openai/whisper-small")
# Transcribe the saved audio file
transcribed_text = asr("live_input.wav")["text"]
print(f"Transcribed Text: {transcribed_text}")

# 4. Detect Emotion from Transcribed Text
print("Detecting emotion...")
# Preprocess the transcribed text for the emotion classifier
processed_input = preprocess_text(transcribed_text)
# Predict the emotion label using the trained emotion model
predicted_label = emotion_model.predict([processed_input])[0]
# Get the human-readable emotion name from the label_names list
detected_emotion = label_names[predicted_label]
print(f"Detected Emotion: {detected_emotion}")

# 5. Generate Emotional AI Response
print("Generating AI response...")
# Call the Gemini function to get an emotionally tailored response
ai_response_text = generate_emotional_response(transcribed_text, detected_emotion)
print(f"\nAI Response Text: {ai_response_text}")

# 6. Convert AI Response to Speech
# This will save the audio file that SadTalker will use
output_audio_filename = 'ai_response_for_sadtalker.mp3'
text_to_speech_gtts(ai_response_text, filename=output_audio_filename)

# --- SadTalker Integration (NEW) ---
print("\n--- Running SadTalker to generate talking head video ---")

# Ensure the output directory exists
os.makedirs(SADTALKER_OUTPUT_DIR, exist_ok=True)

# Construct the SadTalker command
# We use 'python' assuming it's in the PATH or the SadTalker environment is active.
# Adjust 'python' to 'python3' or a full path if needed.
# Added '--cpu' flag as a common requirement if no GPU is available or configured.
sadtalker_command = [
    "python",
    os.path.join(SADTALKER_PATH, "inference.py"),
    "--driven_audio", output_audio_filename,
    "--source_image", SOURCE_IMAGE_PATH,
    "--result_dir", SADTALKER_OUTPUT_DIR,
    "--cpu" # Add --cpu if you don't have a GPU or compatible CUDA setup for SadTalker
]

try:
    print(f"Executing SadTalker command: {' '.join(sadtalker_command)}")
    # Run the SadTalker command as a subprocess
    # capture_output=True will capture stdout and stderr
    # text=True decodes stdout/stderr as text
    # check=True will raise a CalledProcessError if the command returns a non-zero exit code
    result = subprocess.run(sadtalker_command, capture_output=True, text=True, check=True)
    print("\nSadTalker Output (stdout):\n", result.stdout)
    if result.stderr:
        print("\nSadTalker Errors (stderr):\n", result.stderr)
    print(f"\nSadTalker process completed. Check '{SADTALKER_OUTPUT_DIR}' for the generated video.")

except FileNotFoundError:
    print(f"ERROR: 'python' command or SadTalker's 'inference.py' not found.")
    print(f"Please ensure '{SADTALKER_PATH}/inference.py' exists and 'python' is in your system's PATH or SadTalker's environment is activated.")
except subprocess.CalledProcessError as e:
    print(f"ERROR: SadTalker command failed with exit code {e.returncode}")
    print("Command:", e.cmd)
    print("Stdout:", e.stdout)
    print("Stderr:", e.stderr)
    print("Please check SadTalker's installation, dependencies, and the provided paths.")
except Exception as e:
    print(f"An unexpected error occurred during SadTalker execution: {e}")

