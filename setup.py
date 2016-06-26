try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Important distutils stuff:
#   This file from https://docs.python.org/2/distutils/
#   https://python-packaging-user-guide.readthedocs.org/en/latest/distributing.html

setup(
    name="chromabot2",
    version="2.0",
    description= "Arbiter of the eternal battle between orangered and periwinkle",
    author="Roger Ostrander",
    author_email="atiaxi@gmail.com",
    url="http://reddit.com/r/chromabot",
    packages=['chromabot2'],
    install_requires=[
        "pyparsing >=2.1.1",
        "sqlalchemy >= 1.0.12",
    ],
)
