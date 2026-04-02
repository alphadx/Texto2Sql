<?php
$payload = ["model"=>"glm-4-flash","messages"=>[["role"=>"user","content"=>"hola"]]];
$ch = curl_init("https://open.bigmodel.cn/api/paas/v4/chat/completions");
curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("ZHIPU_API_KEY")],CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
