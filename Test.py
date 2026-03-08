import os
import gradio as gr
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def respond(message, history=None):
    try:
        print("📨 Prompt:", message)
        res = model.generate_content(message)
        print("✅ Gemini responded:", res.text)
        return res.text
    except Exception as e:
        import traceback
        print("❌ Gemini error:", e)
        print("🔍 Full traceback:\n", traceback.format_exc())
        return f"❌ Gemini error: {e}"



demo = gr.ChatInterface(fn=respond)
demo.launch()
