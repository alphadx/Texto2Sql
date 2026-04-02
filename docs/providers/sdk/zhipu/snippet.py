from openai import OpenAI

client = OpenAI(api_key="${ZHIPU_API_KEY}", base_url="https://open.bigmodel.cn/api/paas/v4/chat/completions")
resp = client.chat.completions.create(model="glm-4-flash", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
