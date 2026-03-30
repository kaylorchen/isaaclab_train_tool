#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Setup script for Isaac Lab Train Tool"""

from setuptools import setup, find_packages

setup(
    name='isaaclab-train-tool',
    version='1.1.0',
    description='GUI tool for managing Isaac Lab training sessions',
    author='Kaylor',
    author_email='kaylor@kaylordut.com',
    url='https://github.com/isaac-sim/IsaacLab',
    license='MIT',
    python_requires='>=3.8',
    install_requires=[
        'PyQt5>=5.15.0',
    ],
    py_modules=[
        'main',
        'main_window',
        'config',
        'config_dialog',
        'models',
        'workspace_scanner',
        'tmux_manager',
        'i18n',
    ],
    entry_points={
        'console_scripts': [
            'isaaclab-train-tool=main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Robotics',
    ],
)