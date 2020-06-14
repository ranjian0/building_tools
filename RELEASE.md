This document outlines the release life cycle for building tools addon.

It will include details about:
- The various stages of the release cycle.
- The duration of each stage of the release cycle.
- The activities that are to be conducted during each stage.


## Stages
---
1. Pre-alpha.
2. Alpha.
3. Beta.
4. Release Candidate.
5. Stable Release.

## Stage Details
---

**1. Pre-alpha**

Pre-alpha refers to the stage of development where a given set of features is completed
in preparation for testing.

Activities in this stage include normal software development with aim of meeting stipulated
requirements/functionality.

> Estimated Duration: **2 - 3 months**.

**2. Alpha**

Alpha refers to the stage in the release cycle when serious software testing begins.
Software at this stage has not been tested by developers and may contain serious errors.

During the course of this stage, new feature may be added, but the end of this phase
sets in a feature freeze, indicating that no more features should be added.

> Estimated Duration: **1 month**.

**3. Beta**

The beta stage begins when the software is feature complete but may contain some known/unkown bugs.
The goal of this stage is to reduce as much as possible bugs that may be in the software and
also enhace usability. This means that arising issues such as performance should be tackled at this
stage.

> Estimated Duration: **2 - 3 weeks**.

**4. Release Candidate**

Release candiate is the stage at which the software has potential to be a stable product unless
significant bugs emerge.

This is a stage of product stabilization.

> Estimated Duration: **1 week**.

**5. Stable Release**

This is the last release candiate where remaining bugs have been considered acceptable.

Stable release marks the end of one software development cycle after which iteration may be made to include more
features.

> Estimated Duration: **undefined**.

## Versioning Scheme

Given a version number MAJOR.MINOR.PATCH, increment the:

> MAJOR version when you make incompatible API changes,
> MINOR version when you add functionality in a backwards-compatible manner, and
> PATCH version when you make backwards-compatible bug fixes.
