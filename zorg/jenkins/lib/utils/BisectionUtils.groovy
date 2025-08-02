#!/usr/bin/env groovy

class BisectionUtils {

    // Static list to track bisection steps for reproduction
    static def bisectionSteps = []
    static def bisectionStartTime = 0
    static def stepDurations = []

    static def performBisectionWithRunner(goodCommit, badCommit, jobTemplate, buildConfig, artifact) {
        // Initialize bisection tracking
        bisectionSteps.clear()
        bisectionSteps.add("git bisect start --first-parent")
        bisectionSteps.add("git bisect bad ${badCommit}")
        bisectionSteps.add("git bisect good ${goodCommit}")

        bisectionStartTime = System.currentTimeMillis()
        stepDurations.clear()

        // Calculate and log estimated steps
        def commits = getCommitRange(goodCommit, badCommit)
        def estimatedSteps = Math.ceil(Math.log(commits.size()) / Math.log(2))
        echo "Starting bisection: ${commits.size()} commits to test, estimated ${estimatedSteps} steps"

        return performBisectionRecursive(goodCommit, badCommit, jobTemplate, buildConfig, artifact)
    }

    static def performBisectionRecursive(goodCommit, badCommit, jobTemplate, buildConfig, artifact) {
        def commits = getCommitRange(goodCommit, badCommit)

        if (commits.size() <= 2) {
            echo "Bisection complete: failing commit is ${badCommit}"
            return badCommit
        }

        def midpoint = commits[commits.size() / 2]

        // Calculate progress and ETA
        def remainingCommits = commits.size()
        def remainingSteps = Math.ceil(Math.log(remainingCommits) / Math.log(2))
        def avgStepDuration = stepDurations.size() > 0 ? stepDurations.sum() / stepDurations.size() : 0

        def etaText = "unknown"
        if (avgStepDuration > 0) {
            def etaMillis = remainingSteps * avgStepDuration
            def etaDays = Math.floor(etaMillis / 86400000)  // 24 * 60 * 60 * 1000
            def etaHours = Math.floor((etaMillis % 86400000) / 3600000)  // 60 * 60 * 1000

            if (etaDays > 0) {
                etaText = "${etaDays}d ${etaHours}h"
            } else {
                etaText = "${etaHours}h"
            }
        }

        echo "Bisecting: testing commit ${midpoint} (${remainingCommits} commits remaining, ~${remainingSteps} steps left, ETA: ${etaText})"

        // Record step start time
        def stepStartTime = System.currentTimeMillis()

        // Test the midpoint commit using the build-bisect-run job
        def testResult = testCommitWithRunner(midpoint, jobTemplate, buildConfig, artifact, goodCommit, badCommit)

        // Record step duration
        def stepDuration = System.currentTimeMillis() - stepStartTime
        stepDurations.add(stepDuration)

        // Format step duration for logging
        def stepHours = Math.floor(stepDuration / 3600000)
        def stepMinutes = Math.ceil((stepDuration % 3600000) / 60000)
        echo "Step completed in ${stepHours}h ${stepMinutes}m"

        if (testResult == 'SUCCESS') {
            // Failure is in the second half
            bisectionSteps.add("git bisect good ${midpoint}")
            return performBisectionRecursive(midpoint, badCommit, jobTemplate, buildConfig, artifact)
        } else {
            // Failure is in the first half
            bisectionSteps.add("git bisect bad ${midpoint}")
            return performBisectionRecursive(goodCommit, midpoint, jobTemplate, buildConfig, artifact)
        }
    }

    static def testCommitWithRunner(commit, jobTemplate, buildConfig, artifact, goodCommit, badCommit) {
        echo "Testing commit ${commit} using job template ${jobTemplate}"

        def result = build job: 'build-bisect-run',
                          parameters: [
                              string(name: 'GIT_SHA', value: commit),
                              string(name: 'JOB_TEMPLATE', value: jobTemplate),
                              string(name: 'BUILD_CONFIG', value: buildConfig),
                              string(name: 'ARTIFACT', value: artifact),
                              string(name: 'BISECT_GOOD', value: goodCommit),
                              string(name: 'BISECT_BAD', value: badCommit)
                          ],
                          propagate: false

        echo "Test result for ${commit}: ${result.result}"
        return result.result
    }

    static def getCommitRange(goodCommit, badCommit) {
        def commits = sh(
            script: "cd llvm-project && git rev-list --reverse ${goodCommit}..${badCommit}",
            returnStdout: true
        ).trim().split('\n')

        // Add the boundary commits
        return [goodCommit] + commits + [badCommit]
    }

    static def reportBisectionResult(failingCommit, originalJobName) {
        def commitInfo = getCommitInfo(failingCommit)

        // Add final bisect step
        bisectionSteps.add("git bisect reset")

        // Calculate final timing statistics
        def totalDuration = System.currentTimeMillis() - bisectionStartTime
        def totalDays = Math.floor(totalDuration / 86400000)
        def totalHours = Math.floor((totalDuration % 86400000) / 3600000)
        def totalMinutes = Math.ceil((totalDuration % 3600000) / 60000)

        def avgStepDuration = stepDurations.size() > 0 ? stepDurations.sum() / stepDurations.size() : 0
        def avgStepHours = Math.floor(avgStepDuration / 3600000)
        def avgStepMinutes = Math.ceil((avgStepDuration % 3600000) / 60000)

        // Format total time
        def totalTimeText = ""
        if (totalDays > 0) {
            totalTimeText = "${totalDays}d ${totalHours}h ${totalMinutes}m"
        } else if (totalHours > 0) {
            totalTimeText = "${totalHours}h ${totalMinutes}m"
        } else {
            totalTimeText = "${totalMinutes}m"
        }

        // Format average step time
        def avgStepText = "${avgStepHours}h ${avgStepMinutes}m"

        // Format reproduction steps
        def reproductionSteps = bisectionSteps.join('\n')

        def report = """
=== BISECTION COMPLETE ===
Original Job: ${originalJobName}
Failing commit: ${failingCommit}
Author: ${commitInfo.author}
Date: ${commitInfo.date}
Message: ${commitInfo.message}

Bisection Statistics:
- Total steps: ${stepDurations.size()}
- Total time: ${totalTimeText}
- Average step time: ${avgStepText}

This commit appears to be the first one that introduced the failure.

To reproduce this bisection locally:
1. Clone the repository and navigate to llvm-project/
2. Run the following git bisect commands in sequence:

${reproductionSteps}

3. At each bisect step, test the commit using your build configuration
4. Mark commits as 'git bisect good' or 'git bisect bad' based on build results
5. The bisection will converge on commit ${failingCommit}

To reproduce the specific failure:
1. Check out commit ${failingCommit}
2. Run the ${originalJobName} job configuration
3. The failure should reproduce consistently

===========================
        """.trim()

        echo report

        // Write the report to the workspace for archival
        writeFile file: 'bisection-result.txt', text: report
        archiveArtifacts artifacts: 'bisection-result.txt', allowEmptyArchive: false

        return failingCommit
    }

    static def getCommitInfo(commit) {
        def authorInfo = sh(
            script: "cd llvm-project && git show -s --format='%an|%ad|%s' ${commit}",
            returnStdout: true
        ).trim().split('\\|')

        return [
            author: authorInfo[0],
            date: authorInfo[1],
            message: authorInfo[2]
        ]
    }
}

return this