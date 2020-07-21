import os
import sys
from setuptools import setup, find_packages

os.chdir(os.path.dirname(os.path.realpath(__file__)))

VERSION_PATH = os.path.join("mudslide", "VERSION.txt")
OS_WINDOWS = os.name == "nt"


def get_requirements():
    """
    To update the requirements for honahlee, edit the requirements.txt file.
    """
    with open("requirements.txt", "r") as f:
        req_lines = f.readlines()
    reqs = []
    for line in req_lines:
        # Avoid adding comments.
        line = line.split("#")[0].strip()
        if line:
            reqs.append(line)
    return reqs


def get_version():
    """
    When updating the Evennia package for release, remember to increment the
    version number in evennia/VERSION.txt
    """
    return open(VERSION_PATH).read().strip()


def package_data():
    """
    By default, the distribution tools ignore all non-python files.

    Make sure we get everything.
    """
    file_set = []
    for root, dirs, files in os.walk("mudslide"):
        for f in files:
            if ".git" in f.split(os.path.normpath(os.path.join(root, f))):
                # Prevent the repo from being added.
                continue
            file_name = os.path.relpath(os.path.join(root, f), "mudslide")
            file_set.append(file_name)
    return file_set


# setup the package
setup(
    name="mudslide",
    version=get_version(),
    author="Volund",
    maintainer="Volund",
    url="https://github.com/volundmush/mudslide",
    description="A library that builds on Evennia to provide popular and useful features for text-based multiplayer games (MUDs, MU*).",
    license="BSD",
    long_description="""
    honahlee is an open-source library and toolkit built atop of Evennia for
    the purpose of easing the process of building all sorts of multi-player
    online text games (MUD, MUX, MUSH, MUCK and other MU*). Plugins are provided
    that make the experience much more similar to traditional MUDs and MUSHes than
    the tools Evennia provides out of the box, from communication tools to common
    RPG design patterns such as Equipment slots and Inventory control. honahlee gets
    its name after the alchemist's furnace, as it hopes to refine the things that
    Evennia is already great into something even grander.
    """,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    # scripts=get_scripts(),
    install_requires=get_requirements(),
    package_data={"": package_data()},
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: JavaScript",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: BSD License",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 2.2",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Topic :: Database",
        "Topic :: Education",
        "Topic :: Games/Entertainment :: Multi-User Dungeons (MUD)",
        "Topic :: Games/Entertainment :: Puzzle Games",
        "Topic :: Games/Entertainment :: Role-Playing",
        "Topic :: Games/Entertainment :: Simulation",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
    ],
    python_requires=">=3.8",
    project_urls={
        "Source": "https://github.com/volundmush/mudslide",
        "For": "https://github.com/evennia/honahlee",
        "Issue tracker": "https://github.com/volundmush/mudslide/issues",
        "Patreon": "https://www.patreon.com/volund",
    },
)
