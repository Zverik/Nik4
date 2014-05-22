from distutils.core import setup

setup(
		name='Nik4',
		version='1.3.0',
		license='WTFPL',
		description='Command-line interface to a Mapnik rendering toolkit',
		long_description=open('README.txt').read(),
		url='https://github.com/Zverik/Nik4',
		author='Ilya Zverev',
		author_email='zverik@textual.ru',
		platforms=['any'],
		requires=['Mapnik'],
		keywords='Mapnik,GIS,OpenStreetMap,mapping,export',
		scripts=['nik4.py'],
		classifiers=[
			'Development Status :: 5 - Production/Stable',
			'Environment :: Console',
			'Environment :: Web Environment',
			'Intended Audience :: End Users/Desktop',
			'Intended Audience :: Science/Research',
			'Operating System :: OS Independent',
			'Programming Language :: Python',
			'Topic :: Scientific/Engineering :: GIS',
			'Topic :: Printing',
			'Topic :: Utilities'
		]
)
