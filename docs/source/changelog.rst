.. Created by log.py at 2019-11-17, command
   'changey log ./docs/source/changes compile --output ./docs/source/changelog.rst'
   based on the format of 'https://keepachangelog.com/'
#########
CHANGELOG
#########

[0.4.2] - 2019-11-13
====================

Fixed
-----

* Concurrent exceptions may cascade through nested scopes

[0.4.1] - 2019-10-25
====================

Fixed
-----

* Scopes clean up all children on exit

[0.4.0] - 2019-10-24
====================

Added
-----

* Pipe resource type to simulate pipes/fluxes of limited throughput
* full SimPy compatibility layer

Changed
-------

* μSim flattened into the ``usim`` namespace

Fixed
-----

* Scopes clean up children after failures

