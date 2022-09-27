# Overview

The *pre-merge checks* for the [LLVM project](http://llvm.org/) infrastructure
provides a [continuous integration
(CI)](https://en.wikipedia.org/wiki/Continuous_integration) workflow. The
workflow automatically run tests against the changes the developers upload to the
[Phabricator](https://reviews.llvm.org) and reports back results.

In theory more bugs the we can catch during the code review phase, the more stable
and bug-free the main branch will be for all contributors <sup>[citation needed]</sup>.

Check out this presentation by Louis Dione on LLVM devmtg 2021 https://youtu.be/B7gB6van7Bw

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/B7gB6van7Bw/0.jpg)](https://www.youtube.com/watch?v=B7gB6van7Bw)

The workflow checks the patches before a user merges them to the main branch -
thus the term *pre-merge testing**. When a user uploads a patch to the LLVM
Phabricator, Phabricator triggers the checks and then displays the results.

This directory contains documentation for maintainers, configuration scripts and
code that runs tests for pre-merge checks.