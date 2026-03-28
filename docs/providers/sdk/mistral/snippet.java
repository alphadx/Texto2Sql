var client = java.net.http.HttpClient.newHttpClient();
var json = "{\"model\":\"mistral-small-latest\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = java.net.http.HttpRequest.newBuilder(java.net.URI.create("https://api.mistral.ai/v1/chat/completions"))
    .header("Content-Type","application/json")
    .header("Authorization","Bearer " + System.getenv("MISTRAL_API_KEY"))
    .POST(java.net.http.HttpRequest.BodyPublishers.ofString(json))
    .build();
var resp = client.send(req, java.net.http.HttpResponse.BodyHandlers.ofString());
System.out.println(resp.body());
