import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.MISTRAL_API_KEY, baseURL: "https://api.mistral.ai/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "mistral-small-latest", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
