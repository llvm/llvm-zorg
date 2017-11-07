#!/usr/bin/env python
import sys
import re
from xml.sax.saxutils import escape

pipeline_git_url = sys.argv[1]
pipeline_git_path = sys.argv[2]
description = open(sys.argv[3]).read()

template = '''\
<?xml version='1.0' encoding='UTF-8'?>
<flow-definition plugin="workflow-job@2.15">
  <description>{description}</description>
  <keepDependencies>false</keepDependencies>
  <properties>
    <com.sonyericsson.jenkins.plugins.bfa.model.ScannerJobProperty plugin="build-failure-analyzer@1.19.0">
      <doNotScan>false</doNotScan>
    </com.sonyericsson.jenkins.plugins.bfa.model.ScannerJobProperty>
    <com.sonyericsson.rebuild.RebuildSettings plugin="rebuild@1.27">
      <autoRebuild>false</autoRebuild>
      <rebuildDisabled>false</rebuildDisabled>
    </com.sonyericsson.rebuild.RebuildSettings>
    {extra_properties}
  </properties>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps@2.41">
    <scm class="hudson.plugins.git.GitSCM" plugin="git@3.6.1">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>{pipeline_git_url}</url>
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches>
        <hudson.plugins.git.BranchSpec>
          <name>*/master</name>
        </hudson.plugins.git.BranchSpec>
      </branches>
      <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
      <submoduleCfg class="list"/>
      <extensions/>
    </scm>
    <scriptPath>{pipeline_git_path}</scriptPath>
    <lightweight>true</lightweight>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>
'''

# Bad hack to set throttle parameter if 'relay' is in the jobname
extra_properties = ''
if 'relay' in pipeline_git_path:
    extra_properties += '''
    <hudson.plugins.throttleconcurrents.ThrottleJobProperty plugin="throttle-concurrents@2.0.1">
      <maxConcurrentPerNode>1</maxConcurrentPerNode>
      <maxConcurrentTotal>1</maxConcurrentTotal>
      <categories class="java.util.concurrent.CopyOnWriteArrayList"/>
      <throttleEnabled>true</throttleEnabled>
      <throttleOption>project</throttleOption>
      <limitOneJobWithMatchingParams>false</limitOneJobWithMatchingParams>
      <paramsToUseForLimit></paramsToUseForLimit>
    </hudson.plugins.throttleconcurrents.ThrottleJobProperty>
'''

variables = {
    "pipeline_git_url": escape(pipeline_git_url),
    "pipeline_git_path": escape(pipeline_git_path),
    "extra_properties": extra_properties,
}
variables['description'] = escape(description.format(**variables))

sys.stdout.write(template.format(**variables))
