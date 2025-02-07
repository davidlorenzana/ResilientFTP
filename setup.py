from setuptools import setup, find_packages

setup(
    name="ResilientFTP",
    version="0.1.0",
    description="Handle FTP connections with automatic retry and reconnection logic.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="David Lorenzana Martínez",
    author_email="davlorenzana@gmail.com",
    url="https://github.com/davidlorenzana/ResilientFTP",
    packages=find_packages(),
    install_requires=[
        "tenacity",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    license="MIT",
)
