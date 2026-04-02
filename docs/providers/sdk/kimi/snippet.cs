using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("KIMI_API_KEY"));
var body = JsonSerializer.Serialize(new { model = "kimi-k2", messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync("https://api.moonshot.cn/v1/chat/completions", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
