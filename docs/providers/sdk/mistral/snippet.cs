using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("MISTRAL_API_KEY"));
var body = JsonSerializer.Serialize(new { model = "mistral-small-latest", messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync("https://api.mistral.ai/v1/chat/completions", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
