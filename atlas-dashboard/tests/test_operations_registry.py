"""
atlas/tests/test_operations_registry.py

Unit tests for services/operations_registry.py (AES-009B) -- the
reusable OperationDescriptor model and list_operations() that the
Operations Center template now renders generically from.
"""

from __future__ import annotations

import pytest

from services.operations_registry import OperationDescriptor, list_operations
from services.orchestrator.pipelines.directory_launch import PIPELINE_NAME


def test_list_operations_returns_exactly_one_directory_launch_entry():
    operations = list_operations()

    assert len(operations) == 1
    assert operations[0].key == PIPELINE_NAME
    assert operations[0].name == "Directory Launch"


def test_list_operations_entries_are_operation_descriptors():
    operations = list_operations()

    assert all(isinstance(op, OperationDescriptor) for op in operations)


def test_directory_launch_descriptor_fields():
    [operation] = list_operations()

    assert operation.icon
    assert operation.route == f"#run-{PIPELINE_NAME}"
    assert operation.status == "available"
    assert operation.description


def test_operation_descriptor_is_frozen():
    descriptor = OperationDescriptor(
        key="test",
        name="Test",
        description="Test operation.",
        icon="*",
        route="#run-test",
    )

    with pytest.raises(Exception):
        descriptor.name = "Renamed"  # type: ignore[misc]


def test_operation_descriptor_status_defaults_to_available():
    descriptor = OperationDescriptor(
        key="test",
        name="Test",
        description="Test operation.",
        icon="*",
        route="#run-test",
    )

    assert descriptor.status == "available"


def test_operation_descriptor_supports_non_available_status_for_future_operations():
    descriptor = OperationDescriptor(
        key="future-op",
        name="Future Operation",
        description="Not wired up yet.",
        icon="*",
        route="#run-future-op",
        status="coming_soon",
    )

    assert descriptor.status == "coming_soon"
