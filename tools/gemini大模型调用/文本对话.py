from google import genai

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
GEMINI_API_KEY_file = r"H:\Code\Python\travel\tools\gemini大模型调用\gemini_API"
with open(GEMINI_API_KEY_file, 'r', encoding='utf-8') as f:
    GEMINI_API_KEY = f.read().strip()

client = genai.Client(api_key=GEMINI_API_KEY)

response = client.models.generate_content(
    model="gemini-2.5-flash", contents="Explain how AI works in a few words"
)
print(response.text)