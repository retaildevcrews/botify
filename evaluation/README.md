# Evaluation Approach - Ensuring Confidence and Reliability

- [Introduction](#introduction)
- [Execute Evaluation Flows](./run_evaluations/README.md)
- [Available Evaluators](#custom-evaluators)

## Introduction

The evaluation phase is crucial in developing a generative AI solution to ensure
the system behaves as desired and meets performance expectations.
During this phase, the solution undergoes a series of evaluations whose
results are analyzed to identify strengths and areas for improvement.
Based on these insights, the solution is refined and updated.  The solution iteratively
improved until evaluation results are satisfactory.
Once satisfactory, the solution becomes a candidate for deployment.

This project leverages the PromptFlow Eval Package to perform evaluation tasks.
You can find the official documentation [here](https://microsoft.github.io/promptflow/reference/python-library-reference/promptflow-evals/promptflow.html).

## Available Evaluators

These evaluators use PromptFlow Evals Module to implement different evaluation strategies and produce metrics based on
thos strategies.

- [Bot Behavior Evaluator](./evaluators/bot_behavior/README.md) - The Bot Behavior Evaluator is a tool designed
to assess the alignment of a bot's responses with predefined expected behaviors.
- [Coherrence Evaluator](./evaluators/coherence/README.md) - The Coherence Evaluator is a specialized tool designed
to measure the coherence of answers in question-answering (QA) scenarios. Coherence refers to how well the sentences in a
response fit together to form a logical and natural flow of ideas. This evaluator is crucial for assessing the quality
of communication in automated systems, ensuring that the responses generated are not only relevant but also articulate
and easy to understand.
