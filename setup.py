from setuptools import find_packages, setup

EXCLUDE_FROM_PACKAGES = ['tests']

setup(
    name='Splendor',
    version="0.1.0",
    python_requires='>=3.5',
    author='ForgeWorks',
    author_email='hello@forge.works',
    description='OpenAPI compatible rest framework built on Flask',
    license='MIT',
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    scripts=[],
    zip_safe=False
)