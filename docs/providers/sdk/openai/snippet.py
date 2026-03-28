from openai import OpenAI

client = OpenAI(api_key="${OPENAI_API_KEY}", base_url="https://api.openai.com/v1/chat/completions")
resp = client.chat.completions.create(model="gpt-4.1-mini", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
