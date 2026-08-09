# Splendor local CI

GitHub Actions isn't used (the Blender-runtime tests need the ~1.5 GB built
binary, which stock GitHub-hosted runners don't have). Instead the suite runs
**locally**, gated on every push.

## Run the suite
```
bash scripts/ci/run_tests.sh
# or point at a specific binary:
SPLENDOR_BLENDER=/path/to/blender bash scripts/ci/run_tests.sh
```
Runs all `tests/splendor/` suites: pure-Python ones under `python3`, Blender-runtime
ones under `blender --background`. Exits non-zero on any failure.

## Install the pre-push gate (one-time)
```
bash scripts/ci/install-hooks.sh
```
Now `git push` runs the suite first and blocks the push if anything fails.
Bypass in an emergency: `SPLENDOR_SKIP_CI=1 git push`.

## Moving to hosted CI later
Needs a **self-hosted runner** with the built Splendor binary, or a job that builds
the fork first (slow — `make deps` + `make`). The pure-Python suites alone could run
on a stock runner if you want partial coverage.
