from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="transcribe",
    version="0.0.1",
    description="Music transcriber",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sevagh/transcribe",
    author="Sevag Hanssian",
    author_email="sevag.hanssian@gmail.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Music :: Audio",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
    ],
    keywords="mcleod pitch detection numpy numba",
    install_requires=[
        "matplotlib",
        "numpy",
        "scipy",
        "llvmlite",
        "numba",
        "cairocffi",
        "pydub",
    ],
    extras_require={"dev": ["black", "profilehooks", "xar"]},
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    entry_points={"console_scripts": ["transcribe=transcribe.__main__:main"]},
)
