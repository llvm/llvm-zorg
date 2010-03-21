from setuptools import setup, find_packages
setup(
    name = "LNT",
    version = "0.3",

    author = "Daniel Dunbar",
    author_email = "daniel@zuster.org",
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
    packages = find_packages(),
    entry_points = {
        'console_scripts': [
            'lnt = lnt.lnttool:main',
            ],
        },
    install_requires=['Quixote==2.7b2', 'SQLAlchemy', 'Werkzeug'],
)
