import os
import google.generativeai as genai
from transformers import pipeline

GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY","AIzaSyAw2NboM9zg9YYgJH_icLo2RWSpYIOP19s")
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model=genai.GenerativeModel('gemini-2.0-flash')

print("Loading.........")

try:
    emotion_classifier = pipeline("sentiment-analysis", model="j-hartmann/emotion-english-distilroberta-base")
    print("Emotion detection model loaded successfully.")
except Exception as e:
    print(f"Error loading emotion detection model: {e}")
    print("Please ensure you have an active internet connection and that the model files can be downloaded.")
    exit()

def get_emotional_response(user_text: str) -> str:
    """
    Analyzes the emotion of the user's text and generates an emotionally-aware reply.

    Args:
        user_text (str): The input text from the user.

    Returns:
        str: An emotionally-tuned response from the AI.
    """
    if not user_text.strip():
        return "say something........."
    try:
        result_emotion=emotion_classifier(user_text)
        detected_emotion=result_emotion[0]['label']
        print(f"DETECTED_EMOTION:{detected_emotion}")
    except:
        print("error")
    if detected_emotion == "joy":
        system_instruction = "You are a very positive and enthusiastic assistant. Respond with excitement and warmth."
        user_prompt = f"The user expressed joy: '{user_text}'. Respond in a way that amplifies their happiness."
    elif detected_emotion == "sadness":
        system_instruction = "You are an empathetic and supportive assistant. Respond with understanding and offer comfort."
        user_prompt = f"The user expressed sadness: '{user_text}'. Offer words of comfort and support."
    elif detected_emotion == "anger":
        system_instruction = "You are a calm and de-escalating assistant. Respond patiently, acknowledge their frustration, and offer practical help if applicable."
        user_prompt = f"The user expressed anger: '{user_text}'. Respond calmly and try to de-escalate the situation."
    elif detected_emotion == "surprise":
        system_instruction = "You are an engaging and curious assistant. Respond with wonder and interest."
        user_prompt = f"The user expressed surprise: '{user_text}'. Show curiosity and acknowledge their surprise."
    elif detected_emotion == "fear":
        system_instruction = "You are a reassuring and calming assistant. Respond to alleviate their fears and offer practical steps if needed."
        user_prompt = f"The user expressed fear: '{user_text}'. Try to reassure them and address their concerns."
    elif detected_emotion == "disgust":
        system_instruction = "You are a neutral and understanding assistant. Acknowledge their feeling without judgment and try to shift to a more productive topic if appropriate."
        user_prompt = f"The user expressed disgust: '{user_text}'. Acknowledge their feeling neutrally."
    else: # Default for neutral or other less defined emotions
        system_instruction = "You are a helpful and polite assistant. Respond directly to the user's query."
        user_prompt = f"The user said: '{user_text}'. Respond appropriately."

    try:
        chat_session=gemini_model.start_chat(history=[])
        response=chat_session.send_message(f"SYSTEM INSTRUCTION: {system_instruction} \nUSER INPUT:{user_prompt}")
        generated_text=response.text
    except:
        print("error generating response......")
    return generated_text
if __name__=="__main__":
    print("WELCOME")
    while(True):
        user_input=input("\nYou:")
        if user_input.lower() in ['quit','exit']:
            print("BYE")
            break
        ai_response=get_emotional_response(user_input)
        print(f"Response:{ai_response}")
