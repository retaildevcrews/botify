import argparse
import asyncio
import os
import pprint
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from app.settings import AppSettings
from evaluation_utils.runnable_caller import RunnableCaller


async def call_full_flow_perf_data(index, results: list, row, semaphore: asyncio.Semaphore):
    async with semaphore:
        try:
            runnable_caller = RunnableCaller()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                runnable_caller.call_full_flow,
                row["question"],
                row["session_id"],
                row["user_id"],
                row["chat_history"],
            )
            results.append(
                {
                    "question": row["question"],
                    "answer": result["answer"],
                    "start_time": result["start_time"],
                    "end_time": result["end_time"],
                    "ellapsed_time": result["ellapsed_time"],
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "total_tokens": result["total_tokens"],
                }
            )
        except Exception as e:
            results.append(
                {
                    "question": row["question"],
                    "answer": "Error",
                    "start_time": 0,
                    "end_time": 0,
                    "ellapsed_time": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
            )
        print(f"Processed Record: {index}")


async def get_perf_numbers(dataset_path, head=-1, max_concurrent_tasks=3):
    data = pd.read_json(dataset_path, lines=True)
    if head > 0:
        data = data.head(head)
    results = []
    tasks = []
    semaphore = asyncio.Semaphore(max_concurrent_tasks)
    for i, row in data.iterrows():
        task = asyncio.create_task(call_full_flow_perf_data(i, results, row, semaphore))
        tasks.append(task)
    await asyncio.gather(*tasks)
    results_df = pd.DataFrame(results)
    return results_df


def generate_report(df, results_dir):
    app_settings = pprint.pformat(AppSettings())
    print(app_settings)

    # Calculate insights
    insights = {
        "mean_elapsed_time": df["ellapsed_time"].mean(),
        "median_elapsed_time": df["ellapsed_time"].median(),
        "std_elapsed_time": df["ellapsed_time"].std(),
        "top_90_elapsed_time": df["ellapsed_time"].quantile(0.90),
        "max_elapsed_time": df["ellapsed_time"].max(),
        "min_elapsed_time": df["ellapsed_time"].min(),
        "total_entries": len(df),
    }
    # Create a Markdown report
    report_md = f"""
# Performance Insights

## Configuration

```python

{app_settings}

```

## Summary Statistics

Mean Elapsed Time: {insights["mean_elapsed_time"]}

Median Elapsed Time: {insights["median_elapsed_time"]}

Standard Deviation: {insights["std_elapsed_time"]}

Top 90% Elapsed Time: {insights["top_90_elapsed_time"]}

Max Elapsed Time: {insights["max_elapsed_time"]}

Min Elapsed Time: {insights["min_elapsed_time"]}

Total Entries: {insights["total_entries"]}

## Plots

### Time vs Completion Tokens

![Time vs Completion Tokens](time_to_completion_tokens.png)

### Time vs Prompt Tokens

![Time vs Prompt Tokens](time_to_prompt_tokens.png)

### Time vs Total Tokens

![Time vs Total Tokens](time_to_total_tokens.png)

### Completion Tokens Distribution

![Completion Tokens Histogram](completion_tokens_hist.png)

### Prompt Tokens Distribution

![Prompt Tokens Histogram](prompt_tokens_hist.png)

### Total Tokens Distribution

![Total Tokens Histogram](total_tokens_hist.png)

### Ellapsed Time Distribution

![Elapsed Time Histogram](ellapsed_time_hist.png)
"""
    # Save the Markdown report to a file
    report_path = os.path.join(results_dir, "report.md")
    with open(report_path, "w") as file:
        file.write(report_md)


if __name__ == "__main__":
    # Run your async function to get the performance numbers
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset_path",
        help="Test dataset to use with evaluation",
        default="/workspaces/botify/evaluation/data_files/chatbot_test.jsonl",
        type=str,
    )
    parser.add_argument(
        "--head",
        help="The number of lines to run from the file, defalut is -1 which means all lines",
        default=-1,
        type=int,
    )
    args = parser.parse_args()
    df = asyncio.run(get_perf_numbers(dataset_path=args.dataset_path, head=args.head))

    # Create a directory with the name results + current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"../data_files/results/perf_results_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)

    # Save scatter plots and CSV to the created directory
    plt.scatter(df["completion_tokens"], df["ellapsed_time"])
    plt.savefig(
        os.path.join(results_dir, "time_to_completion_tokens.png"),
        format="png",
        bbox_inches="tight",
    )
    plt.clf()  # Clear the figure for the next plot

    plt.scatter(df["prompt_tokens"], df["ellapsed_time"])
    plt.savefig(
        os.path.join(results_dir, "time_to_prompt_tokens.png"),
        format="png",
        bbox_inches="tight",
    )
    plt.clf()

    plt.scatter(df["total_tokens"], df["ellapsed_time"])
    plt.savefig(
        os.path.join(results_dir, "time_to_total_tokens.png"),
        format="png",
        bbox_inches="tight",
    )
    plt.clf()

    df.hist(column="completion_tokens")
    plt.savefig(
        os.path.join(results_dir, "completion_tokens_hist.png"),
        format="png",
        bbox_inches="tight",
    )
    plt.clf()

    df.hist(column="prompt_tokens")
    plt.savefig(
        os.path.join(results_dir, "prompt_tokens_hist.png"),
        format="png",
        bbox_inches="tight",
    )
    plt.clf()

    df.hist(column="total_tokens")
    plt.savefig(
        os.path.join(results_dir, "total_tokens_hist.png"),
        format="png",
        bbox_inches="tight",
    )
    plt.clf()

    df.hist(column="ellapsed_time")
    plt.savefig(
        os.path.join(results_dir, "ellapsed_time_hist.png"),
        format="png",
        bbox_inches="tight",
    )

    plt.clf()

    # Save large token data
    large_completion_tokens = df[df["completion_tokens"] > 400]
    large_prompt_tokens = df[df["prompt_tokens"] > 8000]

    large_prompt_tokens.to_csv(
        os.path.join(results_dir, "large_prompt_tokens.csv"),
        encoding="utf-8",
        index=False,
        header=True,
    )
    large_completion_tokens.to_csv(
        os.path.join(results_dir, "large_completion_tokens.csv"),
        encoding="utf-8",
        index=False,
        header=True,
    )
    df.to_csv(
        os.path.join(results_dir, "timings.csv"),
        encoding="utf-8",
        index=False,
        header=True,
    )
    # Generate the HTML report
    generate_report(df, results_dir)
