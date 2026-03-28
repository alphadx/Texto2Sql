<?php
$payload = ["model"=>"gpt-4.1-mini","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://api.openai.com/v1/chat/completions");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("OPENAI_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
