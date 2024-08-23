# Performance Evaluation Program

## Overview

This program evaluates the performance of a bot by processing a dataset of user queries. It measures various metrics such as elapsed time and token usage, visualizes the results, and generates a Markdown report.

## Features

- Asynchronous processing of queries to optimize performance.
- Calculation of various performance metrics, including mean, median, and standard deviation of elapsed time.
- Generation of visualizations and a comprehensive Markdown report of the results.

## Installation/Setup

Follow these instructions to set up environment to run this program: [Eval Framework Setup Instructions]('../README.md')

## Usage

To run the program, use the following command:

```bash
python performance_analysis.py --dataset_path <path_to_your_dataset.jsonl> --head <number_of_lines>
```

### Arguments

- `--dataset_path`: Path to the JSONL dataset containing user queries (default: `evaluation/data_files/golden_datasets/golden_end_to_end_dataset_0807.jsonl`).\n-
- `--head`: Number of lines to process from the dataset (default: `-1`, which means all lines).

### Example

```bash
 python performance_analysis.py --dataset_path path/to/your/dataset.jsonl --head 100
 ```

## Output

The program generates a directory named `results_<timestamp>` containing:

**Markdown Report**:

- `report.md` with performance insights.

**Plots**: Various scatter plots and histograms saved as PNG files:

- `time_to_completion_tokens.png`
- `time_to_prompt_tokens.png`
- `time_to_total_tokens.png`
- `completion_tokens_hist.png`
- `prompt_tokens_hist.png`
- `total_tokens_hist.png`
- `ellapsed_time_hist.png`

**CSV Files**:

- `timings.csv`: All processed timing data.
- `large_prompt_tokens.csv`: Entries with prompt tokens greater than 8000.
- `large_completion_tokens.csv`: Entries with completion tokens greater than 400.

## Functionality

- **Asynchronous Data Processing**: Utilizes asyncio to efficiently handle multiple queries concurrently.
- **Performance Metrics Calculation**: Computes essential statistics on the performance of the bot.
- **Visualization**: Generates scatter plots and histograms for better insight into the performance metrics.
- **Markdown Reporting**: Compiles a report with configuration settings and performance statistics.
