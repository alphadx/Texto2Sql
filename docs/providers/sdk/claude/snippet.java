var client = java.net.http.HttpClient.newHttpClient();
var json = "{\"model\":\"claude-3-5-haiku-latest\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = java.net.http.HttpRequest.newBuilder(java.net.URI.create("https://api.anthropic.com/v1/messages"))
    .header("Content-Type","application/json")
    .header("Authorization","Bearer " + System.getenv("ANTHROPIC_API_KEY"))
    .POST(java.net.http.HttpRequest.BodyPublishers.ofString(json))
    .build();
var resp = client.send(req, java.net.http.HttpResponse.BodyHandlers.ofString());
System.out.println(resp.body());
