from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ollm-bridge",
    version="0.6",
    author="Les-El",
    author_email="your.email@example.com",  # TODO: Update with actual email
    description="Python version of the Ollm Bridge script",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Les-El/Ollm-Bridge",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "ollm-bridge=ollm_bridge.ollm_bridge:main",
        ],
    },
)
