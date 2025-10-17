#!/usr/bin/env groovy

@NonCPS
private def basename(path) {
    return path.drop(path.lastIndexOf('/') + 1)
}

@NonCPS
private def render_template(template_text, log_summary) {
    def binding = [
        'currentBuild': currentBuild,
        'env': env,
        'log_summary': log_summary,
    ]
    def engine = new groovy.text.SimpleTemplateEngine()
    def template_eng = engine.createTemplate(template_text).make(binding)
    return template_eng.toString()
}

// Clone llvm-project.git get the blamelist filled. This is necessary for relay
// jobs as with current jenkins we do not want to trigger the relay job with any
// parameters or blamelists. (If we would do that then jenkins won't merge
// requests anymore and we would be forced to test every single revision for
// which we don't have the hardware right now).
//
// FIXME: Make this do a --bare or --mirror clone instead of a full clone. This
// is very space-intensive.
private def clone_llvm_project(name, sha) {
        dir("pseudo-checkout-${name}") {
        checkout poll: false, changelog: true, scm: [
            $class: 'GitSCM',
            branches: [[name: sha ]],
            extensions: [[
                $class: 'CloneOption',
                reference: '/Users/Shared/llvm-project.git'
            ]],
            userRemoteConfigs: [[url: 'https://github.com/llvm/llvm-project.git']]
        ]
    }
}

private def post_build() {
    // Analyze build log.
    def log_url = "${env.BUILD_URL}/consoleText"
    def ret = sh \
        script: "curl '${log_url}' -s | config/zorg/jenkins/inspect_log.py > log_summary.html",
        returnStatus: true
    if (ret != 0 && currentBuild.currentResult == 'SUCCESS')
        currentBuild.result = 'UNSTABLE'
    def log_summary = readFile 'log_summary.html'

    // Update job description.
    description_template = readTrusted 'zorg/jenkins/job_description.template'
    def descr_body = render_template(description_template, log_summary)
    if (currentBuild.description == null)
        currentBuild.description = ""
    currentBuild.description += descr_body
}

def task_pipeline(label, body) {
    node(label) {
        try {
            stage('main') {
                dir('config') {
                    git url: 'https://github.com/llvm/llvm-zorg.git', branch: 'main', poll: false
                }
                withEnv([
                    "PATH=$PATH:$WORKSPACE/venv/bin:/usr/bin:/usr/local/bin"
                ]) {
                    withCredentials([string(credentialsId: 's3_resource_bucket', variable: 'S3_BUCKET')]) {
                        body()
                    }
                }
            }
        } catch(hudson.AbortException e) {
            // No need to print the exception if something fails inside a 'sh'
            // step.
            currentBuild.result = 'FAILURE'
        } catch (Exception e) {
            currentBuild.result = 'FAILURE'
            throw e
        } finally {
            stage('post') {
                post_build()
            }
        }
    }
}

def benchmark_pipeline(label, body) {
    properties([
        disableResume(),
        parameters([
            string(name: 'ARTIFACT'),
            string(name: 'GIT_DISTANCE'),
            string(name: 'GIT_SHA')
        ])
    ])

    currentBuild.displayName = basename(params.ARTIFACT)
    task_pipeline(label) {
        clone_llvm_project('llvm-project', params.GIT_SHA)
        body()
    }
}

def testsuite_pipeline(label, body) {
    benchmark_pipeline(label) {
        dir('lnt') {
            git url: 'https://github.com/llvm/llvm-lnt.git', branch: 'python3.8-stable', poll: false
        }
        dir('test-suite') {
            git url: 'https://github.com/llvm/llvm-test-suite.git', branch: 'main', poll: false
        }
        body()
    }
}

return this
