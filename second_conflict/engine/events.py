"""Random event processing.

Faithful translation of FUN_1088_07a7 from SCW.EXE.

10 event types are selected by rolling rand(10)+1 per player per turn
when random_events is enabled.  Each event is gated by a difficulty-
scaled probability check.
"""
from second_conflict.model.constants import EMPIRE_FACTION
from second_conflict.model.game_state import GameState
from second_conflict.util.rng import rand


def process(state: GameState):
    for player in active_players_with_stars(state):
        if not player.is_human:
            continue   # random events only affect human players
        if rand(100) < _threshold(state.options.difficulty):
            event_type = rand(10) + 1
            _fire_event(event_type, player, state)


def _threshold(difficulty: int) -> int:
    return 20 + difficulty * 10


def _fire_event(event_type: int, player, state: GameState):
    my_stars = state.stars_owned_by(player.faction_id)
    if not my_stars:
        return

    if event_type == 1:
        _imperial_missile_strike(player, my_stars, state)
    elif event_type == 2:
        _independence_movement(player, my_stars, state)
    elif event_type == 3:
        _tech_breakthrough(player, my_stars, state)
    elif event_type == 4:
        _muon_cloud(player, state)
    elif event_type == 5:
        _reinforcements(player, my_stars, state)
    elif event_type == 6:
        _espionage(player, state)
    elif event_type == 7:
        _pirate_raid(player, my_stars, state)
    elif event_type == 8:
        _diplomatic_overture(player, state)
    elif event_type == 9:
        _resource_discovery(player, my_stars, state)
    elif event_type == 10:
        _plague(player, my_stars, state)


# ---------------------------------------------------------------------------
# Individual event implementations
# ---------------------------------------------------------------------------

def _imperial_missile_strike(player, my_stars, state: GameState):
    star = my_stars[rand(len(my_stars))]
    losses = rand(5) + 3
    star.warships = max(0, star.warships - losses)
    state.add_event('event', player.faction_id,
                    f"Imperial missile strike destroys {losses} WarShips at star {star.star_id}!")


def _independence_movement(player, my_stars, state: GameState):
    star = my_stars[rand(len(my_stars))]
    defectors = max(1, star.warships // 4)
    star.warships = max(0, star.warships - defectors)
    state.add_event('revolt', player.faction_id,
                    f"Independence movement: {defectors} WarShips lost at star {star.star_id}.")


def _tech_breakthrough(player, my_stars, state: GameState):
    star = my_stars[rand(len(my_stars))]
    if rand(2) == 0:
        star.resource = min(star.resource + 1, 15)
        state.add_event('event', player.faction_id,
                        f"Tech breakthrough! Star {star.star_id} production increased.")
    else:
        from second_conflict.model.constants import PlanetType
        if star.planet_type == PlanetType.NEUTRAL:
            star.planet_type = PlanetType.FACTORY
        state.add_event('event', player.faction_id,
                        f"Tech breakthrough! New factory at star {star.star_id}.")


def _muon_cloud(player, state: GameState):
    active = [f for f in state.fleets_in_transit
              if f.owner_faction_id == player.faction_id]
    if not active:
        return
    fleet = active[rand(len(active))]
    losses = rand(fleet.warships + 1)
    fleet.warships = max(0, fleet.warships - losses)
    state.add_event('event', player.faction_id,
                    f"Muon cloud damages fleet: {losses} WarShips lost!")


def _reinforcements(player, my_stars, state: GameState):
    star = my_stars[rand(len(my_stars))]
    count = rand(5) + 2
    star.warships += count
    state.add_event('reinforce', player.faction_id,
                    f"Reinforcements: {count} WarShips arrive at star {star.star_id}.")


def _espionage(player, state: GameState):
    enemy_fleets = [f for f in state.fleets_in_transit
                    if f.owner_faction_id != player.faction_id
                    and f.owner_faction_id != EMPIRE_FACTION
                    and not f.is_free]
    if not enemy_fleets:
        return
    fleet = enemy_fleets[rand(len(enemy_fleets))]
    enemy = state.player_for_faction(fleet.owner_faction_id)
    enemy_name = enemy.name if enemy else f"Faction {fleet.owner_faction_id:02x}"
    state.add_event('scout', player.faction_id,
                    f"Intelligence: {enemy_name}'s fleet en route to star {fleet.dest_star}, "
                    f"{fleet.turns_remaining} turns away.")


def _pirate_raid(player, my_stars, state: GameState):
    star = my_stars[rand(len(my_stars))]
    stolen = rand(50) + 10
    player.credits = max(0, player.credits - stolen)
    state.add_event('event', player.faction_id,
                    f"Pirates raided star {star.star_id}! {stolen} credits stolen.")


def _diplomatic_overture(player, state: GameState):
    others = [p for p in state.active_players() if p.faction_id != player.faction_id
              and p.faction_id != EMPIRE_FACTION]
    if not others:
        return
    other = others[rand(len(others))]
    bonus = rand(30) + 10
    player.credits += bonus
    state.add_event('event', player.faction_id,
                    f"Diplomatic overture from {other.name}: {bonus} credits received.")


def _resource_discovery(player, my_stars, state: GameState):
    star = my_stars[rand(len(my_stars))]
    star.resource = min(star.resource + 1, 15)
    state.add_event('event', player.faction_id,
                    f"Resource deposits at star {star.star_id}! "
                    f"Production increased to {star.resource}.")


def _plague(player, my_stars, state: GameState):
    star = my_stars[rand(len(my_stars))]
    if star.planets:
        planet = star.planets[rand(len(star.planets))]
        losses = max(1, planet.troops // 5)
        planet.troops = max(0, planet.troops - losses)
        state.add_event('event', player.faction_id,
                        f"Plague at star {star.star_id}! {losses} troops lost.")


def active_players_with_stars(state: GameState):
    return [p for p in state.active_players()
            if state.stars_owned_by(p.faction_id)]


GameState.active_players = lambda self: [p for p in self.players if p.is_active]