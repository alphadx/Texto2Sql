<?php
$payload = ["model"=>"claude-3-5-haiku-latest","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://api.anthropic.com/v1/messages");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("ANTHROPIC_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
