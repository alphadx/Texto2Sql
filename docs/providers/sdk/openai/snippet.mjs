import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY, baseURL: "https://api.openai.com/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "gpt-4.1-mini", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
