# Default values for optional parameters
chunksize ?= 5000
chunkoverlapsize ?= 750
datafile ?= "search_index/data.jsonl"

create-index-and-load-data: create-index load-json-data

create-index:
	python search_index/create_search_index.py --chunksize $(chunksize) --chunkoverlapsize $(chunkoverlapsize)

load-json-data:
	python search_index/load_json_data.py --datafile $(datafile)
