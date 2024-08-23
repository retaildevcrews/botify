#!/bin/bash

_cur_dir=$(dirname "$0")
_frontend_dir="$_cur_dir/frontend"
_backend_dir="$_cur_dir/backend/langserve"

docker build -t rag-example-frontend "$_frontend_dir"
docker build -t rag-example-backend "$_backend_dir"
