package org.llvm.jenkins

class ClangBuilder implements Serializable {
    def script

    ClangBuilder(script) {
        this.script = script
    }

    def checkoutStage(zorgBranch) {
        script.sh "rm -rf '${script.env.CLANG_CRASH_DIAGNOSTICS_DIR}'"
        script.sh "rm -rf '${script.env.CLANG_CRASH_DIAGNOSTICS_DIR}.zip'"
        script.sh "mkdir -p '${script.env.CLANG_CRASH_DIAGNOSTICS_DIR}'"

        script.dir('llvm-project') {
            if (script.params.IS_BISECT_JOB) {
                // Bisection pipeline - use specific git SHA
                script.checkout([
                    $class: 'GitSCM',
                    branches: [[name: script.params.GIT_SHA]],
                    extensions: [[$class: 'CloneOption', timeout: 30]],
                    userRemoteConfigs: [[url: 'https://github.com/llvm/llvm-project.git']]
                ])
            } else {
                if (script.params.GIT_SHA) {
                    script.checkout([
                        $class: 'GitSCM',
                        branches: [[name: script.params.GIT_SHA]],
                        extensions: [[$class: 'CloneOption', timeout: 30]],
                        userRemoteConfigs: [[url: 'https://github.com/llvm/llvm-project.git']]
                    ])
                } else {
                    // Multibranch pipeline - use the SCM configuration from the job which includes timeout
                    script.checkout(script.scm)
                }
            }
        }
        script.dir('llvm-zorg') {
            script.checkout([
                $class: 'GitSCM',
                branches: [[name: zorgBranch]],
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
        def timeout = config.timeout ?: 120
        def stage1Mode = config.stage == 1
        def incremental = config.incremental
        def extraEnvVars = config.env_vars ?: [:]

        // Build environment variables map
        def envVars = [
            "PATH+EXTRA": "/usr/bin:/usr/local/bin",
            "MACOSX_DEPLOYMENT_TARGET": stage1Mode ? "13.6" : null
        ]

        def shellEnvVars = [:]
        extraEnvVars.each { key, value ->
            def strValue = value.toString()
            if (strValue.contains('$')) {
                // This needs to be expanded by the shell
                shellEnvVars[key] = strValue.replace('\\$', '$')
            } else {
                envVars[key] = value
            }
        }

        // Add custom environment variables
        extraEnvVars.each { key, value ->
            envVars[key] = value
        }

        def shellExports = []
        shellEnvVars.each { k, v ->
           shellExports.add("export ${k}=${v}")
        }
        def shellExportsStr = shellExports.join('\n')

        // Filter out null values
        envVars = envVars.findAll { k, v -> v != null }
        def envList = envVars.collect { k, v -> "${k}=${v}" }

        script.withEnv(envList) {
            script.timeout(timeout) {
                script.withCredentials([script.string(credentialsId: 's3_resource_bucket', variable: 'S3_BUCKET')]) {
                    def buildCmd = buildMonorepoBuildCommand(config)

                    script.sh """
                        set -u
                        ${shellExportsStr}
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
                        ${incremental ? '' : 'rm -rf clang-build clang-install *.tar.gz'}
                        ${buildCmd}
                    """
                }
            }
        }
    }

    def buildMonorepoBuildCommand(config) {
        def buildType = config.build_type ?: "cmake"
        def projects = config.projects ?: ""
        def runtimes = config.runtimes ?: ""
        def cmakeType = config.cmake_type ?: "RelWithDebInfo"
        def assertions = config.assertions ?: false
        def testTimeout = config.test_timeout ?: ""
        def buildTarget = config.build_target ?:  "build"
        def cmakeBuildTarget = config.cmake_build_target ?:  ""
        def noinstall = config.noinstall ?: false
        def thinlto = config.thinlto ?: false
        def sanitizer = config.sanitizer ?: ""
        def extraCmakeFlags = config.cmake_flags ?: []

        def cmd = "python llvm-zorg/zorg/jenkins/monorepo_build.py ${buildType} ${buildTarget}"

        if (cmakeType != "default") {
            cmd += " --cmake-type=${cmakeType}"
        }

        if (projects) {
            cmd += " --projects=\"${projects}\""
        }

        if (runtimes) {
            cmd += " --runtimes=\"${runtimes}\""
        }

        if (assertions) {
            cmd += " --assertions"
        }

        if (testTimeout) {
            cmd += " --timeout=${testTimeout}"
        }

        if (cmakeBuildTarget) {
            cmd += " --cmake-build-target=${cmakeBuildTarget}"
        }

        if (noinstall) {
            cmd += " --noinstall"
        }

        def cmakeFlags = []
        cmakeFlags.add("-DPython3_EXECUTABLE=\$(which python)")

        if (thinlto) {
            if (buildType == "cmake") {
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

    // Locates the llvm-lit binary within the build tree. Most 'cmake' build_type jobs
    // install straight into clang-build/, but 'clang' build_type jobs (e.g. thinlto)
    // build under a nested clang-build/Build/ directory instead.
    def findLitBinary() {
        def candidates = ['./clang-build/bin/llvm-lit', './clang-build/Build/bin/llvm-lit']
        def found = candidates.find { path -> script.fileExists(path) }
        if (!found) {
            script.error("llvm-lit not found in any of: ${candidates.join(', ')}")
        }
        script.echo "Resolved llvm-lit binary: ${found}"
        return found
    }

    // Re-anchors a workspace-relative LIT_TEST_FILTER (e.g.
    // llvm-project/compiler-rt/test/asan/TestCases/Darwin/foo.cpp) onto the build tree.
    //
    // lit never copies test sources into the build tree only generated
    // lit.site.cfg.py files land there.
    //
    // Returns one resolved path per matching config directory, since a single test
    // can have more than one valid build config (e.g. multiple target architectures).
    // Two narrowing passes keep unrelated configs out of that list: (1) a sibling
    // suite nested one level deeper (e.g. asan/Unit/<Config>/, a separate gtest-based
    // suite) is only considered if there's no config directly under the matched
    // ancestor, and (2) if the filter's tail encodes a platform (e.g.
    // TestCases/Darwin/...), configs for other platforms (e.g. an IOSConfig variant)
    // are dropped
    def resolveTestPaths(litFilter) {
        def relPath = litFilter.replaceFirst(/^[^\/]+\//, '')
        def parts = relPath.split('/') as List

        // Walk up the tree looking for lit.site.cfg.py
        for (int i = parts.size() - 1; i >= 1; i--) {
            def ancestor = parts[0..<i].join('/')
            def tail = parts[i..-1].join('/')

            // Prefer a config directly in the ancestor (clang/llvm tools); only fall
            // back to one-level-deep variant subdirectories (compiler-rt's per-arch
            // X86_64DarwinConfig/) if there's no direct config.
            def direct = script.findFiles(glob: "clang-build/**/${ancestor}/lit.site.cfg.py")
            def matches = direct.size() > 0 ? direct : script.findFiles(glob: "clang-build/**/${ancestor}/*/lit.site.cfg.py")
            if (matches.size() == 0) {
                continue
            }

            // We found the lit config(s) so construct the full file name(s)
            def configDirs = matches.collect { it.path.substring(0, it.path.lastIndexOf('/')) }.unique().sort()

            def tailParts = tail.split('/') as List

            // We see if any of the provided test path match the ones we found, for example if a user passes something
            // like llvm-project/compiler-rt/test/dir/TestCases/Darwin/test.cpp. we would match only configs which match
            // Darwin here as opposed to the other platform variants. Basically seeing if there's overlap in the strings
            // to narrow down
            def platformSegment = tailParts.find { seg ->
                def hits = configDirs.count { dir ->
                    def name = dir.substring(dir.lastIndexOf('/') + 1)
                    name.toLowerCase().contains(seg.toLowerCase())
                }
                hits > 0 && hits < configDirs.size()
            }
            if (platformSegment) {
                configDirs = configDirs.findAll { dir ->
                    def name = dir.substring(dir.lastIndexOf('/') + 1)
                    name.toLowerCase().contains(platformSegment.toLowerCase())
                }
                script.echo "Narrowed build configs by platform hint '${platformSegment}': ${configDirs.join(', ')}"
            }

            script.echo "Resolved '${litFilter}' -> ${configDirs.size()} build config(s) at '${ancestor}': ${configDirs.join(', ')}"
            return configDirs.collect { "${it}/${tail}" }
        }

        script.echo "No generated lit.site.cfg.py found in build tree for '${litFilter}'; running as-is"
        return [litFilter]
    }

    def testStage(config = [:]) {
        def testCommand = config.test_command ?: "cmake"
        def testType = config.test_type ?: "testlong"
        def testTargets = config.test_targets ?: []
        def timeout = config.timeout ?: 420
        def extraEnvVars = config.env_vars ?: [:]
        def customScript = config.custom_script ?: ""

        def envVars = ["PATH": "${script.env.PATH}:/usr/bin:/usr/local/bin"]
        extraEnvVars.each { key, value ->
            envVars[key] = value
        }

        def shellEnvVars = [:]
        extraEnvVars.each { key, value ->
            def strValue = value.toString()
            if (strValue.contains('$')) {
                // This needs to be expanded by shell
                shellEnvVars[key] = strValue.replace('\\$', '$')
            } else {
                envVars[key] = value
            }
        }

        def shellExports = []
        shellEnvVars.each { k, v ->
           shellExports.add("export ${k}=${v}")
        }
        def shellExportsStr = shellExports.join('\n')

        def envList = envVars.collect { k, v -> "${k}=${v}" }

        if (script.params.IS_BISECT_JOB && script.params.LIT_TEST_FILTER) {
            def litFilter = script.params.LIT_TEST_FILTER
            def repeatCount = (script.params.TEST_REPEAT_COUNT ?: '3').toInteger()
            def litBinary = customScript ? null : findLitBinary()
            def resolvedPaths = customScript ? null : resolveTestPaths(litFilter)
            script.echo "Bisection LIT filter mode: '${litFilter}' × ${repeatCount} run(s)"
            script.withEnv(envList) {
                script.timeout(timeout) {
                    for (int run = 1; run <= repeatCount; run++) {
                        script.echo "LIT run ${run}/${repeatCount}: ${litFilter}"
                        def runScript
                        if (customScript) {
                            runScript = """
                                set +e
                                source ./venv/bin/activate
                                export LIT_FILTER='${litFilter}'
                                ${shellExportsStr}
                                ${customScript}
                            """
                        } else {
                            def litArgs = resolvedPaths.collect { "./${it}" }.join(' ')
                            runScript = """
                                set +e
                                source ./venv/bin/activate
                                ${shellExportsStr}
                                python ${litBinary} -v ${litArgs}
                            """
                        }
                        def exitCode = script.sh(script: runScript, returnStatus: true)
                        if (exitCode != 0) {
                            script.error("LIT run ${run}/${repeatCount} FAILED for '${litFilter}' — marking commit as BAD")
                        }
                        script.echo "LIT run ${run}/${repeatCount}: PASSED"
                    }
                    script.echo "All ${repeatCount} LIT run(s) passed for '${litFilter}' — marking commit as GOOD"
                }
            }
            return
        }

        script.withEnv(envList) {
            script.timeout(timeout) {
                if (customScript) {
                    // Run custom test script
                    script.sh """
                        set -u
                        source ./venv/bin/activate
                        ${shellExportsStr}
                        ${customScript}
                    """
                } else {
                    // Run standard monorepo_build.py tests
                    def cmd = "python llvm-zorg/zorg/jenkins/monorepo_build.py ${testCommand} ${testType}"

                    testTargets.each { target ->
                        cmd += " --cmake-test-target=${target}"
                    }

                    script.sh """
                        set -u
                        source ./venv/bin/activate
                        rm -rf clang-build/testresults.xunit.xml
                        ${shellExportsStr}
                        ${cmd}
                    """
                }
            }
        }
    }

    def cleanupStage(config) {
        def incremental = config.incremental
        if (!incremental) {
            script.sh "rm -rf clang-build clang-install"
        }
        script.sh "rm -rf host-compiler *.tar.gz"
    }
}
