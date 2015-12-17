from setuptools import setup, find_packages

from subm.subm import VERSION


setup(
    name='subm',
    author='demmc',
    version=VERSION,
    description='A tool downloads reddit data',
    license='MIT',
    url='https://github.com/demmc/subm',
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
    keywords='reddit',
    packages=find_packages(),
    install_requires=['arrow', 'retry', 'praw'],
    entry_points={
        'console_scripts': [
            'subm=subm:subm.main',
        ],
    },
)
