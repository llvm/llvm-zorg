def call(Map params) {
    def pythonScript = libraryResource('scripts/bisect.py')
    writeFile file: 'bisect.py', text: pythonScript
    sh 'chmod +x bisect.py'

    try {
        def command = params.command
        def args = params.args ?: []
        def repoPath = params.repoPath ?: '.'
        def workspace = params.workspace ?: '.'

        def cmdLine = "python3 bisect.py ${command}"

        if (repoPath != '.') {
            cmdLine += " --repo-path '${repoPath}'"
        }
        if (workspace != '.') {
            cmdLine += " --workspace '${workspace}'"
        }

        if (args) {
            cmdLine += " ${args.join(' ')}"
        }

        // Execute command - stderr goes to Jenkins console automatically,
        // stdout contains JSON (if any)
        def result = sh(script: cmdLine, returnStdout: true).trim()

        // Check if we got JSON output
        if (result && (result.startsWith('{') || result.startsWith('['))) {
            try {
                return readJSON(text: result)
            } catch (Exception e) {
                echo "Warning: Failed to parse JSON output: ${e.message}"
                echo "Raw output was: ${result}"
                return [output: result]
            }
        } else {
            return [success: true]
        }
    } finally {
        try {
            sh 'rm -f bisect.py'
        } catch (Exception e) {
            echo "Warning: Could not clean up bisect.py: ${e}"
        }
    }
}

def initializeBisection(String goodCommit, String badCommit, String testJob,
                       String repoPath = '.', String sessionId = null) {
    def args = [goodCommit, badCommit, '--test-job', testJob]
    if (sessionId) {
        args.addAll(['--session-id', sessionId])
    }

    return bisectionManager([
        command: 'init',
        args: args,
        repoPath: repoPath
    ])
}

def logStepStart(int stepNumber, String repoPath = '.') {
    return bisectionManager([
        command: 'log-step',
        args: [stepNumber.toString()],
        repoPath: repoPath
    ])
}

def showRestartInstructions(int stepNumber, String testJob, String repoPath = '.') {
    return bisectionManager([
        command: 'show-restart',
        args: [stepNumber.toString(), testJob, '--platform', 'jenkins'],
        repoPath: repoPath
    ])
}

def logJobExecution(String jobName, String result, double duration,
                   String jobUrl = null, String buildNumber = null, String repoPath = '.') {
    def args = [jobName, result, duration.toString()]
    if (jobUrl) {
        args.addAll(['--job-url', jobUrl])
    }
    if (buildNumber) {
        args.addAll(['--build-number', buildNumber])
    }

    bisectionManager([
        command: 'log-job',
        args: args,
        repoPath: repoPath
    ])
}

def recordTestResult(String commit, String result, String repoPath = '.') {
    return bisectionManager([
        command: 'record',
        args: [commit, result],
        repoPath: repoPath
    ])
}

def generateFinalReport(String repoPath = '.') {
    return bisectionManager([
        command: 'final-report',
        repoPath: repoPath
    ])
}

def displaySummary(String repoPath = '.') {
    bisectionManager([
        command: 'summary',
        repoPath: repoPath
    ])
}
