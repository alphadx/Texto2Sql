<?php
$payload = ["model"=>"MiniMax-Text-01","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://api.minimax.chat/v1/chat/completions");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("MINIMAX_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
