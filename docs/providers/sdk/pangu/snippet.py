from openai import OpenAI

client = OpenAI(api_key="${PANGU_API_KEY}", base_url="https://modelarts.cn-north-4.myhuaweicloud.com/v1/chat/completions")
resp = client.chat.completions.create(model="pangu-pro", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
