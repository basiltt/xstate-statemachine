"""The examples here are demos that FAIL on purpose (a seeded bug for
`model_test`, #271). Collect them only when a file in this folder is named
explicitly on the command line, never as part of a directory run."""

import pathlib


def pytest_ignore_collect(collection_path: pathlib.Path, config) -> bool:
    if collection_path.suffix != ".py":
        return False
    named = {
        pathlib.Path(str(a).split("::")[0]).resolve() for a in config.args
    }
    return collection_path.resolve() not in named
