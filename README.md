TIS-backup Documentation
========================

This is the documentation repository of the TIS-backup project.
The documentation is provided under the license CC-BY-SA.

How to contribute?
==================

You must install documentation tools and requirements before doing anything:

```bash
sudo sh ./install_requirements.sh
```

Once installed, pre-commit checks (lint/syntax) are launched prior
to committing your changes. To launch tests manually, you can run the following:

```bash
pre-commit run --all-files
```

This should (take a while because sphinx-build) return :

```bash
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
rst ``code`` is two backticks............................................Passed
sphinx build.............................................................Passed
```

How to push documentation to public ?
=====================================

Pushing the documentation through a rsync is bad.

To publish WAPT documentation to public, a 'release-' tag must be set using git.

Once a release tag has been set, it creates a tagged build which
must be launched manually in Jenkins.

```bash
git add *
git commit -m 'I have checked it builds without errors, trust me'
git push
git tag -a release-1.8.1.6694-doc -m "WAPT documentation publish for 1.8.1.6694"
git push origin --tags
```

Once that tag has been pushed, in Jenkins you have to re-scan
the multi-branche project and go to `Tags` tab, select your tag and build it.

Wait for the entire build to go through, it will publish everything
according to JenkinsFile procedure.
