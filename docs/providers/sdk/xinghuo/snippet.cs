using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("XINGHUO_API_KEY"));
var body = JsonSerializer.Serialize(new { model = "generalv3.5", messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync("https://spark-api-open.xf-yun.com/v1/chat/completions", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
