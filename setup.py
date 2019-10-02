import setuptools
import pylogix

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pylogix",
    version=pylogix.__version__,
    author="Dustin Roeder",
    author_email="dmroeder@gmail.com",
    description="Read/Write Rockwell Automation Logix based PLC's",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="Apache License 2.0",
    url="https://github.com/dmroeder/pylogix",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
