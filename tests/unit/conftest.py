# pylint: disable=import-outside-toplevel
import os

import boto3
import pytest

os.environ.setdefault("LOG_LEVEL", "INFO")