import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.XINGHUO_API_KEY, baseURL: "https://spark-api-open.xf-yun.com/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "generalv3.5", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
