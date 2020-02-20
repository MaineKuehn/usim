Resource Modelling
==================

Resource Containers
-------------------

Resources support the comparison operations, such as ``==``, ``>=``, or ``<``.
This derives a :py:class:`~usim.Comparison` that triggers when the Resources'
levels reaches the desired value.

.. autoclass:: usim.Resources
    :members:

.. autoclass:: usim.Capacities
    :members:

.. autoclass:: usim.typing.ResourceLevels
    :members:

.. autoexception:: usim.ResourcesUnavailable
    :members:

Resource Transfer
-----------------

.. autoclass:: usim.Pipe
    :members:

.. autoclass:: usim.UnboundedPipe
    :members:
