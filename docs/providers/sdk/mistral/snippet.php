<?php
$payload = ["model"=>"mistral-small-latest","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://api.mistral.ai/v1/chat/completions");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("MISTRAL_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
