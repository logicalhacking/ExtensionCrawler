from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='Extension Crawler',
    description='A collection of utilities for downloading and analyzing browser extension from the Chrome Web store.',
    author='Achim D. Brucker, Michael Herzberg',
    license='GPL 3.0',
    install_requires=requirements
)
