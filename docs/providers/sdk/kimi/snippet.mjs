import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.KIMI_API_KEY, baseURL: "https://api.moonshot.cn/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "kimi-k2", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
