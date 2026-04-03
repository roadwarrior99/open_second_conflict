"""Shared test fixtures."""
import pytest
from second_conflict.model.constants import EMPIRE_FACTION, FREE_SLOT
from second_conflict.model.game_state import GameState, GameOptions
from second_conflict.model.star import Star, Planet
from second_conflict.model.player import Player
from second_conflict.model.fleet import FleetInTransit, EmpireOrder


def make_options(**kwargs) -> GameOptions:
    defaults = dict(difficulty=1, sim_steps=5, map_param=150, random_events=False,
                    novice_mode=False, empire_builds=False)
    defaults.update(kwargs)
    return GameOptions(**defaults)


def make_star(star_id=0, x=10, y=10, owner=1, planet_type='W',
              resource=3, base_prod=0, warships=0, transports=0,
              stealthships=0, missiles=0, planets=None) -> Star:
    if planets is None:
        planets = [Planet(owner_faction_id=owner, morale=1, recruit=3, troops=0)]
    return Star(
        star_id=star_id, x=x, y=y, owner_faction_id=owner,
        planet_type=planet_type, resource=resource, base_prod=base_prod,
        warships=warships, transports=transports,
        stealthships=stealthships, missiles=missiles,
        planets=planets,
    )


def make_player(slot=0, faction_id=1, name="Alice", is_human=True, is_active=True) -> Player:
    return Player(slot=slot, name=name, faction_id=faction_id,
                  is_human=is_human, is_active=is_active)


def make_free_fleet(slot=0) -> FleetInTransit:
    return FleetInTransit(slot=slot, owner_faction_id=FREE_SLOT,
                          dest_star=0, turns_remaining=0)


def make_fleet(slot=0, owner=1, dest=1, src=0, turns=5,
               warships=10, fleet_type='C') -> FleetInTransit:
    return FleetInTransit(slot=slot, owner_faction_id=owner,
                          dest_star=dest, src_star=src,
                          turns_remaining=turns, fleet_type_char=fleet_type,
                          warships=warships)


def make_state(stars=None, players=None, fleets=None, options=None) -> GameState:
    if options is None:
        options = make_options()
    if stars is None:
        stars = [make_star(i, x=i*5, y=i*5) for i in range(4)]
    if players is None:
        players = [make_player()]
    if fleets is None:
        fleets = [make_free_fleet(i) for i in range(10)]
    state = GameState(options=options, stars=stars, players=players,
                      fleets_in_transit=fleets)
    return state