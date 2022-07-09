from setuptools import setup

setup(
   name='lnd-bot',
   version='1.1',
   description='LND bot to read stats from your node',
   author='Martin Biolek',
   author_email='martin@biolek.net',
   #packages=['foo'],  #same as name
   install_requires=['python-dotenv','requests'], #external packages as dependencies
   scripts=[]
)