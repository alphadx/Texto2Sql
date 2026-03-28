import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.DEEPSEEK_API_KEY, baseURL: "https://api.deepseek.com/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "deepseek-chat", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
