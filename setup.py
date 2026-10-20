from setuptools import setup
setup(name='virtual_iridium',
      version='1.0',
      package_dir={'virtual_iridium': 'python'},
      packages=['virtual_iridium'],
      install_requires=['pyserial', 'pyasyncore; python_version >= "3.12"'],
      scripts=['python/Iridium9602.py', 'python/iridium_mo_forward_server.py', 'python/iridium_mt_forward_server.py', 'python/iridium_rudics_shore_connection.py']
      )
