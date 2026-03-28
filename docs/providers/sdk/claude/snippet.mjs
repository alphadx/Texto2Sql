import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.ANTHROPIC_API_KEY, baseURL: "https://api.anthropic.com/v1/messages" });
const resp = await client.chat.completions.create({ model: "claude-3-5-haiku-latest", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
