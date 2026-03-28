<?php
$payload = ["model"=>"gemini-2.0-flash-lite","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("GEMINI_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
