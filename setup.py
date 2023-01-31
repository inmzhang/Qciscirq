from setuptools import setup, find_packages

with open('README.md', encoding='UTF-8') as f:
    long_description = f.read()

setup(
    name='Qciscirq',
    version='0.1-beta',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    url='',
    license='MIT',
    author='Yiming Zhang',
    author_email='zhangyiming21@mail.ustc.edu.cn',
    description='Adaptor between QCIS and Cirq',
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='>=3.8.0',
    install_requires=['cirq>=1.0.0'],
    ext_package='pytest',
    tests_require=['pytest'],
)
