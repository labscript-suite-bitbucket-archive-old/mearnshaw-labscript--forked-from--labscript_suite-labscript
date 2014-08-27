from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
setup(
        name = "labscript",
        packages = find_packages(),
        install_requires = ['h5py', 'labscript_utils']
)

