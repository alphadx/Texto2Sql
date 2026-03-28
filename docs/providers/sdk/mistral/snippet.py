from openai import OpenAI

client = OpenAI(api_key="${MISTRAL_API_KEY}", base_url="https://api.mistral.ai/v1/chat/completions")
resp = client.chat.completions.create(model="mistral-small-latest", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
