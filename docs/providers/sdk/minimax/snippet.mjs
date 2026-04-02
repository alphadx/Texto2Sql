import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.MINIMAX_API_KEY, baseURL: "https://api.minimax.chat/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "MiniMax-Text-01", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
