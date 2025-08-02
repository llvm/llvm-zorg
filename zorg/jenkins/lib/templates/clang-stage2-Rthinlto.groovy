#!/usr/bin/env groovy

// Template configuration for clang ThinLTO jobs (Release + ThinLTO)
class ClangThinLTOTemplate {

    static def getDefaultBuildConfig(userConfig = [:]) {
        def defaults = [
            thinlto: true,
            test_command: "clang",
            projects: "clang;compiler-rt",
            cmake_type: "Release"                    // R = Release
        ]

        // User config overrides defaults
        return defaults + userConfig
    }

    static def getDefaultTestConfig(userConfig = [:]) {
        def defaults = [
            test_command: "clang"
        ]

        return defaults + userConfig
    }

    static def getJobDescription() {
        return "Clang ThinLTO build configuration (Release + ThinLTO)"
    }

    // Template-specific job configuration
    static def getJobConfig(jobName) {
        return [
            name: jobName,
            job_template: 'clang-stage2-Rthinlto',
            enable_bisection_trigger: true,  // All templated ThinLTO jobs enable bisection
            bisect_job_name: 'build-bisect'
        ]
    }
}

return ClangThinLTOTemplate