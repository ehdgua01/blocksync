import setuptools


with open("README.rst", "r") as f:
    long_description = f.read()


setuptools.setup(
    name="blocksync",
    version="0.4.1",
    author="ehdgua01",
    author_email="ehdgua01@gmail.com",
    license="MIT License",
    description="Synchronize (large) files to a destination (local/remote) using a incremental algorithm",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/ehdgua01/blocksync",
    platforms="Any",
    packages=["blocksync"],
    keywords=["file synchronize", "incremental algorithm"],
    install_requires=["paramiko"],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
)
