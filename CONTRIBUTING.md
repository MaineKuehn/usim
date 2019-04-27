# Contributing to μSim

μSim is hosted on GitHub and open source.
This makes it easy for you to submit bug reports or directly propose changes.

## Reporting a Bug

Enabling precise and reliable simulations is our goal,
and that means chasing every single bug.
However, there is so little time in a day -
Please help us help you!

* Avoid reporting issues that are already being worked on:
  * *Exclude version issues:*
    Test whether the issue also occurs with the most recent version of μSim.
  * *Check previous reports:*
    Have a look at [previous reports](https://github.com/MaineKuehn/usim/issues?q=is%3Aissue+label%3Abug)
    if any of those matches your issue.
    Feel free to comment on open issues, especially when they are old.
* Isolate the cause of the issue:
  * Identify where in your simulation the issue occurs, and under which conditions.
    Try to build a complete, verifiable example that is as small as possible. 
  * Even if you can fix the code yourself, consider whether our API misled you.
    There are some errors which cannot be prevented, only mitigated.
* Open an [issue ticket](https://github.com/MaineKuehn/usim/issues/new) with as much information as possible:
  * Use a title that describes the general, underlying problem.
    Remember that other people may search through reported issues.
  * Describe both the *desired* behaviour you expected,
    as well as *actual* behaviour you observed.
  * Provide basic code that reproduces or at least illustrates your setup.
    If the error caused an Exception, include the traceback.

## Submitting Fixes and Features

We welcome direct contributions of code and documentation,
but also need to maintain the current and future quality of μSim.
The better you integrate with the development style of μSim,
the more likely and faster we can include your contribution.

* Locate your contribution with respect to ongoing development:
  * Check the [open issues](https://github.com/MaineKuehn/usim/issues?q=is%3Aissue+label%3Abug+is%3Aopen)
    if they are fixed by your changes.
    If there is no open issue yet, it might be a good idea to create one for documentation.
  * Check the [open pull requests](https://github.com/MaineKuehn/usim/pulls)
    if they are similar to your changes.
    Make sure to assess how your contribution relates to conflicting changes.
* Open a [pull request](https://github.com/MaineKuehn/usim/pulls) for your changes:
  * Use a title that describes the contribution as clearly as possible.
    For new features, prepend ``WIP:`` to the title to show that it needs discussion.
  * Provide a description of the changes, ideally with a short example.
    Include references to all related issues and pull requests.
* We will review your changes before merging
