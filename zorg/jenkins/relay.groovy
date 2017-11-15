#!/usr/bin/env groovy
@NonCPS
private def get_matching_jobs(pattern) {
    def jobs = []
    for (job in Jenkins.getInstance().getAllItems(Job)) {
        def jobname = job.getName()
        def m = jobname =~ pattern
        if (m) {
            def shortname = m[0][1]
            jobs.push([shortname, jobname])
        }
    }
    return jobs
}

private def basename(path) {
    return path.drop(path.lastIndexOf('/') + 1)
}

private def relay_steps(job_pattern, artifact_url, last_good_properties_url) {
    // The upstream jobs triggering the relay produce a
    // "last_good_build.properties" file that contains a reference to the
    // compiler artifact that should be used for this run and which llvm
    // revision it is based on.
    propfile = basename(last_good_properties_url)
    sh """
rm -f ${propfile}
curl -fksSO "${last_good_properties_url}"
"""
    def props = readProperties file: propfile
    def artifact = "http://labmaster2.local/artifacts/${props.ARTIFACT}"
    currentBuild.setDisplayName("r${props.LLVM_REV}")

    // Trigger all jobs with names matching the `job_pattern` regex.
    def joblist = get_matching_jobs(job_pattern)
    def parallel_builds = [:]
    for (j in joblist) {
        def shortname = j[0]
        def jobname = j[1]
        parallel_builds[shortname] = {
            def job_params = [
                [$class: 'StringParameterValue',
                 name: 'ARTIFACT',
                 value: artifact],
                [$class: 'StringParameterValue',
                 name: 'LLVM_REV',
                 value: props.LLVM_REV],
            ]
            build job: jobname, parameters: job_params
        }
    }
    parallel parallel_builds
}

def pipeline(job_pattern,
        artifact_url='http://labmaster2.local/artifacts/',
        last_good_properties_url='http://labmaster2.local/artifacts/clang-stage1-configure-RA/last_good_build.properties') {
    node('master') {
        stage('main') {
            relay_steps job_pattern, artifact_url, last_good_properties_url
        }
    }
}
return this
