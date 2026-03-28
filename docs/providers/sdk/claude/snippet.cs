using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY"));
var body = JsonSerializer.Serialize(new { model = "claude-3-5-haiku-latest", messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync("https://api.anthropic.com/v1/messages", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
