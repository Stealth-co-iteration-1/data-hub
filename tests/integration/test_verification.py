"""Verification tests confirming data integrity (VERF-01).

These tests verify that data stored via repository.add() can be
retrieved via repository.get() with exact same content.
"""
import pytest


class TestDataVerification:
    """Tests for data verification capability (VERF-01)."""

    async def test_data_roundtrip_integrity(self, repository):
        """Data retrieved matches exactly what was submitted."""
        original_data = {
            "name": "Test Record",
            "email": "test@example.com",
            "active": True,
            "score": 95.5,
            "count": 42,
        }

        record_id = await repository.add(
            model="contacts",
            connection_id="verification_test",
            data=original_data,
        )

        retrieved = await repository.get("contacts", record_id)

        # Exact match - no data loss or transformation
        assert retrieved == original_data

    async def test_data_preserves_extra_fields(self, repository):
        """Extra fields beyond expected schema are preserved."""
        data_with_extras = {
            "required_field": "value",
            "extra_field_1": "should be preserved",
            "extra_field_2": 12345,
            "_metadata": {"source": "test"},
        }

        record_id = await repository.add(
            model="flexible_schema",
            connection_id="test",
            data=data_with_extras,
        )

        retrieved = await repository.get("flexible_schema", record_id)

        assert retrieved == data_with_extras
        assert retrieved["extra_field_1"] == "should be preserved"
        assert retrieved["_metadata"]["source"] == "test"

    async def test_data_preserves_nested_structures(self, repository):
        """Nested dicts and lists are preserved exactly."""
        nested_data = {
            "contact": {
                "name": "Alice",
                "address": {
                    "street": "123 Main St",
                    "city": "Boston",
                    "zip": "02101",
                },
            },
            "tags": ["customer", "vip", "enterprise"],
            "metadata": {
                "created_by": "import_script",
                "source_ids": [1, 2, 3],
            },
        }

        record_id = await repository.add(
            model="contacts",
            connection_id="nested_test",
            data=nested_data,
        )

        retrieved = await repository.get("contacts", record_id)

        assert retrieved == nested_data
        assert retrieved["contact"]["address"]["city"] == "Boston"
        assert retrieved["tags"] == ["customer", "vip", "enterprise"]
        assert retrieved["metadata"]["source_ids"] == [1, 2, 3]

    async def test_multiple_records_independently_verifiable(self, repository):
        """Each record can be verified independently."""
        records = [
            {"id": 1, "name": "Record A"},
            {"id": 2, "name": "Record B"},
            {"id": 3, "name": "Record C"},
        ]

        record_ids = []
        for data in records:
            rid = await repository.add(model="batch", connection_id="batch_test", data=data)
            record_ids.append(rid)

        # Each record independently verifiable
        for i, rid in enumerate(record_ids):
            retrieved = await repository.get("batch", rid)
            assert retrieved == records[i]

    async def test_null_values_preserved(self, repository):
        """Null values in data are preserved, not stripped."""
        data_with_nulls = {
            "name": "Test",
            "optional_field": None,
            "nested": {
                "also_null": None,
            },
        }

        record_id = await repository.add(
            model="nullable",
            connection_id="null_test",
            data=data_with_nulls,
        )

        retrieved = await repository.get("nullable", record_id)

        assert retrieved == data_with_nulls
        assert retrieved["optional_field"] is None
        assert retrieved["nested"]["also_null"] is None
