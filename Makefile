SHELL := /bin/bash

RG ?= ""
VAULT ?= false

.PHONY: create-config run

create-config:
	cd ./infra/scripts && ./create-config.sh $(RG) $(VAULT)

run:
	cd ./apps && docker-compose up --build
