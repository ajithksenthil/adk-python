"""
Setup configuration for ADK Supabase SDK
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="adk-supabase",
    version="1.0.0",
    author="ADK Team",
    author_email="team@adk.dev",
    description="Unified Python SDK for ADK Supabase backend (FSA + MemCube)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/adk/adk-supabase",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "supabase>=2.3.0",
        "python-dateutil>=2.8.2",
        "typing-extensions>=4.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
            "isort>=5.12.0",
        ],
    },
    keywords="adk supabase fsa memcube multi-agent orchestration",
    project_urls={
        "Bug Reports": "https://github.com/adk/adk-supabase/issues",
        "Source": "https://github.com/adk/adk-supabase",
        "Documentation": "https://docs.adk.dev/supabase",
    },
)