import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.PANGU_API_KEY, baseURL: "https://modelarts.cn-north-4.myhuaweicloud.com/v1/chat/completions" });
const resp = await client.chat.completions.create({ model: "pangu-pro", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
