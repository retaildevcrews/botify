import json
import os
import uuid


def run_evaluation(name, dataset_path, model_config, evaluation_function, output_path=None):
    run_id = f"{name}_{str(uuid.uuid4())}"
    evaluation_results = []
    output_path = output_path + "/eval_output" if output_path != "" else "eval_output"
    for index, line in enumerate(open(dataset_path, "r")):
        evaluation_result = evaluation_function(line, model_config)
        evaluation_results.append(
            {
                "run_id": run_id,
                "evaluation": name,
                "result": evaluation_result,
            }
        )
        print(f"Completed evaluation: {name} for line {index}")
    if output_path:
        # Ensure the output directory exists
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
        output_file = f"{output_path}/{run_id}.jsonl"
        with open(output_file, "w") as f:
            for evaluation_result in evaluation_results:
                json.dump(evaluation_result, f)
                f.write("\n")
    return evaluation_results
