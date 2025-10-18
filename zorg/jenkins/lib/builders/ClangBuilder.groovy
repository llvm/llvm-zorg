#!/usr/bin/env groovy

class ClangBuilder {

    static def pipeline(config) {
        def buildConfig = config.config ?: [:]
        def stagesToRun = config.stages ?: ['checkout', 'build', 'test']
        def postFailureConfig = config.post_failure ?: [:]

        pipeline {
            options {
                disableConcurrentBuilds()
            }

            parameters {
                string(name: 'LABEL', defaultValue: params.LABEL ?: 'macos-x86_64', description: 'Node label to run on')
                string(name: 'GIT_SHA', defaultValue: params.GIT_REVISION ?: '*/main', description: 'Git commit to build.')
                string(name: 'ARTIFACT', defaultValue: params.ARTIFACT ?: 'llvm.org/clang-stage1-RA/latest', description: 'Clang artifact to use')
                string(name: 'BISECT_GOOD', defaultValue: params.BISECT_GOOD ?: '', description: 'Good commit for bisection')
                string(name: 'BISECT_BAD', defaultValue: params.BISECT_BAD ?: '', description: 'Bad commit for bisection')
                booleanParam(name: 'IS_BISECT_JOB', defaultValue: params.IS_BISECT_JOB ?: false, description: 'Whether this is a bisection job')
            }

            agent {
                node {
                    label params.LABEL
                }
            }

            stages {
                stage('Checkout') {
                    when {
                        expression { 'checkout' in stagesToRun }
                    }
                    steps {
                        script {
                            ClangBuilder.checkoutStage()
                        }
                    }
                }

                stage('Setup Venv') {
                    when {
                        expression { 'checkout' in stagesToRun }
                    }
                    steps {
                        script {
                            ClangBuilder.setupVenvStage()
                        }
                    }
                }

                stage('Fetch Artifact') {
                    when {
                        expression { 'build' in stagesToRun }
                    }
                    steps {
                        script {
                            ClangBuilder.fetchArtifactStage()
                        }
                    }
                }

                stage('Build') {
                    when {
                        expression { 'build' in stagesToRun }
                    }
                    steps {
                        script {
                            ClangBuilder.buildStage(buildConfig)
                        }
                    }
                }

                stage('Test') {
                    when {
                        expression { 'test' in stagesToRun }
                    }
                    steps {
                        script {
                            ClangBuilder.testStage()
                        }
                    }
                    post {
                        always {
                            script {
                                junit "clang-build/**/testresults.xunit.xml"
                            }
                        }
                    }
                }
            }

            post {
                always {
                    script {
                        sh "rm -rf clang-build clang-install host-compiler *.tar.gz"
                    }
                }
                failure {
                    script {
                        // Only trigger bisection for main jobs, not bisection jobs themselves
                        if (!params.IS_BISECT_JOB && shouldTriggerBisection(postFailureConfig)) {
                            triggerBisection(config.name, postFailureConfig)
                        }
                    }
                }
            }
        }
    }

    static def checkoutStage() {
        dir('llvm-project') {
            checkout([$class: 'GitSCM', branches: [
                [name: params.GIT_SHA]
            ], extensions: [
                [$class: 'CloneOption', timeout: 30]
            ], userRemoteConfigs: [
                [url: 'https://github.com/llvm/llvm-project.git']
            ]])
        }
        dir('llvm-zorg') {
            checkout([$class: 'GitSCM', branches: [
                [name: '*/main']
            ], extensions: [
                [$class: 'CloneOption', reference: '/Users/Shared/llvm-zorg.git']
            ], userRemoteConfigs: [
                [url: 'https://github.com/llvm/llvm-zorg.git']
            ]])
        }
    }

    static def setupVenvStage() {
        withEnv(["PATH=$PATH:/usr/bin:/usr/local/bin"]) {
            sh '''
                # Non-incremental, so always delete.
                rm -rf clang-build clang-install host-compiler *.tar.gz
                rm -rf venv
                python3 -m venv venv
                set +u
                source ./venv/bin/activate
                pip install -r ./llvm-zorg/zorg/jenkins/jobs/requirements.txt
                set -u
            '''
        }
    }

    static def fetchArtifactStage() {
        withEnv(["PATH=$PATH:/usr/bin:/usr/local/bin"]) {
            withCredentials([string(credentialsId: 's3_resource_bucket', variable: 'S3_BUCKET')]) {
                sh """
                    source ./venv/bin/activate
                    echo "ARTIFACT=${params.ARTIFACT}"
                    python llvm-zorg/zorg/jenkins/monorepo_build.py fetch
                    ls $WORKSPACE/host-compiler/lib/clang/
                    VERSION=`ls $WORKSPACE/host-compiler/lib/clang/`
                """
            }
        }
    }

    static def buildStage(config = [:]) {
        def thinlto = config.thinlto ?: false
        def cmakeType = config.cmake_type ?: "RelWithDebInfo"
        def projects = config.projects ?: "clang;clang-tools-extra;compiler-rt"
        def runtimes = config.runtimes ?: ""
        def sanitizer = config.sanitizer ?: ""
        def assertions = config.assertions ?: false
        def timeout = config.timeout ?: 120
        def buildTarget = config.build_target ?: ""
        def noinstall = config.noinstall ?: false
        def extraCmakeFlags = config.cmake_flags ?: []
        def stage1Mode = config.stage1 ?: false
        def extraEnvVars = config.env_vars ?: [:]
        def testCommand = config.test_command ?: "cmake"
        def testTargets = config.test_targets ?: []

        // Build environment variables map
        def envVars = [
            "PATH": "\$PATH:/usr/bin:/usr/local/bin",
            "MACOSX_DEPLOYMENT_TARGET": stage1Mode ? "13.6" : null
        ]

        // Add custom environment variables
        extraEnvVars.each { key, value ->
            envVars[key] = value
        }

        // Filter out null values
        envVars = envVars.findAll { k, v -> v != null }

        def envList = envVars.collect { k, v -> "${k}=${v}" }

        withEnv(envList) {
            timeout(timeout) {
                withCredentials([string(credentialsId: 's3_resource_bucket', variable: 'S3_BUCKET')]) {
                    // Build the command dynamically
                    def buildCmd = buildMonorepoBuildCommand(config)

                    sh """
                        set -u
                        ${stage1Mode ? 'rm -rf build.properties' : ''}
                        source ./venv/bin/activate

                        cd llvm-project
                        git tag -a -m "First Commit" first_commit 97724f18c79c7cc81ced24239eb5e883bf1398ef || true

                        git_desc=\$(git describe --match "first_commit")
                        export GIT_DISTANCE=\$(echo \${git_desc} | cut -f 2 -d "-")

                        sha=\$(echo \${git_desc} | cut -f 3 -d "-")
                        export GIT_SHA=\${sha:1}

                        ${stage1Mode ? 'export LLVM_REV=$(git show -q | grep "llvm-svn:" | cut -f2 -d":" | tr -d " ")' : ''}

                        cd -

                        ${stage1Mode ? 'echo "GIT_DISTANCE=\$GIT_DISTANCE" > build.properties' : ''}
                        ${stage1Mode ? 'echo "GIT_SHA=\$GIT_SHA" >> build.properties' : ''}
                        ${stage1Mode ? 'echo "ARTIFACT=\$JOB_NAME/clang-d\$GIT_DISTANCE-g\$GIT_SHA-t\$BUILD_ID-b\$BUILD_NUMBER.tar.gz" >> build.properties' : ''}

                        ${stage1Mode ? 'rm -rf clang-build clang-install *.tar.gz' : ''}
                        ${buildCmd}
                    """
                }
            }
        }
    }

    static def buildMonorepoBuildCommand(config) {
        def testCommand = config.test_command ?: "cmake"
        def projects = config.projects ?: "clang;clang-tools-extra;compiler-rt"
        def runtimes = config.runtimes ?: ""
        def cmakeType = config.cmake_type ?: "RelWithDebInfo"
        def assertions = config.assertions ?: false
        def timeout = config.timeout ?: 120
        def buildTarget = config.build_target ?: ""
        def noinstall = config.noinstall ?: false
        def thinlto = config.thinlto ?: false
        def sanitizer = config.sanitizer ?: ""
        def extraCmakeFlags = config.cmake_flags ?: []

        // Start building command
        def cmd = "python llvm-zorg/zorg/jenkins/monorepo_build.py ${testCommand} build"

        // Add cmake type if not default
        if (cmakeType != "default") {
            cmd += " --cmake-type=${cmakeType}"
        }

        // Add projects
        cmd += " --projects=\"${projects}\""

        // Add runtimes if specified
        if (runtimes) {
            cmd += " --runtimes=\"${runtimes}\""
        }

        // Add assertions flag
        if (assertions) {
            cmd += " --assertions"
        }

        // Add timeout if different from default
        if (timeout != 2400) {
            cmd += " --timeout=${timeout}"
        }

        // Add build target if specified
        if (buildTarget) {
            cmd += " --cmake-build-target=${buildTarget}"
        }

        // Add noinstall flag
        if (noinstall) {
            cmd += " --noinstall"
        }

        // Build cmake flags
        def cmakeFlags = []
        cmakeFlags.add("-DPython3_EXECUTABLE=\$(which python)")

        if (thinlto) {
            cmakeFlags.add("-DLLVM_ENABLE_LTO=Thin")
        }

        if (sanitizer) {
            cmakeFlags.add("-DLLVM_USE_SANITIZER=${sanitizer}")
        }

        // Add DYLD_LIBRARY_PATH for TSan
        if (sanitizer == "Thread") {
            cmakeFlags.add("-DDYLD_LIBRARY_PATH=\$DYLD_LIBRARY_PATH")
        }

        // Add extra cmake flags from config
        cmakeFlags.addAll(extraCmakeFlags)

        // Add all cmake flags to command
        cmakeFlags.each { flag ->
            cmd += " --cmake-flag=\"${flag}\""
        }

        return cmd
    }

    static def testStage(config = [:]) {
        def testCommand = config.test_command ?: "cmake"
        def testType = config.test_type ?: "testlong"  // testlong vs test
        def testTargets = config.test_targets ?: []
        def timeout = config.test_timeout ?: 420
        def extraEnvVars = config.env_vars ?: [:]

        // Build environment variables map
        def envVars = [
            "PATH": "\$PATH:/usr/bin:/usr/local/bin"
        ]

        // Add custom environment variables (like ASAN_SYMBOLIZER_PATH)
        extraEnvVars.each { key, value ->
            envVars[key] = value
        }

        def envList = envVars.collect { k, v -> "${k}=${v}" }

        withEnv(envList) {
            timeout(timeout) {
                // Build test command dynamically
                def cmd = "python llvm-zorg/zorg/jenkins/monorepo_build.py ${testCommand} ${testType}"

                // Add specific test targets if provided
                testTargets.each { target ->
                    cmd += " --cmake-test-target=${target}"
                }

                sh """
                    set -u
                    source ./venv/bin/activate

                    rm -rf clang-build/testresults.xunit.xml

                    ${cmd}
                """
            }
            }
        }
    }

    static def cleanupStage() {
        sh "rm -rf clang-build clang-install host-compiler *.tar.gz"
    }

    static def createTemplatedPipeline(config) {
        def jobName = config.name
        def jobTemplate = config.job_template ?: 'clang-stage2-Rthinlto'
        def enableBisectionTrigger = config.enable_bisection_trigger ?: false
        def bisectJobName = config.bisect_job_name ?: 'build-bisect'
        def descriptionPrefix = config.description_prefix ?: ""

        def clangBuilder = evaluate readTrusted('zorg/jenkins/lib/builders/ClangBuilder.groovy')

        return {
            pipeline {
                options {
                    disableConcurrentBuilds()
                }

                parameters {
                    string(name: 'LABEL', defaultValue: params.LABEL ?: 'macos-x86_64', description: 'Node label to run on')
                    string(name: 'GIT_SHA', defaultValue: params.GIT_REVISION ?: '*/main', description: 'Git commit to build.')
                    string(name: 'ARTIFACT', defaultValue: params.ARTIFACT ?: 'llvm.org/clang-stage1-RA/latest', description: 'Clang artifact to use')
                    booleanParam(name: 'IS_BISECT_JOB', defaultValue: params.IS_BISECT_JOB ?: false, description: 'Whether this is a bisection job')
                    string(name: 'BISECT_GOOD', defaultValue: params.BISECT_GOOD ?: '', description: 'Good commit for bisection')
                    string(name: 'BISECT_BAD', defaultValue: params.BISECT_BAD ?: '', description: 'Bad commit for bisection')
                }

                agent {
                    node {
                        label params.LABEL
                    }
                }

                stages {
                    stage('Setup Build Description') {
                        steps {
                            script {
                                // Set build description based on context
                                def buildType = params.IS_BISECT_JOB ? "🔍 BISECTION TEST" : "🔧 NORMAL BUILD"
                                def commitInfo = params.GIT_SHA.take(8)

                                if (params.IS_BISECT_JOB && params.BISECT_GOOD && params.BISECT_BAD) {
                                    def goodShort = params.BISECT_GOOD.take(8)
                                    def badShort = params.BISECT_BAD.take(8)
                                    currentBuild.description = "${buildType}: Testing ${commitInfo} (${goodShort}..${badShort})"
                                } else {
                                    currentBuild.description = "${buildType}: ${commitInfo}"
                                }

                                if (descriptionPrefix) {
                                    currentBuild.description = "${descriptionPrefix}: ${currentBuild.description}"
                                }

                                echo "Build Type: ${buildType}"
                                echo "Job Template: ${jobTemplate}"
                                if (params.IS_BISECT_JOB) {
                                    echo "This is a bisection test run - results will be used by build-bisect job"
                                } else {
                                    echo "This is a normal CI build"
                                }
                            }
                        }
                    }
                    stage('Checkout') {
                        steps {
                            script {
                                clangBuilder.checkoutStage()
                            }
                        }
                    }

                    stage('Setup Venv') {
                        steps {
                            script {
                                clangBuilder.setupVenvStage()
                            }
                        }
                    }

                    stage('Fetch Artifact') {
                        when {
                            expression {
                                // Load template to check if this is a stage2+ build
                                def template = evaluate readTrusted("zorg/jenkins/lib/templates/${jobTemplate}.groovy")
                                def buildConfig = template.getDefaultBuildConfig()
                                def stage = buildConfig.stage ?: 2  // Default to stage2 if not specified
                                return stage >= 2
                            }
                        }
                        steps {
                            script {
                                clangBuilder.fetchArtifactStage()
                            }
                        }
                    }

                    stage('Build') {
                        steps {
                            script {
                                // Load the shared template
                                def template = evaluate readTrusted("zorg/jenkins/lib/templates/${jobTemplate}.groovy")
                                def buildConfig = template.getDefaultBuildConfig()

                                clangBuilder.buildStage(buildConfig)
                            }
                        }
                    }

                    stage('Test') {
                        steps {
                            script {
                                // Load the shared template
                                def template = evaluate readTrusted("zorg/jenkins/lib/templates/${jobTemplate}.groovy")
                                def testConfig = template.getDefaultTestConfig()

                                clangBuilder.testStage(testConfig)
                            }
                        }
                        post {
                            always {
                                script {
                                    junit "clang-build/**/testresults.xunit.xml"
                                }
                            }
                        }
                    }
                }

                post {
                    always {
                        script {
                            clangBuilder.cleanupStage()
                        }
                    }
                    failure {
                        script {
                            // Only trigger bisection if enabled and this is not already a bisection job
                            if (enableBisectionTrigger && !params.IS_BISECT_JOB && shouldTriggerBisection()) {
                                triggerBisection(jobName, bisectJobName, jobTemplate)
                            }
                        }
                    }
                }
            }
        }
    }

    static def shouldTriggerBisection() {
        // Check if this is a new failure by looking at previous build result
        def previousBuild = currentBuild.previousBuild
        if (previousBuild == null) {
            return false  // First build, can't bisect
        }

        // Only bisect if previous build was successful (new failure)
        return previousBuild.result == 'SUCCESS'
    }

    static def triggerBisection(currentJobName, bisectJobName, jobTemplate) {
        // Get the commit range for bisection
        def currentCommit = env.GIT_COMMIT
        def goodCommit = getPreviousGoodCommit()

        if (goodCommit) {
            echo "Triggering bisection: ${goodCommit}...${currentCommit}"

            // Launch the bisection orchestrator with template configuration
            build job: bisectJobName,
                  parameters: [
                      string(name: 'BISECT_GOOD', value: goodCommit),
                      string(name: 'BISECT_BAD', value: currentCommit),
                      string(name: 'JOB_TEMPLATE', value: jobTemplate),
                      string(name: 'BUILD_CONFIG', value: '{}'),  // Use template defaults
                      string(name: 'ARTIFACT', value: params.ARTIFACT)
                  ],
                  wait: false
        } else {
            echo "Could not determine good commit for bisection"
        }
    }

    static def getPreviousGoodCommit() {
        // Walk back through builds to find the last successful one
        def build = currentBuild.previousBuild
        while (build != null) {
            if (build.result == 'SUCCESS') {
                // Extract commit from the successful build
                def buildEnv = build.getBuildVariables()
                return buildEnv.GIT_COMMIT
            }
            build = build.previousBuild
        }
        return null
    }
}

return this