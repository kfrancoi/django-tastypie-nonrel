#!/usr/bin/env python
# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='django-tastypie-nonrel',
    version='0.0.1.1',
    description='Nonrelational extensions for Django Tastypie.',
    author='Andres Douglas & Kevin Françoisse',
    author_email='andres.douglas@gmail.com',
    url='https://github.com/andresdouglas/django-tastypie-nonrel',
    packages=[
        'tastypie_nonrel',
    ],
    requires=[
        'tastypie',
    ],
)
