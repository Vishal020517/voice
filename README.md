# Voice-First Accessibility App for Visually Impaired Users

This application provides a complete voice-only interface for document learning, designed specifically for visually impaired users. It eliminates the need for screen reading or touching, providing a seamless audio-based experience.

## Features

- **PDF Processing**: Extracts text from PDF documents
- **AI-Powered Summarization**: Creates clear, audio-friendly summaries
- **Voice-Only Interaction**: Complete hands-free operation
- **Intelligent Quiz Generation**: Creates multiple-choice questions from document content
- **Real-time Feedback**: Provides immediate responses to quiz answers
- **Conversation Flow Management**: Guides users through the entire learning process

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Google API key:
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

## Usage

1. Run the application:
```bash
python voice_accessibility_app.py
```

2. Follow the voice prompts:
   - Upload a PDF file when prompted
   - Listen to the document summary
   - Participate in the quiz session
   - Receive feedback and final scores

## Conversation Flow

1. **PDF Upload**: "Please upload a PDF file to get started"
2. **Summary Offer**: "Shall I make a summary of this document?"
3. **Summary Delivery**: Reads the AI-generated summary aloud
4. **Comprehension Check**: "Do you understand?"
5. **Quiz Offer**: "Shall we have a quiz session?"
6. **Quiz Session**: Asks questions with spoken options
7. **Answer Processing**: Provides immediate feedback
8. **Final Results**: Gives score and performance feedback

## Voice Commands

- **Affirmative**: "Yes", "Okay", "Sure"
- **Negative**: "No", "Not now"
- **Quiz Answers**: "Option A", "Option B", "Option C", "Option D"
- **Exit**: "Quit", "Exit"

## Technical Details

- **Speech Recognition**: OpenAI Whisper (whisper-small model)
- **Text-to-Speech**: Google Text-to-Speech (gTTS)
- **AI Model**: Google Gemini 2.0 Flash
- **PDF Processing**: PyPDF2
- **Audio Recording**: sounddevice library

## Accessibility Features

- Complete voice-only operation
- Clear audio feedback for all interactions
- Structured conversation flow
- No visual interface required
- Compatible with existing screen readers (TalkBack)

## Demo

A demo PDF about Machine Learning is included for testing. Run the app and use `demo_machine_learning.pdf` when prompted for a file path.

## Requirements

- Python 3.7+
- Microphone for voice input
- Speakers/headphones for audio output
- Internet connection for AI services
- Google API key for Gemini model

## Troubleshooting

- Ensure microphone permissions are granted
- Check internet connection for AI services
- Verify Google API key is properly set
- Make sure audio output device is working

## Future Enhancements

- Support for multiple document formats
- Offline mode capabilities
- Customizable quiz difficulty levels
- Progress tracking across sessions
- Multi-language support
