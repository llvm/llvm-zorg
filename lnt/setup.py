import lnt

from setuptools import setup, find_packages
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
        'License :: OSI Approved :: University of Illinois/NCSA Open Source License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Progamming Language :: Python',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        ],

    zip_safe = False,

    # Additional resource extensions we use.
    #
    # FIXME: Remove the .ptl entry once we move to Jinja. Note that the files
    # most likely won't get byte compiled because of how permissions will be
    # set, unless WSGI app has permissions to write to the install directory. I
    # can't find a way to force setuptools to treat these as Python modules.
    package_data = {'lnt.viewer': ['*.ptl',
                                   'zview/*.ptl',
                                   'js/*.js',
                                   'resources/*.css',
                                   'resources/*.js'],
                    'lnt.util': ['NTAuxSubmit'],
                    },

    packages = find_packages(),

    entry_points = {
        'console_scripts': [
            'lnt = lnt.lnttool:main',
            ],
        },
    install_requires=['Quixote==2.7b2', 'SQLAlchemy', 'Werkzeug'],
)
