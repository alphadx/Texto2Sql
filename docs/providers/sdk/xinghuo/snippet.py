from openai import OpenAI

client = OpenAI(api_key="${XINGHUO_API_KEY}", base_url="https://spark-api-open.xf-yun.com/v1/chat/completions")
resp = client.chat.completions.create(model="generalv3.5", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
