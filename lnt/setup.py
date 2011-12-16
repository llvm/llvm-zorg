import lnt
import os

from setuptools import setup, find_packages

# setuptools expects to be invoked from within the directory of setup.py, but it
# is nice to allow:
#   python path/to/setup.py install
# to work (for scripts, etc.)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

setup(
    name = "LNT",
    version = lnt.__version__,

    author = lnt.__author__,
    author_email = lnt.__email__,
    url = 'http://llvm.org',
    license = 'BSD',

    description = "LLVM Nightly Test Infrastructure",
    keywords = 'web testing performance development llvm',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        ('License :: OSI Approved :: '
         'University of Illinois/NCSA Open Source License'),
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Progamming Language :: Python',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        ],

    zip_safe = False,

    # Additional resource extensions we use.
    package_data = {'lnt.server.ui': ['static/*.ico',
                                      'static/*.js',
                                      'static/*.css',
                                      'templates/*.html'],

                    'lnt.util': ['NTAuxSubmit'],
                    },

    packages = find_packages(),

    test_suite = 'tests.test_all',

    entry_points = {
        'console_scripts': [
            'lnt = lnt.lnttool:main',
            ],
        },
    install_requires=['SQLAlchemy', 'Flask'],
)
