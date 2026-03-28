var client = java.net.http.HttpClient.newHttpClient();
var json = "{\"model\":\"gemini-2.0-flash-lite\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = java.net.http.HttpRequest.newBuilder(java.net.URI.create("https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"))
    .header("Content-Type","application/json")
    .header("Authorization","Bearer " + System.getenv("GEMINI_API_KEY"))
    .POST(java.net.http.HttpRequest.BodyPublishers.ofString(json))
    .build();
var resp = client.send(req, java.net.http.HttpResponse.BodyHandlers.ofString());
System.out.println(resp.body());
