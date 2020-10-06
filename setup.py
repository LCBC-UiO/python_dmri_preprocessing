import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="python_dmri_preprocessing-fredrmag", # Replace with your own username
    version="0.1.0",
    author="Fredrik Magnussen",
    author_email="fredrik.magnussen@psykologi.uio.no.com",
    description="Preprocessing of dMRI data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LCBC-UiO/python_dmri_preprocessing",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)