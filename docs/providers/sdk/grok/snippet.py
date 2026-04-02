from openai import OpenAI

client = OpenAI(api_key="${GROK_API_KEY}", base_url="https://api.x.ai/v1/chat/completions")
resp = client.chat.completions.create(model="grok-2-latest", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
