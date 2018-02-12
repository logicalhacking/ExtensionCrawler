from setuptools import setup

setup(
    name='Extension Crawler',
    description='A collection of utilities for downloading and analyzing browser extension from the Chrome Web store.',
    author='Achim D. Brucker, Michael Herzberg',
    license='GPL 3.0',
    install_requires=['GitPython', 'simhash', 'colorama', 'python_magic', 'tabulate', 'requests', 'pycrypto', 'beautifulsoup4', 'python_dateutil', 'mysqlclient', 'cchardet', 'jsbeautifier']
)
