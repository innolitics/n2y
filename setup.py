"""
A setuptools based setup module.
"""

from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

description = "Notion to YAML"

setup(
    name="n2y",
    version="0.10.2",
    description=description,
    long_description=description,
    long_description_content_type="text/x-rst",
    url="https://github.com/innolitics/n2y",
    author="Innolitics, LLC",
    author_email="info@innolitics.com",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="notion documentation yaml markdown",
    packages=find_packages(exclude=["tests"]),
    install_requires=["pyyaml", "requests", "pandoc", "jinja2"],
    extras_require={
        "dev": [
            "pytest",
            "flake8",
            "check-manifest",
            "requests-cache",
        ]
    },
    include_package_data=True,
    package_data={"n2y": ["data/mermaid_err.png"]},
    entry_points={
        "console_scripts": [
            "n2y = n2y.main:cli_main",
            "n2yaudit = n2y.audit:cli_main",
        ]
    },
)
