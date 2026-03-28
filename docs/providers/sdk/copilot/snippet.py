from openai import OpenAI

client = OpenAI(api_key="${COPILOT_API_KEY}", base_url="https://models.inference.ai.azure.com/chat/completions")
resp = client.chat.completions.create(model="gpt-4.1-mini", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
