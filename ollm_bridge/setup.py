from setuptools import setup, find_packages

setup(
    name="ollm_bridge",
    version="0.6",
    description="Ollm Bridge: Create symbolic links from Ollama models into LMStudio",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your_email@example.com",
    url="https://github.com/yourgithub/ollm_bridge",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        "console_scripts": [
            "ollm-bridge=ollm_bridge.ollm_bridge:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
