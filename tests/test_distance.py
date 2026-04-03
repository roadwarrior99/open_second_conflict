"""Tests for engine/distance.py — star distance and travel time calculations."""
import math
import pytest
from second_conflict.engine.distance import (
    star_distance, travel_time, missile_travel_time, scout_travel_time,
)
from tests.conftest import make_star


class TestStarDistance:
    def test_same_position_is_zero(self):
        a = make_star(x=10, y=10)
        assert star_distance(a, a) == 0.0

    def test_horizontal(self):
        a = make_star(x=0, y=0)
        b = make_star(x=3, y=0)
        assert star_distance(a, b) == pytest.approx(3.0)

    def test_vertical(self):
        a = make_star(x=0, y=0)
        b = make_star(x=0, y=4)
        assert star_distance(a, b) == pytest.approx(4.0)

    def test_diagonal_345(self):
        a = make_star(x=0, y=0)
        b = make_star(x=3, y=4)
        assert star_distance(a, b) == pytest.approx(5.0)

    def test_symmetric(self):
        a = make_star(x=10, y=20)
        b = make_star(x=30, y=50)
        assert star_distance(a, b) == pytest.approx(star_distance(b, a))


class TestTravelTime:
    def test_minimum_one(self):
        a = make_star(x=0, y=0)
        b = make_star(x=0, y=0)
        assert travel_time(a, b, sim_steps=5) >= 1

    def test_further_takes_longer(self):
        origin = make_star(x=0, y=0)
        near   = make_star(x=10, y=0)
        far    = make_star(x=50, y=0)
        assert travel_time(origin, near, 5) < travel_time(origin, far, 5)

    def test_larger_map_param_takes_longer(self):
        a = make_star(x=0, y=0)
        b = make_star(x=30, y=0)
        t150 = travel_time(a, b, sim_steps=5, map_param=150)
        t200 = travel_time(a, b, sim_steps=5, map_param=200)
        assert t200 > t150


class TestMissileTravelTime:
    def test_faster_than_normal(self):
        a = make_star(x=0, y=0)
        b = make_star(x=40, y=0)
        assert missile_travel_time(a, b, 5) < travel_time(a, b, 5)

    def test_minimum_one(self):
        a = make_star(x=0, y=0)
        assert missile_travel_time(a, a, 5) >= 1


class TestScoutTravelTime:
    def test_faster_than_normal(self):
        a = make_star(x=0, y=0)
        b = make_star(x=40, y=0)
        assert scout_travel_time(a, b, 5) < travel_time(a, b, 5)

    def test_slower_than_missile(self):
        a = make_star(x=0, y=0)
        b = make_star(x=40, y=0)
        assert scout_travel_time(a, b, 5) >= missile_travel_time(a, b, 5)

    def test_minimum_one(self):
        a = make_star(x=0, y=0)
        assert scout_travel_time(a, a, 5) >= 1