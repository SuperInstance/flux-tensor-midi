from setuptools import setup, Extension
import numpy as np

ext_modules = [
    Extension(
        "deadband_python._deadband_c",
        sources=["deadband_python/deadband_python.c"],
        include_dirs=[np.get_include()],
        extra_compile_args=["-O3", "-std=c11"],
    ),
]

setup(
    name="deadband-python",
    version="0.1.0",
    description="Python bindings for the Deadband Framework (Eisenstein lattice, HPDF, /360 arithmetic, BMA, shell decomposition)",
    packages=["deadband_python"],
    ext_modules=ext_modules,
    install_requires=["numpy"],
)
