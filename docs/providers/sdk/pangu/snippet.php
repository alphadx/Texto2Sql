<?php
$payload = ["model"=>"pangu-pro","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://modelarts.cn-north-4.myhuaweicloud.com/v1/chat/completions");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("PANGU_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
