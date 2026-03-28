using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("COPILOT_API_KEY"));
var body = JsonSerializer.Serialize(new { model = "gpt-4.1-mini", messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync("https://models.inference.ai.azure.com/chat/completions", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
