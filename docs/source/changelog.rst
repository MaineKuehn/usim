.. Created by log.py at 2020-06-23, command
   '/usr/local/lib/python3.7/site-packages/change/__main__.py log docs/source/changes compile --output docs/source/changelog.rst'
   based on the format of 'https://keepachangelog.com/'
#########
ChangeLog
#########

Upcoming
========

Version [Unreleased] - 2020-06-23
+++++++++++++++++++++++++++++++++

* **[Added]** Basic controlflow primitives

* **[Changed]** Pipes allow for infinite throughput
* **[Changed]** Pipe transfers support totals of zero

* **[Fixed]** Scopes no longer swallow exceptions during graceful shutdown
* **[Fixed]** Cancelling a Task early no longer cancels its parent scope

0.4 Series
==========

Version [0.4.3] - 2019-11-27
++++++++++++++++++++++++++++

* **[Added]** Resources allow comparisons to derive conditions for their levels

* **[Fixed]** Pipe.transfer reliably terminates

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

