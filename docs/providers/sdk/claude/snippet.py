from openai import OpenAI

client = OpenAI(api_key="${ANTHROPIC_API_KEY}", base_url="https://api.anthropic.com/v1/messages")
resp = client.chat.completions.create(model="claude-3-5-haiku-latest", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
