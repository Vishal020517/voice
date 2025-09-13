class VoiceAssistant {
    constructor() {
        this.sessionId = null;
        this.currentState = 'waiting_for_pdf';
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isRecording = false;
        this.currentAudio = null;
        
        this.initializeElements();
        this.initializeSpeechRecognition();
        this.bindEvents();
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chat-messages');
        this.uploadBtn = document.getElementById('upload-btn');
        this.pdfInput = document.getElementById('pdf-input');
        this.uploadStatus = document.getElementById('upload-status');
        this.voiceBtn = document.getElementById('voice-btn');
        this.playBtn = document.getElementById('play-btn');
        this.yesBtn = document.getElementById('yes-btn');
        this.noBtn = document.getElementById('no-btn');
        this.quizControls = document.getElementById('quiz-controls');
        this.voiceControls = document.getElementById('voice-controls');
        this.actionButtons = document.getElementById('action-buttons');
        this.uploadSection = document.getElementById('upload-section');
        this.statusText = document.getElementById('status-text');
        this.loadingSpinner = document.getElementById('loading-spinner');
        this.ttsAudio = document.getElementById('tts-audio');
    }

    initializeSpeechRecognition() {
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
        } else if ('SpeechRecognition' in window) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
        } else {
            console.warn('Speech recognition not supported');
        }
    }

    bindEvents() {
        this.uploadBtn.addEventListener('click', () => this.pdfInput.click());
        this.pdfInput.addEventListener('change', (e) => this.handlePDFUpload(e));
        
        if (this.recognition) {
            this.voiceBtn.addEventListener('mousedown', () => this.startRecording());
            this.voiceBtn.addEventListener('mouseup', () => this.stopRecording());
            this.voiceBtn.addEventListener('touchstart', () => this.startRecording());
            this.voiceBtn.addEventListener('touchend', () => this.stopRecording());
        }

        this.yesBtn.addEventListener('click', () => this.handleYesNo('yes'));
        this.noBtn.addEventListener('click', () => this.handleYesNo('no'));

        // Quiz option buttons
        document.querySelectorAll('.quiz-option').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.selectQuizOption(e.target.dataset.option);
            });
        });

        this.playBtn.addEventListener('click', () => this.playLastResponse());
    }

    async handlePDFUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        this.showLoading('Processing PDF...');
        
        const formData = new FormData();
        formData.append('pdf', file);

        try {
            const response = await fetch('/upload_pdf', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (data.success) {
                this.sessionId = data.session_id;
                this.currentState = data.state;
                this.addMessage('user', `📄 Uploaded: ${file.name}`);
                this.addMessage('bot', data.message);
                this.speakText(data.message);
                
                // If summary is included, display it
                if (data.summary) {
                    this.showTypingIndicator();
                    setTimeout(() => {
                        this.hideTypingIndicator();
                        this.addMessage('bot', data.summary, true);
                        this.speakText(data.summary);
                        
                        setTimeout(() => {
                            this.showTypingIndicator();
                            setTimeout(() => {
                                this.hideTypingIndicator();
                                this.addMessage('bot', 'Do you understand the summary?', true);
                                this.speakText('Do you understand the summary?');
                                this.showActionButtons();
                            }, 1500);
                        }, 3000);
                    }, 2000);
                } else {
                    this.showActionButtons();
                }
                
                this.uploadSection.style.display = 'none';
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError('Error uploading PDF: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async generateSummary() {
        this.showLoading('Generating summary...');
        
        try {
            const response = await fetch('/generate_summary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.currentState = data.state;
                this.addMessage('bot', `📝 Summary:\n\n${data.summary}`);
                this.speakText(data.summary);
                
                setTimeout(() => {
                    this.addMessage('bot', data.message);
                    this.speakText(data.message);
                    this.showActionButtons();
                }, 2000);
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError('Error generating summary: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async startQuiz() {
        this.showLoading('Preparing quiz...');
        
        try {
            const response = await fetch('/start_quiz', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showTypingIndicator();
                setTimeout(() => {
                    this.hideTypingIndicator();
                    this.displayQuizQuestion(data.question, data.question_number, data.total_questions);
                    this.hideActionButtons();
                    this.showQuizControls();
                }, 1500);
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError('Error starting quiz: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async submitAnswer(answer) {
        this.showLoading('Checking answer...');
        
        try {
            const response = await fetch('/submit_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    answer: answer
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showTypingIndicator();
                setTimeout(() => {
                    this.hideTypingIndicator();
                    this.addMessage('bot', data.feedback, true);
                    this.speakText(data.feedback);
                    
                    if (data.quiz_complete) {
                        setTimeout(() => {
                            this.showTypingIndicator();
                            setTimeout(() => {
                                this.hideTypingIndicator();
                                const finalMessage = `Quiz Complete! Score: ${data.final_score} out of ${data.total_questions}. That's ${data.percentage.toFixed(1)} percent. ${data.performance_message}`;
                                this.addMessage('bot', finalMessage, true);
                                this.speakText(finalMessage);
                                this.hideQuizControls();
                                this.showRestartOptions();
                            }, 1500);
                        }, 3000);
                    } else {
                        setTimeout(() => {
                            this.showTypingIndicator();
                            setTimeout(() => {
                                this.hideTypingIndicator();
                                this.displayQuizQuestion(data.next_question, data.question_number, data.total_questions);
                            }, 1500);
                        }, 3000);
                    }
                }, 1000);
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError('Error submitting answer: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    displayQuizQuestion(question, questionNumber, totalQuestions) {
        const questionText = `Question ${questionNumber} of ${totalQuestions}. ${question.question}. ${question.options.join('. ')}`;
        this.addMessage('bot', questionText, true);
        this.speakText(questionText);
    }

    selectQuizOption(option) {
        // Visual feedback
        document.querySelectorAll('.quiz-option').forEach(btn => {
            btn.classList.remove('selected');
        });
        document.querySelector(`[data-option="${option}"]`).classList.add('selected');
        
        this.addMessage('user', `Selected: Option ${option}`);
        this.submitAnswer(option);
    }

    handleYesNo(response) {
        this.addMessage('user', response === 'yes' ? '✅ Yes' : '❌ No');
        
        if (this.currentState === 'summary_ready' && response === 'yes') {
            this.generateSummary();
        } else if (this.currentState === 'summary_generated' && response === 'yes') {
            this.showTypingIndicator();
            setTimeout(() => {
                this.hideTypingIndicator();
                this.addMessage('bot', 'Great! Shall we have a quiz session?', true);
                this.speakText('Great! Shall we have a quiz session?');
            }, 1500);
        } else if (response === 'yes' && this.currentState === 'summary_generated') {
            this.startQuiz();
        } else {
            this.showTypingIndicator();
            setTimeout(() => {
                this.hideTypingIndicator();
                this.addMessage('bot', 'No problem! What would you like to do?', true);
                this.speakText('No problem! What would you like to do?');
            }, 1000);
        }
    }

    startRecording() {
        if (!this.recognition || this.isRecording) return;
        
        this.isRecording = true;
        this.voiceBtn.textContent = '🔴 Recording...';
        this.voiceBtn.classList.add('recording');
        this.statusText.textContent = 'Listening...';
        
        this.recognition.start();
        
        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.addMessage('user', `🎤 "${transcript}"`);
            this.processVoiceInput(transcript);
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.stopRecording();
        };
    }

    stopRecording() {
        if (!this.isRecording) return;
        
        this.isRecording = false;
        this.voiceBtn.textContent = '🎤 Hold to Speak';
        this.voiceBtn.classList.remove('recording');
        this.statusText.textContent = 'Ready';
        
        if (this.recognition) {
            this.recognition.stop();
        }
    }

    processVoiceInput(transcript) {
        const text = transcript.toLowerCase();
        
        if (text.includes('yes') || text.includes('okay') || text.includes('sure')) {
            this.handleYesNo('yes');
        } else if (text.includes('no') || text.includes('nope')) {
            this.handleYesNo('no');
        } else if (text.includes('option a') || text.includes(' a ')) {
            this.selectQuizOption('A');
        } else if (text.includes('option b') || text.includes(' b ')) {
            this.selectQuizOption('B');
        } else if (text.includes('option c') || text.includes(' c ')) {
            this.selectQuizOption('C');
        } else if (text.includes('option d') || text.includes(' d ')) {
            this.selectQuizOption('D');
        }
    }

    async speakText(text, autoPlay = true) {
        try {
            const response = await fetch('/text_to_speech', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text })
            });

            if (response.ok) {
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                
                if (this.currentAudio) {
                    this.currentAudio.pause();
                }
                
                this.currentAudio = new Audio(audioUrl);
                
                if (autoPlay) {
                    this.currentAudio.play();
                }
                
                return audioUrl;
            }
        } catch (error) {
            console.error('Error with text-to-speech:', error);
            if (autoPlay) {
                this.fallbackSpeak(text);
            }
        }
    }

    fallbackSpeak(text) {
        if (this.synthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1;
            utterance.volume = 1;
            this.synthesis.speak(utterance);
        }
    }

    playLastResponse() {
        if (this.currentAudio) {
            this.currentAudio.currentTime = 0;
            this.currentAudio.play();
        }
    }

    addMessage(sender, content, isAudio = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const speaker = document.createElement('span');
        speaker.className = 'speaker';
        speaker.textContent = sender === 'bot' ? '🤖 Assistant' : '👤 You';
        
        if (isAudio && sender === 'bot') {
            // Create audio message with play button
            const audioMessage = document.createElement('div');
            audioMessage.className = 'audio-message';
            
            const playBtn = document.createElement('button');
            playBtn.className = 'play-audio-btn';
            playBtn.innerHTML = '▶️ Play Response';
            playBtn.dataset.text = content;
            
            const status = document.createElement('span');
            status.className = 'audio-status';
            status.textContent = 'Ready to play';
            
            playBtn.addEventListener('click', () => this.playAudioMessage(playBtn, content));
            
            audioMessage.appendChild(playBtn);
            audioMessage.appendChild(status);
            messageContent.appendChild(speaker);
            messageContent.appendChild(audioMessage);
        } else {
            // For user messages or non-audio, show brief text
            const text = document.createElement('p');
            text.textContent = sender === 'user' ? content : '🎵 Audio message';
            text.style.whiteSpace = 'pre-line';
            
            messageContent.appendChild(speaker);
            messageContent.appendChild(text);
        }
        
        messageDiv.appendChild(messageContent);
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    showActionButtons() {
        this.actionButtons.style.display = 'block';
        this.voiceControls.style.display = 'block';
    }

    hideActionButtons() {
        this.actionButtons.style.display = 'none';
    }

    showQuizControls() {
        this.quizControls.style.display = 'block';
        this.voiceControls.style.display = 'block';
    }

    hideQuizControls() {
        this.quizControls.style.display = 'none';
        this.voiceControls.style.display = 'none';
    }

    showRestartOptions() {
        this.showTypingIndicator();
        setTimeout(() => {
            this.hideTypingIndicator();
            this.addMessage('bot', 'Would you like to upload another PDF or retake the quiz?', true);
            this.speakText('Would you like to upload another PDF or retake the quiz?');
            this.uploadSection.style.display = 'block';
        }, 2000);
    }

    showLoading(message) {
        this.statusText.textContent = message;
        this.loadingSpinner.style.display = 'block';
    }

    hideLoading() {
        this.statusText.textContent = 'Ready';
        this.loadingSpinner.style.display = 'none';
    }

    async playAudioMessage(button, text) {
        try {
            button.classList.add('playing');
            button.innerHTML = '⏸️ Playing...';
            
            const audioUrl = await this.speakText(text, true);
            
            // Update status when audio ends
            if (this.currentAudio) {
                this.currentAudio.onended = () => {
                    button.classList.remove('playing');
                    button.innerHTML = '▶️ Play Again';
                    button.nextElementSibling.textContent = 'Finished';
                };
            }
        } catch (error) {
            console.error('Error playing audio:', error);
            button.classList.remove('playing');
            button.innerHTML = '▶️ Play Response';
        }
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typing-indicator';
        
        typingDiv.innerHTML = `
            <span>🤖 Assistant is responding</span>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        
        this.chatMessages.appendChild(typingDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    showError(message) {
        this.uploadStatus.textContent = message;
        this.uploadStatus.className = 'upload-status error';
        setTimeout(() => {
            this.uploadStatus.textContent = '';
            this.uploadStatus.className = 'upload-status';
        }, 5000);
    }
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new VoiceAssistant();
});
