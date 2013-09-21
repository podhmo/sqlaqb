from setuptools import setup, find_packages
requires = [
    "zope.interface"
    ]

setup(name='sqlaqb',
      version='0.0.0',
      description='fmm..',
      long_description="", 
      author='podhmo',
      package_dir={'': '.'},
      packages=find_packages('.'),
      install_requires = requires,
      entry_points = """
      """,
      )
