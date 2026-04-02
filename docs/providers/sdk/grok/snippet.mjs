import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.GROK_API_KEY, baseURL: "https://api.x.ai/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "grok-2-latest", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
