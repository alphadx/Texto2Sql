<?php
$payload = ["model"=>"Qwen/Qwen2.5-3B-Instruct","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://router.huggingface.co/v1/chat/completions");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("HUGGINGFACE_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
