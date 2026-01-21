def call(Map config = [:]) {
    def pythonScript = libraryResource('scripts/artifact_manager.py')
    writeFile file: 'artifact_manager.py', text: pythonScript
    sh 'chmod +x artifact_manager.py'

    withEnv(["PATH+EXTRA=/usr/bin:/usr/local/bin"]) {
        withCredentials([string(credentialsId: 's3_resource_bucket', variable: 'S3_BUCKET')]) {
            def stage1JobName = params.IS_BISECT_JOB ? "Green-Dragon-Testing/bisect/${config.stage1Job}" : "Green-Dragon-Testing/${config.stage1Job}"
            def jobName = env.BRANCH_NAME ? "${stage1JobName}/${env.BRANCH_NAME}" : stage1JobName

            // Determine if we should use a specific artifact parameter
            def artifactParam = params.ARTIFACT

            // Call Python script to handle artifact logic
            def pythonCmd = """
                source ./venv/bin/activate
                python ./artifact_manager.py \\
                    --workspace "\$WORKSPACE" \\
                    --output-file artifact_result.properties"""

            if (artifactParam) {
                pythonCmd += " --artifact \"${artifactParam}\""
            } else {
                pythonCmd += " --job-name \"${jobName}\""
            }

            def scriptResult = sh(
                script: pythonCmd,
                returnStatus: true
            )

            // Read results from Python script
            def resultProps = readProperties file: 'artifact_result.properties'
            def artifactFound = resultProps.ARTIFACT_FOUND == 'true'
            def usedArtifact = resultProps.USED_ARTIFACT
            def needsStage1 = resultProps.NEEDS_STAGE1 == 'true'

            if (needsStage1) {
                echo "Triggering stage 1 build for artifact: ${usedArtifact}"

                // Trigger stage 1 job and wait for completion
                def stage1Build = build(
                    job: jobName,
                    parameters: [
                        string(name: 'GIT_SHA', value: params.GIT_SHA),
                        string(name: 'BISECT_GOOD', value: params.BISECT_GOOD),
                        string(name: 'BISECT_BAD', value: params.BISECT_BAD),
                        booleanParam(name: 'IS_BISECT_JOB', value: true),
                        booleanParam(name: 'SKIP_TESTS', value: true),
                        booleanParam(name: 'SKIP_TRIGGER', value: true)
                    ],
                    wait: true,
                    propagate: true
                )

                echo "Stage 1 build completed successfully. Build number: ${stage1Build.number}"

                // Retry fetching the artifact after stage 1 completes
                def retryCmd = """
                    source ./venv/bin/activate
                    export ARTIFACT="${usedArtifact}"
                    echo "ARTIFACT=\$ARTIFACT"
                    python llvm-zorg/zorg/jenkins/monorepo_build.py fetch
                    ls \$WORKSPACE/host-compiler/lib/clang/
                    VERSION=`ls \$WORKSPACE/host-compiler/lib/clang/`
                """

                sh retryCmd
            }

            // Return useful information
            return [
                artifactFound: artifactFound,
                usedArtifact: usedArtifact,
                needsStage1: needsStage1,
                stage1Triggered: needsStage1
            ]
        }
    }
}
