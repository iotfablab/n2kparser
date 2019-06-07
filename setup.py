from setuptools import setup

setup(name='n2kparser',
    version=1.0,
    description='Extract values from Actisense-Serial PGNs and save them to InfluxDB',
    url='https://github.com/iotfablab/n2kparser',
    author='Shantanoo Desai',
    author_email='des@biba.uni-bremen.de',
    license='MIT',
    packages=['n2kparser'],
    scripts=['bin/n2kparser'],
    install_requires=[
        'influxdb'
    ],
    include_data_package=True,
    zip_safe=False
)