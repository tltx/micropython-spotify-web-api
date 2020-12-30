from setuptools import setup
import sdist_upip

setup(
    name='micropython-spotify-web-api',
    packages=['spotify_web_api'],
    version='0.0.1',
    description='Spotify Web API client for MicroPython',
    long_description='Spotify Web API client for MicroPython',
    url='https://github.com/tltx/micropython-spotify-web-api',
    author='Tore Lundqvist',
    author_email='tlt@mima.x.se',
    license='MIT',
    cmdclass={'sdist': sdist_upip.sdist},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: Implementation :: MicroPython",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
    ],
)
