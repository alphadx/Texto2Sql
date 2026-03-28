<?php
$payload = ["model"=>"deepseek-chat","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://api.deepseek.com/v1/chat/completions");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("DEEPSEEK_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
