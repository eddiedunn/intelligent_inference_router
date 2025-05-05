import os
import google.generativeai as genai

def test_gemini(prompt, model_name="gemini-2.5-flash-preview-04-17"):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY (or GOOGLE_API_KEY) not set.")
        return
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    try:
        print("[DEBUG] Gemini prompt:\n", prompt)
        response = model.generate_content(prompt, generation_config={"temperature": 0.2, "max_output_tokens": 2048})
        print("[DEBUG] Gemini raw response:\n", response)
        print("[DEBUG] Gemini response text:\n", getattr(response, 'text', response))
    except Exception as e:
        print(f"[ERROR] Gemini call failed: {e}")

if __name__ == "__main__":
    # Example prompt: simple, non-structured
    prompt = "List three of the most popular open-source LLMs in 2024."
    test_gemini(prompt)
