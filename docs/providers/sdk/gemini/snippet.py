from openai import OpenAI

client = OpenAI(api_key="${GEMINI_API_KEY}", base_url="https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}")
resp = client.chat.completions.create(model="gemini-2.0-flash-lite", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
