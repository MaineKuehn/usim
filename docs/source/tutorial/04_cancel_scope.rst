
Interlude 01: Interrupting Scopes
---------------------------------

.. code:: python3

    >>> from usim import time, until
    >>>
    >>> async def deliver_one(which):
    ...     print('Delivering', which, 'at', time.now)
    ...     await (time + 5)
    ...     print('Delivered', which, 'at', time.now)
    >>>
    >>> async def deliver_all(count=3):
    ...     print('-- Start deliveries at', time.now)
    ...     async with until(time + 10) as deliveries:   # 1
    ...         for delivery in range(count):          # 2
    ...             deliveries.do(deliver_one(delivery))
    ...             await (time + 3)
    ...         print('Sent deliveries at', time.now)  # 4.1
    ...     print('-- Done deliveries at', time.now)   # 4.2
