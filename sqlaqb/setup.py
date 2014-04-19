from setuptools import setup, find_packages
requires = [
    "sqlalchemy"
    ]

setup(name='sqlaqb',
      version='0.0.0',
      description='utility for portable model definition of sqlalchemy models',
      long_description="", 
      author='podhmo',
      package_dir={'': '.'},
      packages=find_packages('.'),
      install_requires = requires,
      test_suite="sqlaqb.tests", 
      entry_points = """
      """,
      )
