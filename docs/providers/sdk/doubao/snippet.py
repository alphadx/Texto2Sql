from openai import OpenAI

client = OpenAI(api_key="${DOUBAO_API_KEY}", base_url="https://ark.cn-beijing.volces.com/api/v3/chat/completions")
resp = client.chat.completions.create(model="doubao-pro-32k", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
