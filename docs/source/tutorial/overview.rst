Brief Tour to μSim
==================

.. container:: left-col

    This is a short tutorial to using μSim to create your own simulation.
    Teaching by example, the tutorial will get you started quickly.
    It provides an overview of how to best use all tools provided by μSim.
    If needed, additional information is directly accessible from each section.

    If you are already familiar with Python, install ``usim`` and head straight to the :doc:`first section <./01_activity>`.
    Otherwise, proceed below for a short introduction to install μSim and launch Python.

    .. toctree::
        :maxdepth: 1

        01_activity
        02_stacked
        03_scopes

Installing μSim
---------------

.. content-tabs:: left-col

    The newest version of μSim is readily available via Python's package manager.
    You only need Python 3.5 or newer to get started.

.. container:: content-tabs right-col

    .. code:: bash

        python3 -m pip install usim

.. content-tabs:: left-col

    This takes care of installing μSim (the ``usim`` package) and any dependencies. [#pypy3]_

Interactive or Scripted
-----------------------

.. container:: left-col

    You can use μSim both from an interactive Python shell, or a Python script.
    A shell makes it easier to develop and experiment; a script simplifies reuse and reproducibility.
    However, you can freely switch between the two as you prefer.
    The only difference is whether you write code to the shell or a file!

The Shell
.........

.. content-tabs:: left-col

    Python already ships with a basic interactive shell.
    It can be launched from a terminal by typing ``python3``.
    Simply enter the code as desired - but make sure to indent it properly!
    The shell automatically executes any line that is a completed statement, or asks for more with ``...``:

.. content-tabs:: right-col

    .. code:: python3

        $ python3
        Python 3.7.0 (default, Sep 14 2018, 16:24:12)
        [Clang 9.0.0 (clang-900.0.39.2)] on darwin
        Type "help", "copyright", "credits" or "license" for more information.
        >>> # insert your code after >>> or ...
        >>> from usim import run, time
        >>>
        >>> print('usim version:', usim.__version__)
        usim version: 0.1.0
        >>>

.. content-tabs:: left-col

    There are various advanced shells available that make your life easier.
    For example, ``ipython3`` offers code completion, help messages and other convenience features. [#ipython]_

Scripting
.........

.. content-tabs:: left-col

    Python can directly execute code from files.
    Simply open a file and write your code inside;
    any text editor is suitable for small scripts.
    Note that no code is executed at this time.

.. content-tabs:: right-col

    .. code:: python3

        # my_script.py
        from usim import run, time

        print('usim version:', usim.__version__)

.. content-tabs:: left-col

    To run an existing script from a terminal,
    execute Python with the path of the script.

.. content-tabs:: right-col

    .. code:: bash

        $ python3 my_script.py
        usim version: 0.1.0

.. content-tabs:: left-col

    As your simulations become more complex,
    scripts allow you to re-run and fine-tune your work.
    Various advanced text editors and IDEs are available
    to help you write correct and maintainable code.

Let's get started...
--------------------

.. content-tabs:: left-col

    You now have Python and μSim ready to get started.
    Head over to the :doc:`next section <./01_activity>` to write your first simulation.

    .. [#pypy3] Note that μSim does not require any non-Python dependencies.
                It is fully compatible and tested with PyPy3 as well, if you need more speed.

    .. [#ipython] Install it by executing ``python3 -m pip install ipython``.
