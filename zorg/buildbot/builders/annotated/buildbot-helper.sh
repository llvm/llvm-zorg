#!/bin/bash

# Buildbot Helper functions

# Stop if we've encountered an error.
halt_on_failure() {
  echo "@@@HALT_ON_FAILURE@@@"
}

build_step() {
  echo  "@@@BUILD_STEP ${@}@@@"
}
