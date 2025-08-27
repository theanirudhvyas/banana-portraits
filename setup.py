from setuptools import setup, find_packages

setup(
    name="nano-banana-portrait",
    version="0.1.0",
    description="AI Face Identity Image Composer with Fine-Tuning",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "fal-client>=0.4.0",
        "pillow>=10.0.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "nano-banana=src.cli:main",
        ],
    },
    python_requires=">=3.8",
)