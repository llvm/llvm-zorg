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
    sh "curl '${log_url}' -s | config/zorg/jenkins/inspect_log.py > log_summary.html"
    def log_summary = readFile 'log_summary.html'

    // Update job description.
    description_template = readTrusted 'zorg/jenkins/job_description.template'
    def descr_body = render_template(description_template, log_summary)
    if (currentBuild.description == null)
        currentBuild.description = ""
    currentBuild.description += descr_body

    // Send notification email.
    if (currentBuild.getPreviousBuild().result != currentBuild.currentResult &&
        currentBuild.currentResult == 'FAILURE') {
        def email_template = readTrusted 'zorg/jenkins/email.template'
        def body = render_template(email_template, log_summary)
        emailext subject: '$DEFAULT_SUBJECT',
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

def pipeline(label, body) {
    properties([
        parameters([
            string(name: 'ARTIFACT',
                   defaultValue: 'http://labmaster2.local/artifacts/clang-stage1-configure-RA_build/latest')
        ])
    ])

    currentBuild.displayName = basename(params.ARTIFACT)
    node(label) {
        try {
            stage('main') {
                dir('config') {
                    svn url: 'http://llvm.org/svn/llvm-project/zorg/trunk', poll: false
                }
                body()
            }
        } catch(Exception e) {
            currentBuild.result = 'FAILURE'
        } finally {
            stage('post') {
                post_build()
            }
        }
    }
}

def testsuite_pipeline(label, body) {
    pipeline(label) {
        dir('lnt') {
            svn url: 'http://llvm.org/svn/llvm-project/lnt/trunk', poll: false
        }
        dir('test-suite') {
            svn url: 'http://llvm.org/svn/llvm-project/test-suite/trunk'
        }
        body()
    }
}

return this
