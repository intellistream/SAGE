from setuptools import setup, find_packages
from setuptools.extension import Extension

if __name__ == "__main__":
    setup(
        name="candy",
        version="0.1.0",
        description="A Python package that includes compiled C++ extensions of CANDY.",
        long_description=open("README.md").read(),
        long_description_content_type="text/markdown",
        author="IntelliStream",
        author_email="your_email@example.com",
        packages=find_packages(),
        package_data={
            "candy": ["*.so"]  # Include all .so files in the candy package
        },
        classifiers=[
            "Programming Language :: Python :: 3",
            "Operating System :: OS Independent",
        ],
        python_requires=">=3.6",
        zip_safe=False,
    )
