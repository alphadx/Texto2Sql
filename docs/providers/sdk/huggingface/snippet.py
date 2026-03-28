from openai import OpenAI

client = OpenAI(api_key="${HUGGINGFACE_API_KEY}", base_url="https://router.huggingface.co/v1/chat/completions")
resp = client.chat.completions.create(model="Qwen/Qwen2.5-3B-Instruct", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
