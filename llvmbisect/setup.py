import os

from setuptools import setup, find_packages

# setuptools expects to be invoked from within the directory of setup.py, but it
# is nice to allow:
#   python path/to/setup.py install
# to work (for scripts, etc.)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

setup(
    name = "llvmbisect",
    version = "1.0",

    author = "Daniel Dunbar and Chris Matthews",
    author_email = "chris.matthews@apple.com",
    url = 'http://lab.llvm.org',
    license = 'Apache-2.0 with LLVM exception',

    description = "Compiler bisection service.",
    keywords = 'testing compiler performance development llvm',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache-2.0 with LLVM exception',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Progamming Language :: Python',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        ],

    packages = find_packages(),

    scripts = ['bin/llvmlab'],

    install_requires=['requests'],
)
