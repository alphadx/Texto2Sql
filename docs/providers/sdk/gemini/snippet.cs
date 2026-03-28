using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("GEMINI_API_KEY"));
var body = JsonSerializer.Serialize(new { model = "gemini-2.0-flash-lite", messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync("https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
