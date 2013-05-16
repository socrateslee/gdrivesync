#!/usr/bin/env python
import sys
import os


sdict = {
    'name': 'gdrivesync',
    'version': "0.1.0",
    'install_requires': ['httplib2'],
    'py_modules': ['gdrivesync'],
    'data_files': [('%s/bin/' % sys.prefix, ['gdrivesync'])],
    'author': 'Li Chun',
    'url': 'https://github.com/socrateslee/gdrivesync',
    'classifiers': ['Environment :: Console',
                    'Intended Audience :: Developers',
                    'Programming Language :: Python']
}

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

exec_content = '#!%s/bin/python\nimport gdrivesync\ngdrivesync.main()\n' % sys.prefix
open('gdrivesync', 'w').write(exec_content)
os.system("chmod +x gdrivesync")
setup(**sdict)
