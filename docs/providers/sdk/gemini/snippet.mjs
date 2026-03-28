import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.GEMINI_API_KEY, baseURL: "https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}" });
const resp = await client.chat.completions.create({ model: "gemini-2.0-flash-lite", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
