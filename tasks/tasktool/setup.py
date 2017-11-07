from setuptools import setup, find_packages

setup(
    name='tasktool',
    version='1.0',
    author='Matthias Braun',
    author_email='matze@braunis.de',
    license='BSD',
    description='CI Task Runner',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Unix Shell',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Quality Assurance'
        'Topic :: Software Development :: Testing',
    ],
    package_data={
        'tasktool': ['hooks/*'],
    },
    packages=find_packages(),
    entry_points={
        'console_scripts': ['task=tasktool.task:main'],
    },
)
