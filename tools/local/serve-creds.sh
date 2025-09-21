#!/usr/bin/env bash
PORT=8080
while true; do
  aws sts get-session-token --duration-seconds 900 \
    --query 'Credentials' --output json \
    | socat - TCP-LISTEN:$PORT,reuseaddr
done
