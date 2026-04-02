var client = java.net.http.HttpClient.newHttpClient();
var json = "{\"model\":\"generalv3.5\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = java.net.http.HttpRequest.newBuilder(java.net.URI.create("https://spark-api-open.xf-yun.com/v1/chat/completions"))
    .header("Content-Type","application/json")
    .header("Authorization","Bearer " + System.getenv("XINGHUO_API_KEY"))
    .POST(java.net.http.HttpRequest.BodyPublishers.ofString(json))
    .build();
var resp = client.send(req, java.net.http.HttpResponse.BodyHandlers.ofString());
System.out.println(resp.body());
