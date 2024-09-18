create-index-and-load-data: create-index load-json-data

create-index:
	python search_index/create_search_index.py

load-json-data:
	python search_index/load_json_data.py
