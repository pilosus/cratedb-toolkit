# Copyright (c) 2021-2023, Crate.io Inc.
# Distributed under the terms of the AGPLv3 license, see LICENSE.
import pytest
import responses

from cratedb_toolkit.testing.testcontainers.cratedb import CrateDBTestAdapter
from cratedb_toolkit.util.common import setup_logging

# Use different schemas for storing the subsystem database tables, and the
# test/example data, so that they do not accidentally touch the default `doc`
# schema.
TESTDRIVE_DATA_SCHEMA = "testdrive-data"
TESTDRIVE_EXT_SCHEMA = "testdrive-ext"
RESET_TABLES = [
    f'"{TESTDRIVE_EXT_SCHEMA}"."retention_policy"',
    f'"{TESTDRIVE_DATA_SCHEMA}"."raw_metrics"',
    f'"{TESTDRIVE_DATA_SCHEMA}"."sensor_readings"',
    f'"{TESTDRIVE_DATA_SCHEMA}"."testdrive"',
    f'"{TESTDRIVE_DATA_SCHEMA}"."foobar"',
    f'"{TESTDRIVE_DATA_SCHEMA}"."foobar_unique_single"',
    f'"{TESTDRIVE_DATA_SCHEMA}"."foobar_unique_composite"',
    # cratedb_toolkit.io.{influxdb,mongodb}
    '"testdrive"."demo"',
]

CRATEDB_HTTP_PORT = 44209
CRATEDB_SETTINGS = {"http.port": CRATEDB_HTTP_PORT}


@pytest.fixture(scope="session", autouse=True)
def configure_database_schema(session_mocker):
    """
    Configure the machinery to use a different schema for storing subsystem database
    tables, so that they do not accidentally touch the production system.

    If not configured otherwise, the test suite currently uses `testdrive-ext`.
    """
    session_mocker.patch("os.environ", {"CRATEDB_EXT_SCHEMA": TESTDRIVE_EXT_SCHEMA})


@pytest.fixture(scope="session")
def cratedb_service():
    """
    Provide a CrateDB service instance to the test suite.
    """
    db = CrateDBTestAdapter()
    db.start(ports={CRATEDB_HTTP_PORT: None}, cmd_opts=CRATEDB_SETTINGS)
    db.reset(tables=RESET_TABLES)
    yield db
    db.stop()


@pytest.fixture(scope="function")
def cratedb(cratedb_service):
    """
    Provide a fresh canvas to each test case invocation, by resetting database content.
    """
    cratedb_service.reset(tables=RESET_TABLES)
    yield cratedb_service


@pytest.fixture
def cloud_cluster_mock():
    responses.add(
        responses.Response(
            method="GET",
            url="https://console.cratedb.cloud/api/v2/clusters/e1e38d92-a650-48f1-8a70-8133f2d5c400/",
            json={"url": "https://testdrive.example.org:4200/", "project_id": "3b6b7c82-d0ab-458c-ae6f-88f8346765ee"},
        )
    )
    responses.add(
        responses.Response(
            method="POST",
            url="https://console.cratedb.cloud/api/v2/clusters/e1e38d92-a650-48f1-8a70-8133f2d5c400/import-jobs/",
            json={"id": "testdrive-job-id", "status": "REGISTERED"},
        )
    )
    responses.add(
        responses.Response(
            method="GET",
            url="https://console.cratedb.cloud/api/v2/clusters/e1e38d92-a650-48f1-8a70-8133f2d5c400/import-jobs/",
            json=[
                {
                    "id": "testdrive-job-id",
                    "status": "SUCCEEDED",
                    "progress": {"message": "Import succeeded"},
                    "destination": {"table": "basic"},
                }
            ],
        )
    )


setup_logging()
