from setuptools import setup

setup(
    name="lnd-bot",
    version="2.3",
    description="LND bot to read stats from your node",
    author="Martin Biolek",
    author_email="martin@biolek.net",
    # packages=['foo'],  #same as name
    install_requires=[
        "python-dotenv",
        "requests",
        "psycopg2",
    ],  # external packages as dependencies
    scripts=[],
)
