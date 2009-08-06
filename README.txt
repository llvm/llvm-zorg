Zorg - LLVM Testing Infrastructure
==================================

This directory and its subdirectories contain Zorg, a testing infrastructure for
LLVM.

LLVM is open source software. You may freely distribute it under the terms of
the license agreement found in LICENSE.txt.

Zorg consists of several pieces:
 1. A general database utilities for storing test results, with
    accompanying utilities.

 2. A web app for submitting and querying test results.

 3. A 'nightlytest' infrastructure built on top of 1 & 2.

 4. Buildbot configurations for LLVM.

 5. Other testing utility scripts.

Zorg is primarily implemented in Python, and has the following layout:
 $ROOT/buildbot/ - Buildbot configurations.
 $ROOT/zorg/ - The root zorg Python module.
 $ROOT/zorg/buildbot/ - Reusable components for buildbot configurations.
