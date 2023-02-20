from setuptools import setup

setup(
        name='Nik4',
        version='1.7.0',
        license='WTFPL',
        description='Command-line interface to a Mapnik rendering toolkit',
        long_description="""
Nik4
====

This is a mapnik-to-image exporting script. It requires only ``mapnik-python`` bindings.
Install it with ``pip install nik4`` or ``easy_install nik4`` and run with ``-h`` option
to see available options and their descriptions.

.. _See documentation here: https://github.com/Zverik/Nik4/blob/master/README.md
""",
        url='https://github.com/Zverik/Nik4',
        author='Ilya Zverev',
        author_email='zverik@textual.ru',
        platforms=['any'],
        requires=['Mapnik'],
        keywords='Mapnik,GIS,OpenStreetMap,mapping,export',
        scripts=['nik4.py'],
        packages=[],
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
