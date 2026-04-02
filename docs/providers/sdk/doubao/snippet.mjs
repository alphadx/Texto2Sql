import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.DOUBAO_API_KEY, baseURL: "https://ark.cn-beijing.volces.com/api/v3/chat/completions" });
const resp = await client.chat.completions.create({ model: "doubao-pro-32k", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
