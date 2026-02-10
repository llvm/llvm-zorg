private def basename(path) {
    return path.drop(path.lastIndexOf('/') + 1)
}

private def relay_steps(joblist, artifact_url, last_good_properties_url) {
    // The upstream jobs triggering the relay produce a
    // "last_good_build.properties" file that contains a reference to the
    // compiler artifact that should be used for this run and which llvm
    // revision it is based on.
    // Ensure you have the AWS CLI on path before triggering the relay
    withCredentials([string(credentialsId: 's3_resource_bucket', variable: 'S3_BUCKET')]) {
        propfile = basename(last_good_properties_url)
        sh """
          rm -f ${propfile}
          aws s3 cp $S3_BUCKET/clangci/${last_good_properties_url} ${propfile}
        """
    }

    def props = readProperties file: propfile
    def artifact = props.ARTIFACT
    currentBuild.setDisplayName("${props.GIT_DISTANCE}-${props.GIT_SHA}")

    // Trigger all jobs within the provided list
    def parallel_builds = [:]
    for (j in joblist) {
        def jobname = env.BRANCH_NAME ? "${j}/${env.BRANCH_NAME.replace('/', '%2F')}" : j
        parallel_builds[jobname] = {
            def job_params = [
                [$class: 'StringParameterValue',
                 name: 'ARTIFACT',
                 value: artifact],
                [$class: 'StringParameterValue',
                 name: 'GIT_SHA',
                 value: props.GIT_SHA],
                [$class: 'StringParameterValue',
                 name: 'GIT_DISTANCE',
                 value: props.GIT_DISTANCE],
            ]
            build job: jobname, parameters: job_params, propagate: false
        }
    }

    // Workaround to prevent LNT jobs from running in parallel and overloading the LNT server with submissions
    if(joblist.any { it.contains("lnt-ctmark") }) {
         for (j in joblist) {
            def jobname = env.BRANCH_NAME ? "${j}/${env.BRANCH_NAME.replace('/', '%2F')}" : j
            parallel_builds[jobname].call()
         }
    } else {
        parallel parallel_builds
    }
}

def pipeline(joblist,
        artifact_url='',
        last_good_properties_url='') {
    node(label: 'macos-x86_64') {
        stage('main') {
            // Download aws CLI used to gather artifacts
            sh """
              rm -rf venv
              python3 -m venv venv
              set +u
              source ./venv/bin/activate
              pip install awscli
              set -u
            """
            withEnv([
                "PATH=$PATH:$WORKSPACE/venv/bin:/usr/bin:/usr/local/bin"
            ]) {
                def branch = env.BRANCH_NAME ?: 'main'

                if (!artifact_url) {
                    artifact_url = "llvm.org/clang-stage1-RA/${branch}/latest"
                }

                if (!last_good_properties_url) {
                    last_good_properties_url = "llvm.org/clang-stage1-RA/${branch}/last_good_build.properties"
                }
                relay_steps joblist, artifact_url, last_good_properties_url
            }
        }
    }
}

return this
