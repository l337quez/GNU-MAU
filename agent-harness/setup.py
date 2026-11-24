from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-gnu-mau",
    version="1.0.0",
    description="CLI-Anything harness for GNU Mau (Multipurpose Automation Utility)",
    author="CLI-Anything",
    license="MIT",
    packages=find_namespace_packages(),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "mongita>=1.2.0,<2.0.0",
        "python-dotenv",
        "prompt_toolkit>=3.0",
        "markdown2>=2.5",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-gnu-mau=cli_anything.gnu_mau.gnu_mau_cli:cli",
        ],
    },
    package_data={
        "cli_anything.gnu_mau": ["skills/*.md"],
    },
)
