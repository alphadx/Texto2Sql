from openai import OpenAI

client = OpenAI(api_key="${DEEPSEEK_API_KEY}", base_url="https://api.deepseek.com/v1/chat/completions")
resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
