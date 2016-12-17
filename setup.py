import re
from setuptools import setup, find_packages

with open('subm/subm.py', encoding='utf-8') as f:
    version_line = [line for line in f if 'VERSION = ' in line][0]
    VERSION = re.search(r'[0-9.a-z]+', version_line).group(0).strip("' ")

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
    install_requires=['arrow', 'retry', 'praw<4'],
    entry_points={
        'console_scripts': [
            'subm=subm:subm.main',
        ],
    },
)
