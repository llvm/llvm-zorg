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

## Running locally

The bazel bot fixer that runs in GCP uses GitHub app. It uses a secret to
generate short-lived tokens which are used to interact with fork repository at
[google-bazel-bot/llvm-project](https://github.com/google-bazel-bot/llvm-project)
and upstream LLVM repository at
[llvm/llvm-project](https://github.com/llvm/llvm-project)
where PRs are created. For running the bot locally,
one must use their own personal fork to act as both fork
and PR repository. Fine-grained personal access tokens (PATs) must be
[generated](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
for the personal repository with read/write permission to `Contents`,
`Pull request`, `Workflow`.

By default, running the bot on test commits as follows disables usage of GitHub
app token and relies on user-provided environment variable, which must be
provided in test mode. For example, bot can be run on test commits as follows:

`GOOGLE_CLOUD_PROJECT=llvm-bazel GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=1 BUILDKITE_API_TOKEN=<yourkey> GITHUB_FORK_USER=<you>
GITHUB_FORK_USER_TOKEN=<yourforktoken> python bazelbot_server_main.py
--test_commits=test.commits.log --llvm_git_repo=/tmp/bazelbot-llvm-git-repo`
if using VertexAI

or

`GEMINI_API_KEY=<yourkey> GOOGLE_GENAI_USE_VERTEXAI=0
BUILDKITE_API_TOKEN=<yourkey> GITHUB_FORK_USER=<you>
GITHUB_FORK_USER_TOKEN=<yourforktoken> python bazelbot_server_main.py
--test_commits=test.commits.log --llvm_git_repo=/tmp/bazelbot-llvm-git-repo`
if using Gemini API.