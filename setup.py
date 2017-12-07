from setuptools import setup

test_requirements = [
    'pytest',
    'pytest-cov'
]

setup(
    name='compiler',
    packages=['compiler'],
    license='MIT',
    entry_points={
        'console_scripts': [
            'mmcc=compiler.compile:main'
        ]
    },
    include_package_data=True,
    install_requires=['graphviz', 'attrs'],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=test_requirements,
    extras_require={
        'test': test_requirements
    },
)
