from setuptools import setup, find_packages

setup(
    name='stac-merkle-tree-cli',
    version='0.2.0',
    author='Jonathan Healy',
    author_email='jonathan.d.healy@gmail.com',
    description='A CLI tool for computing and adding Merkle Tree information to STAC catalogs, collections, or items.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/stacchain/stac-merkle-tree-cli',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click>=8.0.0',
    ],
    entry_points={
        'console_scripts': [
            'stac-merkle-tree-cli=stac_merkle_tree_cli.cli:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
