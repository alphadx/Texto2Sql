import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.LLAMA_API_KEY, baseURL: "https://router.huggingface.co/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "meta-llama/Llama-3.1-8B-Instruct", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
