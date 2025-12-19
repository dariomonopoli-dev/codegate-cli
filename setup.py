from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="codegate-cli",
    version="0.1.4",
    description="The Supply Chain Firewall for AI Agents. Detects hallucinated dependencies.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Dario Monopoli",
    author_email="jerryscout71@gmail.com",
    url="https://github.com/dariomonopoli-dev/codegate-cli",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "codegate=codegate.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Security",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.8",
)