import os
import sys
import re
import codecs

from setuptools import setup
from distutils.sysconfig import get_python_lib
from acrilib import read_meta_or_file, read_authors, read_version
from acrilib import is_overlay, find_packages

'''
is the Python package in your project. It's the top-level folder containing the
__init__.py module that should be in the same directory as your setup.py file
/-
  |- README.rst
  |- CHANGES.txt
  |- setup.py
  |- dogs
     |- __init__.py
     |- catcher.py

To create package and upload:

  python setup.py register
  python setup.py sdist
  twine upload -s dist/acrilog-1.0.2.tar.gz

'''
HERE = os.path.abspath(os.path.dirname(__file__))
PACKAGE = "acrilog"
NAME = PACKAGE
METAPATH = os.path.join(HERE, PACKAGE, "__init__.py")


'''
DESCRIPTION short description, one sentence, of your project.
'''
DESCRIPTION = '''acrilog is a Python library of providing multiprocessing idiom
to us in multiprocessing environment'''

'''
AUTHORS.txt contains a line per author. Each line contains space separated
name parts and ending with email.
e.g.,
first-name last-name nick-name email@somewhere.com
'''
AUTHOR, AUTHOR_EMAIL = read_authors('authors', metafile=METAPATH)


'''
URL is the URL for the project. This URL may be a project website, the Github
repository, or whatever URL you want. Again, this information is optional.
'''
URL = 'https://github.com/Acrisel/acrilog'
VERSION = read_version('version', metafile=METAPATH,
                       file=os.path.dirname(__file__))
existing_path = is_overlay(PACKAGE)

scripts = ['acrilog/nwlogger_socket_handler.py']

# Find all sub packages
packages = find_packages(os.path.join(HERE, PACKAGE))

setup_info = {
    'name': NAME,
    'version': VERSION,
    'url': URL,
    'author': AUTHOR,
    'author_email': AUTHOR_EMAIL,
    'description': DESCRIPTION,
    'long_description': open("README.rst", "r").read(),
    'license': 'MIT',
    'keywords': 'library logger multiprocessing',
    'packages': packages,
    'scripts': scripts,
    'install_requires': ['acrilib>=1.0.0', ],
    'extras_require': {'dev': [], 'test': []},
    'classifiers': ['Development Status :: 5 - Production/Stable',
                    'Environment :: Other Environment',
                    # 'Framework :: Project Settings and Operation',
                    'Intended Audience :: Developers',
                    'License :: OSI Approved :: MIT License',
                    'Operating System :: OS Independent',
                    'Programming Language :: Python',
                    'Programming Language :: Python :: 3',
                    'Programming Language :: Python :: 3.2',
                    'Programming Language :: Python :: 3.3',
                    'Programming Language :: Python :: 3.4',
                    'Programming Language :: Python :: 3.5',
                    'Programming Language :: Python :: 3.6',
                    'Topic :: Software Development :: Libraries :: Application'
                    'Frameworks',
                    'Topic :: Software Development :: Libraries :: Python'
                    'Modules']}
setup(**setup_info)


if existing_path:
    sys.stderr.write("""

========
WARNING!
========

You have just installed %(name)s over top of an existing
installation, without removing it first. Because of this,
your install may now include extraneous files from a
previous version that have since been removed from
Accord. This is known to cause a variety of problems. You
should manually remove the

%(existing_path)s

directory and re-install %(name)s.

""" % {"existing_path": existing_path,
       "name": NAME,})
