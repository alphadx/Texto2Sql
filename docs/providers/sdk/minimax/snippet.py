from openai import OpenAI

client = OpenAI(api_key="${MINIMAX_API_KEY}", base_url="https://api.minimax.chat/v1/chat/completions")
resp = client.chat.completions.create(model="MiniMax-Text-01", messages=[{"role":"user","content":"hola"}])
print(resp.choices[0].message.content)
