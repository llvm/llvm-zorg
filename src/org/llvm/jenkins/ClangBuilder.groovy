package org.llvm.jenkins

class ClangBuilder implements Serializable {
    def script

    ClangBuilder(script) {
        this.script = script
    }

    def checkoutStage() {
        script.dir('llvm-project') {
            script.checkout([
                $class: 'GitSCM',
                branches: [[name: script.params.GIT_SHA]],
                extensions: [[$class: 'CloneOption', timeout: 30]],
                userRemoteConfigs: [[url: 'https://github.com/llvm/llvm-project.git']]
            ])
        }
        script.dir('llvm-zorg') {
            script.checkout([
                $class: 'GitSCM',
                branches: [[name: 'main']],
                userRemoteConfigs: [[url: 'https://github.com/llvm/llvm-zorg.git']]
            ])
        }
    }

    def setupVenvStage() {
        script.withEnv(["PATH+EXTRA=/usr/bin:/usr/local/bin"]) {
            script.sh '''
                rm -rf clang-*.tar.gz
                rm -rf venv
                python3 -m venv venv
                set +u
                source ./venv/bin/activate
                pip install -r ./llvm-zorg/zorg/jenkins/jobs/requirements.txt
                set -u
            '''
        }
    }

    def buildStage(config = [:]) {
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
        def stage1Mode = config.stage == 1
        def incremental = config.incremental
        def extraEnvVars = config.env_vars ?: [:]

        // Build environment variables map
        def envVars = [
            "PATH+EXTRA": "/usr/bin:/usr/local/bin",
            "MACOSX_DEPLOYMENT_TARGET": stage1Mode ? "13.6" : null
        ]

        // Add custom environment variables
        extraEnvVars.each { key, value ->
            envVars[key] = value
        }

        // Filter out null values
        envVars = envVars.findAll { k, v -> v != null }
        def envList = envVars.collect { k, v -> "${k}=${v}" }

        script.withEnv(envList) {
            script.timeout(timeout) {
                script.withCredentials([script.string(credentialsId: 's3_resource_bucket', variable: 'S3_BUCKET')]) {
                    def buildCmd = buildMonorepoBuildCommand(config)

                    script.sh """
                        set -u
                        ${stage1Mode ? 'rm -rf build.properties' : ''}
                        source ./venv/bin/activate
                        cd llvm-project
                        git tag -a -m "First Commit" first_commit 97724f18c79c7cc81ced24239eb5e883bf1398ef || true
                        git_desc=\$(git describe --match "first_commit")
                        export GIT_DISTANCE=\$(echo \${git_desc} | cut -f 2 -d "-")
                        sha=\$(echo \${git_desc} | cut -f 3 -d "-")
                        export GIT_SHA=\${sha:1}
                        export LLVM_REV=\$(git show -q | grep "llvm-svn:" | cut -f2 -d":" | tr -d " ")
                        cd -
                        ${stage1Mode ? 'echo "GIT_DISTANCE=\$GIT_DISTANCE" > build.properties' : ''}
                        ${stage1Mode ? 'echo "GIT_SHA=\$GIT_SHA" >> build.properties' : ''}
                        echo "ARTIFACT=\$JOB_NAME/clang-d\$GIT_DISTANCE-g\$GIT_SHA.tar.gz" >> build.properties
                        ${incremental ? 'rm -rf clang-build clang-install *.tar.gz' : ''}
                        ${buildCmd}
                    """
                }
            }
        }
    }

    def buildMonorepoBuildCommand(config) {
        def build_type = config.build_type ?: "cmake"
        def projects = config.projects ?: "clang;clang-tools-extra;compiler-rt"
        def runtimes = config.runtimes ?: ""
        def cmakeType = config.cmake_type ?: "RelWithDebInfo"
        def assertions = config.assertions ?: false
        def testTimeout = config.test_timeout ?: ""
        def buildTarget = config.build_target ?: ""
        def noinstall = config.noinstall ?: false
        def thinlto = config.thinlto ?: false
        def sanitizer = config.sanitizer ?: ""
        def extraCmakeFlags = config.cmake_flags ?: []

        def cmd = "python llvm-zorg/zorg/jenkins/monorepo_build.py ${build_type} build"

        if (cmakeType != "default") {
            cmd += " --cmake-type=${cmakeType}"
        }

        cmd += " --projects=\"${projects}\""

        if (runtimes) {
            cmd += " --runtimes=\"${runtimes}\""
        }

        if (assertions) {
            cmd += " --assertions"
        }

        if (testTimeout) {
            cmd += " --timeout=${testTimeout}"
        }

        if (buildTarget) {
            cmd += " --cmake-build-target=${buildTarget}"
        }

        if (noinstall) {
            cmd += " --noinstall"
        }

        def cmakeFlags = []
        cmakeFlags.add("-DPython3_EXECUTABLE=\$(which python)")

        if (thinlto) {
            if (build_type == "cmake") {
                cmakeFlags.add("-DLLVM_ENABLE_LTO=Thin")
            } else {
                cmd += " --thinlto"
            }
        }

        if (sanitizer) {
            cmakeFlags.add("-DLLVM_USE_SANITIZER=${sanitizer}")
        }

        if (sanitizer == "Thread") {
            cmakeFlags.add("-DDYLD_LIBRARY_PATH=\$DYLD_LIBRARY_PATH")
        }

        cmakeFlags.addAll(extraCmakeFlags)

        cmakeFlags.each { flag ->
            cmd += " --cmake-flag=\"${flag}\""
        }

        return cmd
    }

    def testStage(config = [:]) {
        def testCommand = config.test_command ?: "cmake"
        def testType = config.test_type ?: "testlong"
        def testTargets = config.test_targets ?: []
        def timeout = config.timeout ?: 420
        def extraEnvVars = config.env_vars ?: [:]

        def envVars = ["PATH": "${script.env.PATH}:/usr/bin:/usr/local/bin"]
        extraEnvVars.each { key, value ->
            envVars[key] = value
        }

        def envList = envVars.collect { k, v -> "${k}=${v}" }

        script.withEnv(envList) {
            script.timeout(timeout) {
                def cmd = "python llvm-zorg/zorg/jenkins/monorepo_build.py ${testCommand} ${testType}"

                testTargets.each { target ->
                    cmd += " --cmake-test-target=${target}"
                }

                script.sh """
                    set -u
                    source ./venv/bin/activate
                    rm -rf clang-build/testresults.xunit.xml
                    ${cmd}
                """
            }
        }
    }

    def cleanupStage(incremental) {
        if (!incremental) {
            script.sh "rm -rf clang-build clang-install"
        }
        script.sh "rm -rf host-compiler *.tar.gz"
    }
}
