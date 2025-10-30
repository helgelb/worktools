"""Tests for allocate_hours module."""

import pytest

from allocate_hours import (
    allocate_optimal,
    allocate_sequential,
    get_decimal_places,
    round_to_resolution,
)


class TestRoundToResolution:
    """Test the round_to_resolution function."""

    def test_round_to_half_hour(self):
        """Test rounding to half-hour resolution."""
        assert round_to_resolution(1.2, 0.5) == 1.0
        assert round_to_resolution(1.3, 0.5) == 1.5
        assert round_to_resolution(1.7, 0.5) == 1.5
        assert round_to_resolution(1.8, 0.5) == 2.0

    def test_round_to_quarter_hour(self):
        """Test rounding to quarter-hour resolution."""
        assert round_to_resolution(1.1, 0.25) == 1.0
        assert round_to_resolution(1.15, 0.25) == 1.25
        assert round_to_resolution(1.4, 0.25) == 1.5

    def test_round_to_fine_resolution(self):
        """Test rounding to 0.01 hour resolution (high precision)."""
        assert round_to_resolution(1.234, 0.01) == pytest.approx(1.23)
        assert round_to_resolution(1.235, 0.01) == pytest.approx(1.24)
        assert round_to_resolution(1.236, 0.01) == pytest.approx(1.24)
        assert round_to_resolution(0.567, 0.01) == pytest.approx(0.57)

    def test_round_to_whole_hour(self):
        """Test rounding to whole hour resolution."""
        assert round_to_resolution(0.4, 1.0) == 0.0
        assert round_to_resolution(0.6, 1.0) == 1.0
        assert round_to_resolution(1.4, 1.0) == 1.0
        assert round_to_resolution(1.6, 1.0) == 2.0

    def test_invalid_resolution(self):
        """Test error handling for invalid resolution."""
        with pytest.raises(ValueError):
            round_to_resolution(1.0, 0)
        with pytest.raises(ValueError):
            round_to_resolution(1.0, -0.5)

    def test_get_decimal_places(self):
        """Test the get_decimal_places helper function."""
        assert get_decimal_places(1.0) == 0
        assert get_decimal_places(0.5) == 1
        assert get_decimal_places(0.25) == 2
        assert get_decimal_places(0.01) == 2
        assert get_decimal_places(0.001) == 3


class TestAllocateOptimal:
    """Test the allocate_optimal function."""

    def test_basic_allocation(self):
        """Test basic optimal allocation."""
        days = {"monday": 8.0, "tuesday": 8.0}
        percentages = [0.5, 0.5]
        resolution = 0.5

        allocations, targets, remainder = allocate_optimal(
            days, percentages, resolution
        )

        # Check structure
        assert "monday" in allocations
        assert "tuesday" in allocations
        assert len(targets) == 2
        assert remainder >= 0

        # Check allocation doesn't exceed day totals
        for _day, vals in allocations.items():
            assert sum(vals[1:]) <= vals[0] + 1e-6  # Allow small floating point errors

    def test_zero_hours(self):
        """Test allocation with zero hours."""
        days = {"monday": 0.0, "tuesday": 8.0}
        percentages = [0.75, 0.25]
        resolution = 0.5

        allocations, _, _ = allocate_optimal(days, percentages, resolution)

        # Monday should have zero allocation
        assert all(v == 0 for v in allocations["monday"][1:])

        # Tuesday should get all allocation
        assert sum(allocations["tuesday"][1:]) <= 8.0

    def test_uneven_percentages(self):
        """Test allocation with uneven percentages."""
        days = {"monday": 10.0}
        percentages = [0.7, 0.2, 0.1]
        resolution = 0.5

        _allocations, targets, _ = allocate_optimal(days, percentages, resolution)

        # Check that targets roughly match expected values
        total_hours = 10.0
        expected_targets = [p * total_hours for p in percentages]
        for i, target in enumerate(targets):
            assert (
                abs(target - expected_targets[i]) <= 0.5
            )  # Within resolution tolerance

    def test_invalid_resolution_for_optimal(self):
        """Test that invalid resolution raises error in optimal algorithm."""
        days = {"monday": 8.0}
        percentages = [0.5, 0.5]

        with pytest.raises(ValueError):
            allocate_optimal(days, percentages, 0.3)  # Doesn't divide 1.0 evenly


class TestAllocateSequential:
    """Test the allocate_sequential function."""

    def test_basic_allocation(self):
        """Test basic sequential allocation."""
        days = {"monday": 8.0, "tuesday": 8.0}
        percentages = [0.5, 0.5]
        resolution = 0.5

        allocations, targets, remainder = allocate_sequential(
            days, percentages, resolution
        )

        # Check structure
        assert "monday" in allocations
        assert "tuesday" in allocations
        assert len(targets) == 2
        assert remainder >= 0

        # Check allocation doesn't exceed day totals
        for _day, vals in allocations.items():
            assert sum(vals[1:]) <= vals[0] + 1e-6

    def test_single_day(self):
        """Test allocation with single day."""
        days = {"monday": 8.0}
        percentages = [0.6, 0.4]
        resolution = 0.5

        allocations, _, _ = allocate_sequential(days, percentages, resolution)

        # Should allocate within the single day
        monday_vals = allocations["monday"]
        assert monday_vals[0] == 8.0  # Total hours
        assert sum(monday_vals[1:]) <= 8.0  # Allocated doesn't exceed total

    def test_all_zero_hours(self):
        """Test allocation when all days have zero hours."""
        days = {"monday": 0.0, "tuesday": 0.0}
        percentages = [0.5, 0.5]
        resolution = 0.5

        allocations, targets, remainder = allocate_sequential(
            days, percentages, resolution
        )

        # All allocations should be zero
        for _day, vals in allocations.items():
            assert all(v == 0 for v in vals[1:])

        # Targets should be zero
        assert all(t == 0 for t in targets)
        assert remainder == 0


class TestIntegration:
    """Integration tests comparing algorithms."""

    def test_algorithms_produce_valid_results(self):
        """Test that both algorithms produce valid allocations."""
        days = {"mon": 0, "tue": 2, "wed": 7.5, "thu": 7.5, "fri": 7.5}
        percentages = [0.6, 0.4]
        resolution = 0.5

        opt_alloc, _, _ = allocate_optimal(days, percentages, resolution)
        seq_alloc, _, _ = allocate_sequential(days, percentages, resolution)

        # Both should produce valid allocations
        for allocations in [opt_alloc, seq_alloc]:
            for _day, vals in allocations.items():
                # Check structure
                assert len(vals) == 3  # total + 2 categories
                assert vals[0] == days[_day]  # Total should match input
                assert sum(vals[1:]) <= vals[0] + 1e-6  # Allocation <= total

                # Check resolution compliance
                for val in vals[1:]:
                    assert abs(val - round_to_resolution(val, resolution)) < 1e-9

    def test_both_algorithms_handle_edge_cases(self):
        """Test that both algorithms handle edge cases similarly."""
        test_cases = [
            # All zero hours
            ({"mon": 0, "tue": 0}, [0.5, 0.5], 0.5),
            # Single day with small hours
            ({"mon": 1.0}, [0.7, 0.3], 0.5),
            # Uneven distribution
            ({"mon": 3, "tue": 5, "wed": 2}, [0.4, 0.4, 0.2], 0.5),
        ]

        for days, percentages, resolution in test_cases:
            opt_alloc, _, _ = allocate_optimal(days, percentages, resolution)
            seq_alloc, _, _ = allocate_sequential(days, percentages, resolution)

            # Both should handle the case without errors
            assert len(opt_alloc) == len(days)
            assert len(seq_alloc) == len(days)

            # Both should respect day limits
            for day in days:
                assert sum(opt_alloc[day][1:]) <= days[day] + 1e-6
                assert sum(seq_alloc[day][1:]) <= days[day] + 1e-6
