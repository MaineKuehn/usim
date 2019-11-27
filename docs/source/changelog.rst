.. Created by log.py at 2019-11-27, command
   'change log docs/source/changes compile --output docs/source/changelog.rst'
   based on the format of 'https://keepachangelog.com/'
#########
ChangeLog
#########

0.4 Series
==========

Version [0.4.3] - 2019-11-27
++++++++++++++++++++++++++++

* **[Added]** Pipe.transfer reliably terminates
* **[Added]** Resources allow comparisons to derive conditions for their levels

Version [0.4.2] - 2019-11-13
++++++++++++++++++++++++++++

* **[Fixed]** Concurrent exceptions may cascade through nested scopes

Version [0.4.1] - 2019-10-25
++++++++++++++++++++++++++++

* **[Fixed]** Scopes clean up all children on exit

Version [0.4.0] - 2019-10-24
++++++++++++++++++++++++++++

* **[Added]** Pipe resource type to simulate pipes/fluxes of limited throughput
* **[Added]** full SimPy compatibility layer

* **[Changed]** μSim flattened into the ``usim`` namespace

* **[Fixed]** Scopes clean up children after failures

