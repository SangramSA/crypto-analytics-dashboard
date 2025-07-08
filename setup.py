from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="crypto-analytics-dashboard",
    version="1.0.0",
    author="Crypto Analytics Team",
    author_email="team@crypto-analytics.com",
    description="A production-ready, real-time cryptocurrency analytics platform built on AWS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/crypto-analytics-dashboard",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Database",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "bandit>=1.7.0",
            "pre-commit>=3.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "moto>=4.2.0",
            "responses>=0.23.0",
        ],
        "local": [
            "localstack>=2.0.0",
            "docker-compose>=1.29.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "crypto-producer=ingestion.producers.kinesis_producer:main",
            "crypto-health-check=scripts.health_check:main",
            "crypto-cost-monitor=scripts.cost_monitor:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 