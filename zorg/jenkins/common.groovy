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

private def post_build() {
    // Analyze build log.
    def base_url = 'http://labmaster2:8080/green'
    def build_url = currentBuild.getRawBuild().getUrl()
    def log_url = "${base_url}/${build_url}consoleText"
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

    // Send notification email.
    def prev_build = currentBuild.getPreviousBuild()
    if ((prev_build == null ||
         prev_build.result != currentBuild.currentResult) &&
        currentBuild.currentResult == 'FAILURE') {
        def email_template = readTrusted 'zorg/jenkins/email.template'
        def body = render_template(email_template, log_summary)
        emailext subject: '$DEFAULT_SUBJECT',
            presendScript: '$DEFAULT_PRESEND_SCRIPT',
            postsendScript: '$DEFAULT_POSTSEND_SCRIPT',
            recipientProviders: [
                [$class: 'CulpritsRecipientProvider'],
                [$class: 'DevelopersRecipientProvider'],
                [$class: 'RequesterRecipientProvider'],
            ],
            replyTo: '$DEFAULT_REPLYTO',
            to: '$DEFAULT_RECIPIENTS',
            body: body
    }
    // TODO: Notify IRC.
}

def task_pipeline(label, body) {
    node(label) {
        try {
            stage('main') {
                dir('config') {
                    svn url: 'http://llvm.org/svn/llvm-project/zorg/trunk', poll: false
                }
                body()
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
        parameters([
            string(name: 'ARTIFACT',
                   defaultValue: 'http://labmaster2.local/artifacts/clang-stage1-configure-RA_build/latest')
        ])
    ])

    currentBuild.displayName = basename(params.ARTIFACT)
    task_pipeline(label, body)
}

def testsuite_pipeline(label, body) {
    benchmark_pipeline(label) {
        dir('lnt') {
            svn url: 'http://llvm.org/svn/llvm-project/lnt/trunk', poll: false
        }
        dir('test-suite') {
            svn url: 'http://llvm.org/svn/llvm-project/test-suite/trunk', poll: false
        }
        body()
    }
}

return this
