from setuptools import setup, find_packages

setup(
    name='django-nova',
    version='0.1.0',
    description='Simple newsletters for Django sites.',
    author='Dark Horse Comics',
    url='http://bitbucket.org/darkhorse/django-nova',
    package_dir={'nova': 'nova'},
    include_package_data=True,
    packages=find_packages(exclude=['testproject']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    zip_safe=False,
)
