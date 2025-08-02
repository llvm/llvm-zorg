#!/usr/bin/env groovy

/*
 * GENERIC TEMPLATED CLANG JOB
 *
 * This is a generic job script that automatically configures itself based on the Jenkins job name.
 * It works by using symlinks - each job is just a symlink to this file with the appropriate name.
 *
 * NAMING CONVENTION:
 * - Job names follow the pattern: clang-stage[N]-[CONFIG]
 * - Template name is derived by stripping any version suffix (e.g., -v2)
 * - Each template defines its own bisection policy in getJobConfig()
 *
 * EXAMPLES:
 *   clang-stage2-Rthinlto-v2  → template: clang-stage2-Rthinlto, bisection: per template
 *   clang-stage1-RA           → template: clang-stage1-RA, bisection: per template
 *   clang-stage2-cmake-RgSan  → template: clang-stage2-cmake-RgSan, bisection: per template
 *
 * TEMPLATE RESOLUTION:
 * - Templates are loaded from zorg/jenkins/lib/templates/[JOB_TEMPLATE].groovy
 * - Template defines build configuration (stage, cmake_type, projects, etc.)
 * - Template defines job configuration (bisection policy, etc.) via getJobConfig()
 *
 * TO ADD A NEW JOB:
 * 1. Create the template file: zorg/jenkins/lib/templates/your-job-pattern.groovy
 * 2. Create symlink: ln -s templated-clang-job.groovy your-job-name
 * 3. Done! The job will automatically use the correct template and settings.
 *
 * BISECTION:
 * - Each template decides its own bisection policy in getJobConfig()
 * - ThinLTO jobs enable bisection (useful for performance regressions)
 * - Stage1 jobs disable bisection (failures often environmental)
 * - Future templates can define custom bisection logic
 */

def clangBuilder = evaluate readTrusted('zorg/jenkins/lib/builders/ClangBuilder.groovy')

// Auto-configure based on Jenkins job name
def jobName = env.JOB_NAME ?: 'unknown'

// Derive template name by stripping -v2 suffix if present
def templateName = jobName.replaceAll(/-v\d+$/, '')

// Load the template and get its job configuration
def template = evaluate readTrusted("zorg/jenkins/lib/templates/${templateName}.groovy")
def jobConfig = template.getJobConfig(jobName)

// Instantiate the templated pipeline
clangBuilder.createTemplatedPipeline(jobConfig).call()