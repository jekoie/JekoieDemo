from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext

extensions = [
    Extension('app', ['app/app.py']),
    Extension('communicate', ['communicate/communicate.py'])
]

build_list = [
    'app/app.py',
    'communicate/communicate.py',
    'config/config.py',
    'script/script.py',
    'ui/mixin.py',
    'ui/ui.py'
]

setup(
    name="AutoTest",
    cmdclass = {'build_ext': build_ext},
    ext_modules=cythonize(build_list, compiler_directives={'language_level':3})
)

