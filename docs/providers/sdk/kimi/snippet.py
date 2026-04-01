from openai import OpenAI

client = OpenAI(api_key="${KIMI_API_KEY}", base_url="https://api.moonshot.cn/v1/chat/completions")
resp = client.chat.completions.create(model="kimi-k2", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
