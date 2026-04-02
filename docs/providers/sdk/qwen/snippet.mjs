import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.QWEN_API_KEY, baseURL: "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "qwen-plus", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
