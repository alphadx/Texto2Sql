<?php
$payload = ["model"=>"doubao-pro-32k","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://ark.cn-beijing.volces.com/api/v3/chat/completions");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("DOUBAO_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
