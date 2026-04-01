from openai import OpenAI

client = OpenAI(api_key="${QWEN_API_KEY}", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
resp = client.chat.completions.create(model="qwen-plus", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
