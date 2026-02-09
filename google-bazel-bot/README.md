# Google Bazel Bot

This folder contains all of the source code for the AI bazel build fixer bot.
The bot uses a combination of deterministic tooling and LLMs to automatically
generate PRs that fix the bazel build.

## Components

1. Terraform - The GCP resources that are needed to run the bot. This includes
   a GKE cluster and Kubernetes resources.
2. Dockerfile - The container definition used for running both the postcommit
   bazel CI and the fixer bot.
3. Fixer bot source code - The actual source code that drives the fix loop and
   interactes with Github to post a PR if it has generated a fix successfully.
