from setuptools import setup, find_packages
requires = [
    "sqlalchemy"
    ]

setup(name='sqlaqb',
      version='0.0.1',
      description='utility for portable model definition of sqlalchemy models',
      long_description="", 
      author='podhmo',
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3'
      ],
      package_dir={'': '.'},
      packages=find_packages('.'),
      install_requires = requires,
      test_suite="sqlaqb.tests", 
      entry_points = """
      """,
      )
