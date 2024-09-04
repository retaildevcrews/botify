# Updating The System Prompt

## Overview

Maintaining the system prompt for a generative AI-based chatbot is a critical task that ensures the chatbot remains effective, relevant, and aligned with its intended purpose. The system prompt serves as the foundational instruction set that guides the AI's responses, influencing the quality and appropriateness of interactions.  This document describes the process for maintaining GenAI Chatbot's system prompt.  In maintaining GenAI Chatbot's system prompt, it is important to understand what the bot is attempting to do/solve, as well as how the prompt is put together.  This information can be found at:

## How to update the system prompt

### Prerequisite

In order to do this, you must have cloned the GenAI Chatbot repo or opened up the repo in a code space.

### 1. Create a New Branch

1. **Switch to the Main Branch**:
   - Ensure you are on the `main` branch before creating a new branch.

     ```bash
     git checkout main
     ```

2. **Create a New Branch**:
   - Create a new branch for your changes. Use a descriptive name for the branch.

     ```bash
     git checkout -b update-prompt-branch
     ```

### 2. Edit the Prompt Files

GenAI Chatbot has supports two types of prompt formats.  Jinja and Text, at the moment for simplicity,
text is being used to create the system prompt.  The file to be used to create the prompt can be
set in the: [app.settings](../../apps/bot-service/common/app_settings.py)

1. **Open the Prompt Files**:

   1. **Jinja Template Version**

      - Open the relevant Jinja template files in your preferred text editor. These files might be organized in a directory structure like:

      ```text
      apps/bot-service/prompts/templates/jinja
      ├── main_prompt.jinja
      ├── section1.jinja
      ├── section2.jinja
      └── ...
      ```

   2. **Text Template Version**

         - Open the relevant Text template file in your preferred text editor. These files might be organized in a directory structure like:

         ```text
         apps/bot-service/prompts/templates/text
         ├── prompt.txt

         ```

2. **Make Changes**:
   - Edit the content of the necessary Text or Jinja template files.
   - Save the changes.

3. **Test Changes Locally**:
   - [Run Application Locally](docs/developer_experience/quick_run_local.md)
   - Interact with chatbot to validate your changes

### 3. Commit the Changes

1. **Stage the Changes**:
   - Add the modified files to the staging area.

     ```bash
     git add prompts/section1.jinja prompts/section2.jinja
     ```

2. **Commit the Changes**:
   - Commit the changes with a descriptive message.

     ```bash
     git commit -m "Update section1 and section2 of the system prompt"
     ```

### 4. Push the Branch

1. **Push to Remote Repository**:
   - Push the new branch to the remote repository.

     ```bash
     git push origin update-prompt-branch
     ```

   - If branch has been pushed to origin prior only a git push is needed

    ```bash
     git push
     ```

## Review and Merge Changes

### 1. Create a Pull Request (PR)

1. **Navigate to GitHub**:
   - Go to the GitHub repository in your web browser.

2. **Create a New PR**:
   - Navigate to the "Pull requests" tab and click "New pull request".
   - Select the `update-prompt-branch` as the source branch and `main` as the target branch.
   - Add a title and description for the PR and click "Create pull request".

### 2. Review the PR

1. **Team Review**:
   - Team members review the changes in the PR.
   - Provide feedback or request changes if necessary.

2. **Address Feedback**:
   - If there are requested changes, make the necessary updates on the `update-prompt-branch`, commit, and push the changes.
   - The PR will automatically update with the new commits.

### 3. Merge the PR

1. **Approve and Merge**:
   - Once the PR is approved, merge it into the `main` branch using the GitHub interface.
   - Optionally, delete the `update-prompt-branch` after merging.

### 4. Sync Local Repository

1. **Pull the Latest Changes**:
   - After the PR is merged, ensure all team members pull the latest changes from the `main` branch.

     ```bash
     git checkout main
     git pull origin main
     ```

## Best Practices

1. **Branch Naming**:
   - Use descriptive names for branches, e.g., `update-prompt-branch`, `fix-typo-in-section1`.

2. **Commit Messages**:
   - Write clear and concise commit messages that describe the changes made.

3. **Small, Incremental Changes**:
   - Make small, incremental changes rather than large, sweeping updates. This makes it easier to review and understand changes.
