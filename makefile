include apps/credentials.env

create-index-and-load-data: create-index load-json-data

create-index:
	python search_index/create_search_index.py

load-json-data:
	python search_index/load_json_data.py

evaluation: evaluation-setup evaluation-runs

evaluation-setup:
	cd apps/bot-service && pip install .
	cd evaluation && pip install .

evalation-runs:
	python evaluation/run_evaluations/evaluate_full_flow.py
	python evaluation/run_evaluations/evaluate_bot_behavior.py
