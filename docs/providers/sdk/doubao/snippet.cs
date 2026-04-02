using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("DOUBAO_API_KEY"));
var body = JsonSerializer.Serialize(new { model = "doubao-pro-32k", messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync("https://ark.cn-beijing.volces.com/api/v3/chat/completions", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
