from setuptools import setup

import os

# Put here required packages
packages = ['Django<=1.6',]

if 'REDISCLOUD_URL' in os.environ and 'REDISCLOUD_PORT' in os.environ and 'REDISCLOUD_PASSWORD' in os.environ:
     packages.append('django-redis-cache')
     packages.append('hiredis')

setup(name='BroquilDelGotic',
      version='1.0',
      description='El Broquil del Gotic app',
      author='Onur Ferhat',
      author_email='tiendan@gmail.com',
      url='https://onurferhat.com',
      install_requires=packages,
)

