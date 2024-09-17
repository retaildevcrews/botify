SHELL := /bin/bash

.PHONY: create-config

create-config:
	cd ./infra/scripts && ./create-config.sh
