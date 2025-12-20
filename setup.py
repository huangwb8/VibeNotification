from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="vibe-notification",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="智能 AI 助手会话结束通知系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/VibeNotification",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "vibe-notification=vibe_notification.cli:main",
            "vibe-notify=vibe_notification.cli:main",  # 别名
        ],
    },
    include_package_data=True,
    keywords="claude codex notification ai assistant",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/VibeNotification/issues",
        "Source": "https://github.com/yourusername/VibeNotification",
        "Documentation": "https://github.com/yourusername/VibeNotification/docs",
    },
)