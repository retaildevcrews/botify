SHELL := /bin/bash

RG ?= ""
VAULT ?= false

.PHONY: create-config run create-index-and-load-data create-index load-json-data

create-config:
	cd ./infra/scripts && ./create-config.sh $(RG) $(VAULT)

run:
	cd ./apps && docker-compose up --build

create-index-and-load-data:
	create-index load-json-data

create-index:
	python search_index/create_search_index.py

load-json-data:
	python search_index/load_json_data.py
