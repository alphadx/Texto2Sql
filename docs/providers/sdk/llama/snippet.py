from openai import OpenAI

client = OpenAI(api_key="${LLAMA_API_KEY}", base_url="https://router.huggingface.co/v1/chat/completions")
resp = client.chat.completions.create(model="meta-llama/Llama-3.1-8B-Instruct", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
