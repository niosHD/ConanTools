import os
from setuptools import setup
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
from ConanTools import Version  # noqa


def readme():
    with open(os.path.join(script_dir, 'README.rst')) as f:
        return f.read()


pkgname = 'ConanTools'
pkgversion = Version.pep440()

# make the sphinx command available if sphinx is installed
try:
    from sphinx.setup_command import BuildDoc
    cmdclass = {'sphinx': BuildDoc}
except ImportError:
    cmdclass = {}

setup(author='Mario Werner',
      author_email='nioshd@gmail.com',
      classifiers=[  # https://pypi.org/classifiers/
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.5',
          'Topic :: Software Development :: Build Tools',
          'Topic :: Utilities',
      ],
      cmdclass=cmdclass,
      command_options={
          'sphinx': {
              'build_dir': ('setup.py', 'doc/_build'),
              'project': ('setup.py', pkgname),
              'release': ('setup.py', pkgversion),
              'source_dir': ('setup.py', 'doc'),
              'version': ('setup.py', pkgversion),
          }
      },
      description='Helpers and tools that make working with conan more convenient.',
      extras_requires=['sphinx', 'sphinx-autodoc-typehints'],
      license='MIT',
      long_description=readme(),
      name=pkgname,
      packages=[pkgname],
      python_requires='>=3.5',
      setup_requires=['pytest-runner'],
      test_requires=['pytest'],
      url='https://github.com/niosHD/ConanTools',
      version=pkgversion,
      zip_safe=False,
      )
