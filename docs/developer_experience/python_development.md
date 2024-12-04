# Python Development

To ensure a level of code quality and best practices, this repo includes Python linters and formatter configuration.
Before commiting changes to the code in this repo, make sure you execute the following steps:

```bash
# navigate to root of repo
cd /workspaces/botify

# install all required tools (only required once)
poetry install

# format code - this is a pre-requisite for the linting step
make -f python.mk format

# run linters
make -f python.mk lint
```

## Evaluating and fixing linter errors

There are 5 steps to the linting process and in most cases, when one of the steps fails it won't progress any further. This means that after you fix all the errors, you should run the linters again because the additional steps will likely catch additional problems.

In some cases, you need to override a certain rule because it may be too impractical to fix. Depending on the linter that is generating the error there are different ways of doing this through config files or code annotations. This should only be used in special cases where the cost of fixing largely surpasses the benefit (e.g: test classes).

## Run Unit Tests

To get started with running the backend unit tests, run through the following steps:

```bash

# navigate to root of repo
cd /workspaces/botify

# install all required tools
poetry install --directory=apps/bot-service

# activate virtualenv
source $(poetry env info --path --directory apps/bot-service)/bin/activate

# run unit tests
python -m unittest discover -s apps/bot-service/tests/unit -t apps/bot-service/tests

# exit virtualenv
deactivate

```
