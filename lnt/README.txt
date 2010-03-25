LLVM "Nightly Test" Infrastructure
==================================

This directory and its subdirectories contain the LLVM nightly test
infrastructure. This is technically version "3.0" of the LLVM nightly test
architecture.

The infrastructure has the following layout:

 $ROOT/lnt - Top-level Python 'lnt' module

 $ROOT/db - Database schema, utilities, and examples of the LNT plist format.

 $ROOT/docs - Sphinx documentation for LNT.

 $ROOT/tests - Tests for the infrastructure; they currently assume they are
                  running on a system with a live instance available at
                  'http://localhost/zorg/'.

For more information, see the web documentation, or docs/.
