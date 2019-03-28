=================
Glossary of Terms
=================


.. glossary::

    Activity
        Ongoing action that drives forward a simulation - either through time or events.
        Activities may be suspended and resumed as desired, or interrupted involuntarily.

    Time
        Representation of the progression of a simulation.
        Whereas the unit of time is arbitrary, its value always grows.

        Time may only pass while all :term:`activities <Activity>` are *suspended*.
        An :term:`activity` may actively wait for the progression of time,
        or implicitly delay until an event happens at a future point in time.

    Turn
        Inherent ordering of :term:`events <event>` happening at the same :term:`time`.

    Event
        A well-defined occurrence at a specific point in :term:`time`.
        Events may occur
        as result of activities ("dinner is done"),
        as time passes ("after 20 time units"),
        or
        at predefined points in time ("at 2000 time units"),

    Notification
        Information sent to an :term:`activity`, usually in response to an :term:`event`.
