import org.llvm.jenkins.ClangBuilder

def call(Map config = [:]) {
    def builder = new ClangBuilder(this)
    def buildConfig = config.buildConfig ?: [:]
    def testConfig = config.testConfig ?: [:]
    def triggeredJobs = config.triggeredJobs ?: []
    def stagesToRun = config.stages ?: ['checkout', 'fetch', 'build', 'test']
    def jobName = config.jobName

    pipeline {
        options {
            disableConcurrentBuilds()
        }

        parameters {
            string(name: 'LABEL', defaultValue: config.defaultLabel ?: 'macos-x86_64', description: 'Node label to run on')
            string(name: 'GIT_SHA', defaultValue: '', description: 'Git commit to build.')
            string(name: 'ARTIFACT', defaultValue: '', description: 'Clang artifact to use if this is a stage2 job')
            string(name: 'BISECT_GOOD', defaultValue: '', description: 'Good commit for bisection')
            string(name: 'BISECT_BAD', defaultValue: '', description: 'Bad commit for bisection')
            booleanParam(name: 'IS_BISECT_JOB', defaultValue: false, description: 'Whether clang is being built as part of a bisection job')
            booleanParam(name: 'SKIP_TESTS', defaultValue: false, description: 'Skip test stage. Can be useful when rebuilding a stage 1 compiler')
            booleanParam(name: 'SKIP_TRIGGER', defaultValue: false, description: 'Skip trigger of consuming CI jobs')
        }

        agent {
            node {
                label params.LABEL
            }
        }

        stages {
            stage('Validate Configuration') {
                steps {
                    script {
                        echo "Job Name: ${jobName}"
                        echo "Build Config: ${buildConfig}"
                        echo "Test Config: ${testConfig}"
                        echo "Stages to run: ${stagesToRun}"
                    }
                }
            }

            stage('Checkout') {
                when {
                    expression { 'checkout' in stagesToRun }
                }
                steps {
                    script {
                        retry(3) {
                            builder.checkoutStage()
                        }
                    }
                }
            }

            stage('Setup Venv') {
                when {
                    expression { 'checkout' in stagesToRun }
                }
                steps {
                    script {
                        builder.setupVenvStage()
                    }
                }
            }

            stage('Setup Build Description') {
                steps {
                    script {
                        def buildType = params.IS_BISECT_JOB ? "🔍 BISECTION TEST" : "🔧 NORMAL BUILD"
                        def commitInfo = env.GIT_COMMIT ? env.GIT_COMMIT.take(8) : 'unknown'

                        if (params.IS_BISECT_JOB && params.BISECT_GOOD && params.BISECT_BAD) {
                            def goodShort = params.BISECT_GOOD.take(8)
                            def badShort = params.BISECT_BAD.take(8)
                            currentBuild.description = "${buildType}: Testing ${commitInfo} (${goodShort}..${badShort})"
                        } else {
                            currentBuild.description = "${buildType}: ${commitInfo}"
                        }

                        echo "Build Type: ${buildType}"
                    }
                }
            }

            stage('Fetch Artifact') {
                when {
                    expression {
                        'fetch' in stagesToRun && (buildConfig.stage ?: 1) >= 2
                    }
                }
                steps {
                    script {
                        fetchArtifact([
                            stage1Job: buildConfig.stage1Job
                        ])
                    }
                }
            }

            stage('Build') {
                when {
                    expression { 'build' in stagesToRun }
                }
                steps {
                    script {
                        builder.buildStage(buildConfig)
                    }
                }
            }

            stage('Test') {
                when {
                    expression {
                        'test' in stagesToRun  && !params.SKIP_TESTS
                    }
                }
                steps {
                    script {
                        builder.testStage(testConfig)
                    }
                }
            }
        }

        post {
            always {
                script {
                    def Junit = new org.swift.Junit()
                    def junitPatterns = testConfig.junit_patterns ?: []

                    junitPatterns.each { pattern ->
                        Junit.safeJunit([
                            allowEmptyResults: true,
                            testResults: pattern
                        ])
                    }
                    builder.cleanupStage()
                }
            }
            success {
                script {
                    if (!params.SKIP_TRIGGER && triggeredJobs) {
                        triggeredJobs.each { job ->
                            build job: job, wait: false
                        }
                    }
                }
            }
            unstable {
                script {
                    if (!params.SKIP_TRIGGER && triggeredJobs) {
                        triggeredJobs.each { job ->
                            build job: job, wait: false
                        }
                    }
                }
            }
        }
    }
}
