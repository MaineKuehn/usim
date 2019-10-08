``usim.py.resources`` -- Synchronized Resources
===============================================

.. py:module:: usim.py.resources
    :synopsis: Synchronized Resources

.. toctree::
   :hidden:

μSim replicates all resource types provided by SimPy.
Resources synchronize processes by sharing or exchanging objects, data, or ownership.

====================================== ==========================================================================
:py:mod:`~usim.py.resources.resource`  Resources with a fixed ``capacity`` of usage slots
:py:mod:`~usim.py.resources.container` Resources with ``capacity`` of continuous, indistinguishable content
:py:mod:`~usim.py.resources.store`     Resources with a fixed ``capacity`` of slots for storing arbitrary objects
:py:mod:`~usim.py.resources.base`      Common interface inherited by all resource types
====================================== ==========================================================================

Just like the :py:mod:`usim.py`, :py:mod:`usim.py.resources` is a drop-in replacement
for :py:mod:`simpy.resources`.
It is possible to use :py:mod:`usim.py` resources both in :py:mod:`usim.py` processes
as well as regular :py:mod:`usim` activities.

.. content-tabs::

    .. tab-container:: usim
        :title: μSim

        .. code:: python3

            async def block(resource: Resource):
                with resource.get() as request:
                    await request
                    await (time + 5)

    .. tab-container:: simpy
        :title: SimPy

        .. code:: python3

            def block(env, resource: Resource):
                with resource.get() as request:
                    yield request
                    yield env.timeout(5)

.. note::

    μSim only replicates the *public, documented* API of SimPy's resources.
    This includes private methods intended to be overridden, such as
    :py:meth:`~usim.py.resources.base.BaseResource._do_put`.
    Implementation details, especially of internal methods such as
    :py:meth:`~usim.py.resources.base.BaseResource._trigger_put`,
    may differ from SimPy.

Common Resource Interface
-------------------------

All resources of :py:mod:`usim.py` derive from a common interface:
the :py:class:`~.BaseResource` with a given capacity,
and related events to
:py:class:`~usim.py.resources.base.BaseResource.put` and
:py:class:`~usim.py.resources.base.BaseResource.get`
resource in or out of the resource.

.. py:module:: usim.py.resources.base
    :synopsis: Common Resource Interface

.. autoclass:: usim.py.resources.base.BaseResource
    :members:

    .. automethod:: _do_put
    .. automethod:: _do_get

Each request to
:py:class:`~usim.py.resources.base.BaseResource.put` or
:py:class:`~usim.py.resources.base.BaseResource.get`
resources is represented by an
:py:class:`~usim.py.events.Event`.
It is possible, but not necessary, for a process/activity to ``yield``/``await``
such a request to wait for its success.

.. autoclass:: usim.py.resources.base.BaseRequest
    :members:

.. autoclass:: usim.py.resources.base.Put
    :members:

.. autoclass:: usim.py.resources.base.Get
    :members:

Resources -- Shared Resource Usage
----------------------------------

The ``Resource`` types implement various forms of semaphores:
a pool of usage slots which can be requested, acquired and released.
Variants of the basic :py:class:`~usim.py.resources.resource.Resource`
support request priorities (:py:class:`~usim.py.resources.resource.PriorityResource`)
and preemption (:py:class:`~usim.py.resources.resource.PreemptiveResource`).

.. seealso::

    ``Resource`` requests model temporary transfer of ownership:
    every :py:meth:`~usim.py.resources.resource.Resource.request`
    is matched by an eventual :py:meth:`~usim.py.resources.resource.Resource.release`
    of the resource.
    In contrast, a :py:class:`~usim.py.resources.container.Container` models
    permanent transfer of ownership.


.. note::

    ``Resource`` types do not support the methods
    :py:meth:`~usim.py.resources.base.BaseResource.put` or
    :py:meth:`~usim.py.resources.base.BaseResource.get`
    but provide
    :py:meth:`~usim.py.resources.resource.Resource.request` or
    :py:meth:`~usim.py.resources.resource.Resource.release`
    instead.

.. py:module:: usim.py.resources.resource
    :synopsis: Shared Resource Usage

.. autoclass:: usim.py.resources.resource.Resource
    :members:

.. autoclass:: usim.py.resources.resource.PriorityResource
    :members:

.. autoclass:: usim.py.resources.resource.PreemptiveResource
    :members:

.. autoclass:: usim.py.resources.resource.Request
    :members:

.. autoclass:: usim.py.resources.resource.Release
    :members:

.. autoclass:: usim.py.resources.resource.PriorityRequest
    :members:

.. autoclass:: usim.py.resources.resource.Preempted
    :members:

Containers -- Continuous Resource Exchange
------------------------------------------

A ``Container`` models the exchange of resources between processes:
processes may
produce resources and :py:meth:`~usim.py.resources.container.Container.put`
them into the container, or
consume resources and :py:meth:`~usim.py.resources.container.Container.get`
them out of the container.
These resources may be continuous (i.e. fractions can be exchanged) and
do not need to be conserved.

.. seealso::

    ``Container`` requests model permanent transfer of ownership:
    processes may freely :py:meth:`~usim.py.resources.container.Container.get`
    and :py:meth:`~usim.py.resources.container.Container.put` content in and out of
    the container.
    In contrast, a :py:class:`~usim.py.resources.resource.Resource` models
    temporary transfer of ownership.

.. py:module:: usim.py.resources.container
    :synopsis: Continuous Resource Exchange

.. autoclass:: usim.py.resources.container.Container
    :members:

.. autoclass:: usim.py.resources.container.ContainerPut
    :members:

.. autoclass:: usim.py.resources.container.ContainerGet
    :members:

Stores -- Distinct Object Exchange
----------------------------------

The ``Store`` types implement various forms of queues:
an ordered container from which items can be removed and added.
Variants of the basic :py:class:`~usim.py.resources.store.Store`
support item priorities (:py:class:`~usim.py.resources.store.PriorityStore`)
and item filtering (:py:class:`~usim.py.resources.store.FilterStore`).

.. py:module:: usim.py.resources.store
    :synopsis: Distinct Object Exchange

.. autoclass:: usim.py.resources.store.Store
    :members:

.. autoclass:: usim.py.resources.store.PriorityStore
    :members:

.. autoclass:: usim.py.resources.store.PriorityItem
    :members:

.. autoclass:: usim.py.resources.store.FilterStore
    :members:

.. autoclass:: usim.py.resources.store.StoreGet
    :members:

.. autoclass:: usim.py.resources.store.StorePut
    :members:

.. autoclass:: usim.py.resources.store.FilterStoreGet
    :members:
