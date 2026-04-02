import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.ZHIPU_API_KEY, baseURL: "https://open.bigmodel.cn/api/paas/v4/chat/completions" });
const resp = await client.chat.completions.create({ model: "glm-4-flash", messages: [{ role: "user", content: "hola" }] });
console.log(resp.choices[0].message.content);
