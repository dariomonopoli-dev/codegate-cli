from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="codegate-cli",
    version="0.1.7",
    description="Guardrails that prevent AI agents from installing malicious or hallucinated dependencies.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Dario Monopoli",
    author_email="jerryscout71@gmail.com",
    url="https://github.com/dariomonopoli-dev/codegate-cli",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            'codegate=codegate.cli:main',
        ],
    },
    keywords="ai security supply-chain agents pip malware mcp",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Security",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.8",
)