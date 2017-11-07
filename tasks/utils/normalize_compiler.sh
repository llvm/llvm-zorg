# Get rid of the overly deep directory structures in the compiler artifacts
#
# After this script has run you should have $WORKSPACE/compiler/bin/clang etc.
cd "compiler"
# For the people with full xcode paths
if [ -d "Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr" ]; then
    if [ -d "usr" ]; then
        rm -rf usr
    fi
    mv Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/* .
    rm -rf Applications
elif [ -d */bin ]; then
# For people that have exactly 1 toplevel directory in their artifact
# */bin/clang -> bin/clang
    dir=$(dirname */bin)
    for subdir in "$dir"/*
    do
        subdir_basename=$(basename $subdir)
        if [ -d $subdir_basename ]; then
            rm -rf $subdir_basename
        fi
        mv "$dir"/$subdir_basename .
    done
fi

# Make sure there is a clang now
cd "${WORKSPACE}"
${WORKSPACE}/compiler/bin/clang -v
