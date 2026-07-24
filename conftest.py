# Source - https://stackoverflow.com/a/78238069
# Posted by Miško
# Retrieved 2026-05-28, License - CC BY-SA 4.0

def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests",
)

import random
random.seed(0)