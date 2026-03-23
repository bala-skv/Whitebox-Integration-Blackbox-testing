"""Integration Tests for StreetRace Manager.

Each test validates cross-module interactions as shown in the Call Graph.
Tests are grouped by which modules interact with each other.
"""

import pytest
import random
from registration import Registration
from crew_management import CrewManagement
from inventory import Inventory
from race_management import RaceManagement
from results import Results
from mission_planning import MissionPlanning
from garage import Garage
from leaderboard import Leaderboard


# ============================================================
# Fixtures: set up a fresh system for each test
# ============================================================

@pytest.fixture
def system():
    """Create a fully wired StreetRace Manager system."""
    reg = Registration()
    crew = CrewManagement(reg)
    inv = Inventory(starting_cash=10000)
    race_mgmt = RaceManagement(reg, crew, inv)
    res = Results(race_mgmt, inv)
    missions = MissionPlanning(reg, crew)
    gar = Garage(inv, crew)
    lb = Leaderboard(reg)
    return {
        "reg": reg, "crew": crew, "inv": inv,
        "race": race_mgmt, "results": res,
        "missions": missions, "garage": gar, "lb": lb,
    }


# ============================================================
# 1. Crew Management ↔ Registration
#    Call Graph edges:
#      - _validate_member → is_registered
#      - assign_role → get_member
#      - get_by_role → list_members
#      - is_role → get_member
# ============================================================

class TestCrewRegistrationIntegration:
    """Tests for Crew Management ↔ Registration interactions."""

    def test_assign_role_requires_registration(self, system):
        """Scenario: Try to assign a role to an unregistered member.
        Modules: CrewManagement → Registration.is_registered
        Expected: ValueError because member is not registered.
        Why needed: Ensures crew management enforces registration before
        any role operations, preventing ghost crew members."""
        with pytest.raises(ValueError, match="not registered"):
            system["crew"].assign_role("fake_id", "driver")

    def test_assign_role_to_registered_member(self, system):
        """Scenario: Register a member, then change their role.
        Modules: Registration.register → CrewManagement.assign_role → Registration.get_member
        Expected: Role is updated successfully in the registration data.
        Why needed: Verifies that role changes flow through both modules correctly."""
        mid = system["reg"].register_member("Alice", "mechanic")
        system["crew"].assign_role(mid, "driver")
        member = system["reg"].get_member(mid)
        assert member["role"] == "driver"

    def test_set_skill_requires_registration(self, system):
        """Scenario: Try to set skill level for an unregistered member.
        Modules: CrewManagement → Registration.is_registered
        Expected: ValueError because member doesn't exist.
        Why needed: Skill data shouldn't exist for non-existent members."""
        with pytest.raises(ValueError, match="not registered"):
            system["crew"].set_skill_level("fake_id", 5)

    def test_get_by_role_reads_registration_data(self, system):
        """Scenario: Register multiple members, filter by role.
        Modules: CrewManagement.get_by_role → Registration.list_members
        Expected: Only members with matching role are returned.
        Why needed: Confirms crew queries correctly read live registration data."""
        system["reg"].register_member("Alice", "driver")
        system["reg"].register_member("Bob", "mechanic")
        system["reg"].register_member("Charlie", "driver")
        drivers = system["crew"].get_drivers()
        assert len(drivers) == 2
        assert all(d["role"] == "driver" for d in drivers)

    def test_is_role_checks_registration(self, system):
        """Scenario: Check if a registered member has a specific role.
        Modules: CrewManagement.is_role → Registration.get_member
        Expected: Returns True for correct role, False for wrong role.
        Why needed: Race entry depends on this check being accurate."""
        mid = system["reg"].register_member("Alice", "driver")
        assert system["crew"].is_role(mid, "driver") is True
        assert system["crew"].is_role(mid, "mechanic") is False


# ============================================================
# 2. Race Management ↔ Registration + Crew Management + Inventory
#    Call Graph edges:
#      - enter_race → Registration.is_registered
#      - enter_race → CrewManagement.is_role
#      - enter_race → Inventory.is_car_available
#      - complete_race → Inventory.damage_car
# ============================================================

class TestRaceEntryIntegration:
    """Tests for Race Management entry validation across modules."""

    def test_register_driver_then_enter_race(self, system):
        """Scenario: Register a driver, add a car, enter both into a race.
        Modules: Registration → CrewManagement → Inventory → RaceManagement
        Expected: Entry succeeds, race has 1 entry.
        Why needed: This is the primary happy path – all modules must
        cooperate for a valid race entry."""
        did = system["reg"].register_member("Max", "driver")
        cid = system["inv"].add_car("Supra", 250)
        rid = system["race"].create_race("Night Race", 5000)
        system["race"].enter_race(rid, did, cid)
        race = system["race"].get_race(rid)
        assert len(race["entries"]) == 1
        assert race["entries"][0]["driver_id"] == did

    def test_enter_race_without_registration(self, system):
        """Scenario: Try to enter a race with an unregistered driver.
        Modules: RaceManagement.enter_race → Registration.is_registered
        Expected: ValueError – driver not registered.
        Why needed: Prevents unknown people from entering races."""
        cid = system["inv"].add_car("GTR", 240)
        rid = system["race"].create_race("Test Race", 1000)
        with pytest.raises(ValueError, match="not registered"):
            system["race"].enter_race(rid, "fake_driver", cid)

    def test_enter_race_with_non_driver_role(self, system):
        """Scenario: Register a mechanic, try to enter them in a race.
        Modules: RaceManagement.enter_race → CrewManagement.is_role
        Expected: ValueError – member doesn't have 'driver' role.
        Why needed: Only drivers should race; a mechanic on the track
        would be dangerous and break business rules."""
        mid = system["reg"].register_member("Bob", "mechanic")
        cid = system["inv"].add_car("Civic", 200)
        rid = system["race"].create_race("Test Race", 1000)
        with pytest.raises(ValueError, match="driver"):
            system["race"].enter_race(rid, mid, cid)

    def test_enter_race_with_damaged_car(self, system):
        """Scenario: Damage a car, then try to enter it in a race.
        Modules: RaceManagement.enter_race → Inventory.is_car_available
        Expected: ValueError – car is damaged and unavailable.
        Why needed: Racing a damaged car is unsafe; inventory must
        communicate car status to race management."""
        did = system["reg"].register_member("Max", "driver")
        cid = system["inv"].add_car("Supra", 250)
        system["inv"].damage_car(cid)
        rid = system["race"].create_race("Test Race", 1000)
        with pytest.raises(ValueError, match="not available"):
            system["race"].enter_race(rid, did, cid)

    def test_enter_race_with_nonexistent_car(self, system):
        """Scenario: Try to enter a race with a car ID that doesn't exist.
        Modules: RaceManagement.enter_race → Inventory.is_car_available
        Expected: ValueError – car not found.
        Why needed: Prevents racing with phantom vehicles."""
        did = system["reg"].register_member("Max", "driver")
        rid = system["race"].create_race("Test Race", 1000)
        with pytest.raises(ValueError, match="not available"):
            system["race"].enter_race(rid, did, "fake_car")


class TestRaceDamageIntegration:
    """Tests for race completion damaging cars via Inventory."""

    def test_race_completion_can_damage_cars(self, system):
        """Scenario: Complete a race and check if cars get damaged.
        Modules: RaceManagement.complete_race → Inventory.damage_car
        Expected: Some cars may be marked as damaged (50% chance each).
        Why needed: Verifies that race completion triggers the damage
        mechanic in the inventory module."""
        random.seed(42)  # reproducible
        did = system["reg"].register_member("Max", "driver")
        d2 = system["reg"].register_member("Lewis", "driver")
        c1 = system["inv"].add_car("Car1", 250)
        c2 = system["inv"].add_car("Car2", 240)
        rid = system["race"].create_race("Damage Test", 1000)
        system["race"].enter_race(rid, did, c1)
        system["race"].enter_race(rid, d2, c2)
        system["race"].start_race(rid)
        damaged = system["race"].complete_race(rid)
        # Verify damaged cars are actually marked in inventory
        for car_id in damaged:
            car = system["inv"].get_car(car_id)
            assert car["is_damaged"] is True

    def test_damaged_car_from_race_blocks_next_race(self, system):
        """Scenario: Car gets damaged in a race, then can't enter next race.
        Modules: RaceManagement.complete_race → Inventory.damage_car,
                 then RaceManagement.enter_race → Inventory.is_car_available
        Expected: Damaged car is rejected from the next race entry.
        Why needed: Full chain – damage in one race must prevent entry
        in the next, proving both modules share state correctly."""
        did = system["reg"].register_member("Max", "driver")
        cid = system["inv"].add_car("Supra", 250)
        # Manually damage (simulating race damage)
        system["inv"].damage_car(cid)
        rid = system["race"].create_race("Next Race", 1000)
        with pytest.raises(ValueError, match="not available"):
            system["race"].enter_race(rid, did, cid)


# ============================================================
# 3. Results ↔ Race Management + Inventory
#    Call Graph edges:
#      - record_result → RaceManagement.get_race
#      - calculate_prize → RaceManagement.get_race
#      - calculate_prize → Inventory.add_cash
# ============================================================

class TestResultsIntegration:
    """Tests for Results module interacting with Race and Inventory."""

    def test_record_result_validates_race_status(self, system):
        """Scenario: Try to record results for a race that isn't completed.
        Modules: Results.record_result → RaceManagement.get_race
        Expected: ValueError – race is not completed yet.
        Why needed: Results should only be recorded after a race finishes."""
        did = system["reg"].register_member("Max", "driver")
        cid = system["inv"].add_car("Supra", 250)
        rid = system["race"].create_race("Test", 1000)
        system["race"].enter_race(rid, did, cid)
        system["race"].start_race(rid)
        # Race is in_progress, not completed
        with pytest.raises(ValueError, match="not completed"):
            system["results"].record_result(rid, [did])

    def test_race_results_update_inventory_cash(self, system):
        """Scenario: Complete a race, record results, calculate prizes.
        Modules: Results.calculate_prize → RaceManagement.get_race
                 Results.calculate_prize → Inventory.add_cash
        Expected: Prize money is added to the inventory cash balance.
        Why needed: This is a critical business rule – race winnings
        must flow into the crew's shared cash pool."""
        random.seed(99)  # minimize damage for clean test
        d1 = system["reg"].register_member("Max", "driver")
        d2 = system["reg"].register_member("Lewis", "driver")
        c1 = system["inv"].add_car("Car1", 250)
        c2 = system["inv"].add_car("Car2", 240)
        rid = system["race"].create_race("Prize Race", 10000)
        system["race"].enter_race(rid, d1, c1)
        system["race"].enter_race(rid, d2, c2)
        system["race"].start_race(rid)
        system["race"].complete_race(rid)
        cash_before = system["inv"].get_cash()
        system["results"].record_result(rid, [d1, d2])
        payouts = system["results"].calculate_prize(rid)
        cash_after = system["inv"].get_cash()
        # 1st place: 50% of 10000 = 5000, 2nd place: 30% = 3000
        assert payouts[d1] == 5000
        assert payouts[d2] == 3000
        assert cash_after == cash_before + 5000 + 3000

    def test_record_result_validates_driver_was_in_race(self, system):
        """Scenario: Record results with a driver who wasn't in the race.
        Modules: Results.record_result → RaceManagement.get_race
        Expected: ValueError – driver not in race entries.
        Why needed: Prevents fabricated results for non-participants."""
        random.seed(99)
        d1 = system["reg"].register_member("Max", "driver")
        d2 = system["reg"].register_member("Lewis", "driver")
        c1 = system["inv"].add_car("Car1", 250)
        rid = system["race"].create_race("Test", 1000)
        system["race"].enter_race(rid, d1, c1)
        system["race"].start_race(rid)
        system["race"].complete_race(rid)
        with pytest.raises(ValueError, match="not entered"):
            system["results"].record_result(rid, [d2])  # d2 wasn't in race


# ============================================================
# 4. Mission Planning ↔ Registration + Crew Management
#    Call Graph edges:
#      - assign_mission → Registration.is_registered
#      - assign_mission → Registration.get_member (to check roles)
# ============================================================

class TestMissionIntegration:
    """Tests for Mission Planning interacting with Registration and Crew."""

    def test_assign_mission_with_correct_roles(self, system):
        """Scenario: Create a delivery mission needing a driver, assign one.
        Modules: MissionPlanning.assign_mission → Registration.is_registered
                 MissionPlanning.assign_mission → Registration.get_member
        Expected: Mission becomes active.
        Why needed: Validates the happy path where required roles are met."""
        did = system["reg"].register_member("Max", "driver")
        mid = system["missions"].create_mission(
            "Night Delivery", "delivery", ["driver"]
        )
        system["missions"].assign_mission(mid, [did])
        mission = system["missions"].get_mission(mid)
        assert mission["status"] == "active"

    def test_assign_mission_missing_required_role(self, system):
        """Scenario: Mission needs mechanic+driver, only assign a driver.
        Modules: MissionPlanning → Registration.get_member (checks roles)
        Expected: ValueError – mechanic role not covered.
        Why needed: Missions must not start without all required expertise."""
        did = system["reg"].register_member("Max", "driver")
        mid = system["missions"].create_mission(
            "Rescue Op", "rescue", ["driver", "mechanic"]
        )
        with pytest.raises(ValueError, match="roles not covered"):
            system["missions"].assign_mission(mid, [did])

    def test_assign_mission_all_roles_covered(self, system):
        """Scenario: Mission needs driver+mechanic, assign both.
        Modules: MissionPlanning → Registration (validates + reads roles)
        Expected: Mission starts successfully.
        Why needed: Confirms multi-role validation works correctly."""
        did = system["reg"].register_member("Max", "driver")
        mech = system["reg"].register_member("Joe", "mechanic")
        mid = system["missions"].create_mission(
            "Rescue Op", "rescue", ["driver", "mechanic"]
        )
        system["missions"].assign_mission(mid, [did, mech])
        mission = system["missions"].get_mission(mid)
        assert mission["status"] == "active"

    def test_assign_mission_with_unregistered_member(self, system):
        """Scenario: Try to assign an unregistered person to a mission.
        Modules: MissionPlanning.assign_mission → Registration.is_registered
        Expected: ValueError – member not registered.
        Why needed: Prevents assigning non-existent crew to missions."""
        mid = system["missions"].create_mission(
            "Delivery", "delivery", ["driver"]
        )
        with pytest.raises(ValueError, match="not registered"):
            system["missions"].assign_mission(mid, ["fake_id"])


# ============================================================
# 5. Garage ↔ Inventory + Crew Management
#    Call Graph edges:
#      - schedule_repair → Inventory.get_car
#      - schedule_repair → CrewManagement.is_role
#      - complete_repair → Inventory.deduct_cash
#      - complete_repair → Inventory.repair_car
#      - upgrade_car → Inventory.get_car
#      - upgrade_car → Inventory.use_part
# ============================================================

class TestGarageIntegration:
    """Tests for Garage interacting with Inventory and Crew Management."""

    def test_schedule_repair_requires_mechanic_role(self, system):
        """Scenario: Try to schedule a repair with a non-mechanic.
        Modules: Garage.schedule_repair → CrewManagement.is_role
        Expected: ValueError – member is not a mechanic.
        Why needed: Only mechanics should repair cars; a driver doing
        repairs could cause more damage."""
        did = system["reg"].register_member("Max", "driver")
        cid = system["inv"].add_car("Supra", 250)
        system["inv"].damage_car(cid)
        with pytest.raises(ValueError, match="not a mechanic"):
            system["garage"].schedule_repair(cid, did)

    def test_schedule_repair_checks_car_in_inventory(self, system):
        """Scenario: Try to repair a car that doesn't exist.
        Modules: Garage.schedule_repair → Inventory.get_car
        Expected: ValueError – car not found.
        Why needed: Prevents scheduling repairs on phantom cars."""
        mech = system["reg"].register_member("Joe", "mechanic")
        with pytest.raises(ValueError, match="not found"):
            system["garage"].schedule_repair("fake_car", mech)

    def test_complete_repair_deducts_cash_and_fixes_car(self, system):
        """Scenario: Damage a car, schedule repair, complete it.
        Modules: Garage.complete_repair → Inventory.deduct_cash
                 Garage.complete_repair → Inventory.repair_car
        Expected: Cash is reduced by repair cost, car is no longer damaged.
        Why needed: Repair must cost money (affecting inventory cash) AND
        fix the car (affecting inventory car status) – two module updates."""
        mech = system["reg"].register_member("Joe", "mechanic")
        cid = system["inv"].add_car("Supra", 250)
        system["inv"].damage_car(cid)
        cash_before = system["inv"].get_cash()
        system["garage"].schedule_repair(cid, mech)
        system["garage"].complete_repair(cid)
        assert system["inv"].get_car(cid)["is_damaged"] is False
        assert system["inv"].get_cash() == cash_before - 500  # REPAIR_COST

    def test_repair_then_car_can_race_again(self, system):
        """Scenario: Damage car → repair → enter new race.
        Modules: Inventory ↔ Garage ↔ RaceManagement
        Expected: Repaired car is accepted into a new race.
        Why needed: Full chain – damage → repair → re-entry must work
        across three modules sharing car state."""
        did = system["reg"].register_member("Max", "driver")
        mech = system["reg"].register_member("Joe", "mechanic")
        cid = system["inv"].add_car("Supra", 250)
        system["inv"].damage_car(cid)
        system["garage"].schedule_repair(cid, mech)
        system["garage"].complete_repair(cid)
        rid = system["race"].create_race("Comeback Race", 2000)
        system["race"].enter_race(rid, did, cid)  # should succeed
        race = system["race"].get_race(rid)
        assert len(race["entries"]) == 1

    def test_upgrade_car_uses_part_from_inventory(self, system):
        """Scenario: Add a spare part, upgrade a car with it.
        Modules: Garage.upgrade_car → Inventory.get_car
                 Garage.upgrade_car → Inventory.use_part
        Expected: Car speed increases, part count decreases.
        Why needed: Upgrades must consume parts from shared inventory."""
        cid = system["inv"].add_car("Supra", 250)
        system["inv"].add_part("turbo_kit", 2)
        system["garage"].upgrade_car(cid, "turbo_kit", speed_boost=20)
        assert system["inv"].get_car(cid)["top_speed"] == 270
        assert system["inv"].get_part_count("turbo_kit") == 1

    def test_upgrade_fails_without_part(self, system):
        """Scenario: Try to upgrade without the required spare part.
        Modules: Garage.upgrade_car → Inventory.use_part
        Expected: ValueError – part not in stock.
        Why needed: Can't upgrade with parts you don't have."""
        cid = system["inv"].add_car("Supra", 250)
        with pytest.raises(ValueError, match="Not enough"):
            system["garage"].upgrade_car(cid, "turbo_kit", 10)

    def test_upgrade_fails_on_damaged_car(self, system):
        """Scenario: Try to upgrade a damaged car.
        Modules: Garage.upgrade_car → Inventory.get_car
        Expected: ValueError – car is damaged.
        Why needed: Must repair before upgrading."""
        cid = system["inv"].add_car("Supra", 250)
        system["inv"].damage_car(cid)
        system["inv"].add_part("turbo_kit", 1)
        with pytest.raises(ValueError, match="damaged"):
            system["garage"].upgrade_car(cid, "turbo_kit", 10)


# ============================================================
# 6. Leaderboard ↔ Results + Registration
#    Call Graph edges:
#      - get_driver_stats → Registration.get_member
# ============================================================

class TestLeaderboardIntegration:
    """Tests for Leaderboard interacting with Results and Registration."""

    def test_race_results_update_leaderboard(self, system):
        """Scenario: Complete a race, record results, update leaderboard.
        Modules: Results → Leaderboard.update_standings
                 Leaderboard.get_driver_stats → Registration.get_member
        Expected: Winner has 25 points and 1 win in standings.
        Why needed: Race outcomes must propagate to season standings."""
        random.seed(99)
        d1 = system["reg"].register_member("Max", "driver")
        d2 = system["reg"].register_member("Lewis", "driver")
        c1 = system["inv"].add_car("Car1", 250)
        c2 = system["inv"].add_car("Car2", 240)
        rid = system["race"].create_race("GP", 5000)
        system["race"].enter_race(rid, d1, c1)
        system["race"].enter_race(rid, d2, c2)
        system["race"].start_race(rid)
        system["race"].complete_race(rid)
        system["results"].record_result(rid, [d1, d2])
        race_results = system["results"].get_race_results(rid)
        system["lb"].update_standings(race_results)
        # Check leaderboard
        stats = system["lb"].get_driver_stats(d1)
        assert stats["name"] == "Max"
        assert stats["wins"] == 1
        assert stats["points"] == 25

    def test_leaderboard_ranking_order(self, system):
        """Scenario: Two races with different winners, check ranking order.
        Modules: Results → Leaderboard → Registration
        Expected: Driver with more points is ranked higher.
        Why needed: Standings must correctly sort by accumulated points."""
        random.seed(99)
        d1 = system["reg"].register_member("Max", "driver")
        d2 = system["reg"].register_member("Lewis", "driver")
        c1 = system["inv"].add_car("Car1", 250)
        c2 = system["inv"].add_car("Car2", 240)
        # Race 1: Max wins
        r1 = system["race"].create_race("Race 1", 1000)
        system["race"].enter_race(r1, d1, c1)
        system["race"].enter_race(r1, d2, c2)
        system["race"].start_race(r1)
        system["race"].complete_race(r1)
        system["results"].record_result(r1, [d1, d2])
        system["lb"].update_standings(system["results"].get_race_results(r1))
        # Fix any damaged cars for race 2
        for car in system["inv"].list_cars():
            if car["is_damaged"]:
                system["inv"].repair_car(car["id"])
        # Race 2: Max wins again
        r2 = system["race"].create_race("Race 2", 1000)
        system["race"].enter_race(r2, d1, c1)
        system["race"].enter_race(r2, d2, c2)
        system["race"].start_race(r2)
        system["race"].complete_race(r2)
        system["results"].record_result(r2, [d1, d2])
        system["lb"].update_standings(system["results"].get_race_results(r2))
        standings = system["lb"].get_standings()
        # Max should be #1 with 50 points (25+25)
        assert standings[0][0] == d1
        assert standings[0][1]["points"] == 50


# ============================================================
# 7. Full End-to-End Integration
#    All modules working together in realistic scenarios
# ============================================================

class TestFullIntegration:
    """End-to-end tests spanning all modules."""

    def test_full_race_flow(self, system):
        """Scenario: Register → Race → Results → Prize → Leaderboard.
        Modules: ALL (Registration, Crew, Inventory, Race, Results, Leaderboard)
        Expected: Complete flow works end-to-end without errors.
        Why needed: Validates the entire system works as a cohesive unit."""
        random.seed(42)
        # Register drivers
        d1 = system["reg"].register_member("Max", "driver")
        d2 = system["reg"].register_member("Lewis", "driver")
        d3 = system["reg"].register_member("Charles", "driver")
        # Add cars
        c1 = system["inv"].add_car("RB20", 280)
        c2 = system["inv"].add_car("W15", 275)
        c3 = system["inv"].add_car("SF24", 270)
        # Create and run race
        rid = system["race"].create_race("Grand Prix", 9000)
        system["race"].enter_race(rid, d1, c1)
        system["race"].enter_race(rid, d2, c2)
        system["race"].enter_race(rid, d3, c3)
        system["race"].start_race(rid)
        cash_before = system["inv"].get_cash()
        damaged = system["race"].complete_race(rid)
        # Record results
        system["results"].record_result(rid, [d1, d2, d3])
        payouts = system["results"].calculate_prize(rid)
        system["lb"].update_standings(system["results"].get_race_results(rid))
        # Verify payouts: 1st=4500, 2nd=2700, 3rd=1800
        assert payouts[d1] == 4500
        assert payouts[d2] == 2700
        assert payouts[d3] == 1800
        # Verify leaderboard
        standings = system["lb"].get_standings()
        assert standings[0][0] == d1  # Max is #1

    def test_damage_repair_rerace_flow(self, system):
        """Scenario: Race → Car damaged → Repair by mechanic → Race again.
        Modules: Race → Inventory → Garage → Crew → Race (circular flow)
        Expected: Damaged car is repaired and can race again.
        Why needed: Proves the full damage-repair cycle works across
        4 different modules sharing state."""
        did = system["reg"].register_member("Max", "driver")
        mech = system["reg"].register_member("Joe", "mechanic")
        cid = system["inv"].add_car("Supra", 250)
        # Damage the car (simulating race damage)
        system["inv"].damage_car(cid)
        # Can't enter race while damaged
        r1 = system["race"].create_race("Race 1", 1000)
        with pytest.raises(ValueError):
            system["race"].enter_race(r1, did, cid)
        # Repair it
        system["garage"].schedule_repair(cid, mech)
        system["garage"].complete_repair(cid)
        # Now can race again
        r2 = system["race"].create_race("Race 2", 1000)
        system["race"].enter_race(r2, did, cid)
        assert len(system["race"].get_race(r2)["entries"]) == 1

    def test_mission_after_race_damage_needs_mechanic(self, system):
        """Scenario: Car damaged in race → Mission needs mechanic to fix it.
        Modules: Race → Inventory (damage) → Mission (needs mechanic)
                 → Garage (repair)
        Expected: Mission requiring mechanic can be assigned, then
        mechanic repairs the car.
        Why needed: Shows the business rule chain: race damage creates
        a need for a mechanic, which must be validated through missions."""
        did = system["reg"].register_member("Max", "driver")
        mech = system["reg"].register_member("Joe", "mechanic")
        cid = system["inv"].add_car("Supra", 250)
        # Damage the car
        system["inv"].damage_car(cid)
        # Create a repair mission requiring a mechanic
        mid = system["missions"].create_mission(
            "Fix Supra", "rescue", ["mechanic"]
        )
        system["missions"].assign_mission(mid, [mech])
        assert system["missions"].get_mission(mid)["status"] == "active"
        # Mechanic repairs the car
        system["garage"].schedule_repair(cid, mech)
        system["garage"].complete_repair(cid)
        assert system["inv"].get_car(cid)["is_damaged"] is False
        # Complete the mission
        system["missions"].complete_mission(mid)
        assert system["missions"].get_mission(mid)["status"] == "completed"


# ============================================================
# 8. BUG-FINDING TESTS: Results – Double Prize Payout
#    Bug: calculate_prize() has no guard against being called
#    twice on the same race, causing the cash to be added again.
# ============================================================

class TestBugDoublePrizePayout:
    """Tests exposing the double-prize-payout bug in Results."""

    def test_calculate_prize_twice_should_not_double_cash(self, system):
        """Scenario: Call calculate_prize() twice on the same race.
        Modules: Results.calculate_prize → Inventory.add_cash
        Expected: Second call should raise an error or return empty
        (prize already distributed). Cash should NOT increase again.
        Why needed: Without a guard, calling calculate_prize twice
        adds the prize money to inventory twice – an exploit that
        creates infinite money.
        BUG FOUND: calculate_prize() has no idempotency check."""
        random.seed(99)
        d1 = system["reg"].register_member("Max", "driver")
        d2 = system["reg"].register_member("Lewis", "driver")
        c1 = system["inv"].add_car("Car1", 250)
        c2 = system["inv"].add_car("Car2", 240)
        rid = system["race"].create_race("Prize Race", 10000)
        system["race"].enter_race(rid, d1, c1)
        system["race"].enter_race(rid, d2, c2)
        system["race"].start_race(rid)
        system["race"].complete_race(rid)
        system["results"].record_result(rid, [d1, d2])
        # First call – legitimate
        system["results"].calculate_prize(rid)
        cash_after_first = system["inv"].get_cash()
        # Second call – should NOT add more cash
        system["results"].calculate_prize(rid)
        cash_after_second = system["inv"].get_cash()
        assert cash_after_second == cash_after_first, (
            "BUG: calculate_prize() added cash twice! "
            f"After 1st call: ${cash_after_first}, "
            f"after 2nd call: ${cash_after_second}"
        )

    def test_prize_only_distributed_once_total_check(self, system):
        """Scenario: Verify total cash change after two calculate_prize calls.
        Modules: Results → Inventory
        Expected: Total cash increase equals exactly the prize pool (8000).
        Why needed: Ensures the total economic impact is correct.
        BUG FOUND: Same as above – no guard on recalculation."""
        random.seed(99)
        d1 = system["reg"].register_member("Max", "driver")
        d2 = system["reg"].register_member("Lewis", "driver")
        c1 = system["inv"].add_car("Car1", 250)
        c2 = system["inv"].add_car("Car2", 240)
        rid = system["race"].create_race("Cash Race", 10000)
        system["race"].enter_race(rid, d1, c1)
        system["race"].enter_race(rid, d2, c2)
        system["race"].start_race(rid)
        system["race"].complete_race(rid)
        cash_before = system["inv"].get_cash()
        system["results"].record_result(rid, [d1, d2])
        system["results"].calculate_prize(rid)
        system["results"].calculate_prize(rid)  # accidental second call
        cash_after = system["inv"].get_cash()
        expected_total = 5000 + 3000  # 50% + 30% of 10000
        assert cash_after - cash_before == expected_total, (
            f"BUG: Cash increased by ${cash_after - cash_before} "
            f"instead of ${expected_total}"
        )


# ============================================================
# 9. BUG-FINDING TESTS: Inventory – Double Damage
#    Bug: damage_car() does not check if the car is already
#    damaged. Calling it twice reduces condition by 60 instead
#    of 30, and a third call could reduce it to 0.
# ============================================================

class TestBugDoubleDamage:
    """Tests exposing the double-damage bug in Inventory."""

    def test_damage_already_damaged_car_should_not_reduce_condition(self, system):
        """Scenario: Damage a car, then damage it again.
        Modules: Inventory.damage_car (called by RaceManagement)
        Expected: Second damage call should be ignored or raise error.
        Condition should stay at 70 (100 - 30), not drop to 40.
        Why needed: A race that damages an already-damaged car would
        unfairly reduce its condition twice.
        BUG FOUND: damage_car() has no check for is_damaged."""
        cid = system["inv"].add_car("Supra", top_speed=250, condition=100)
        system["inv"].damage_car(cid)
        condition_after_first = system["inv"].get_car(cid)["condition"]
        assert condition_after_first == 70  # 100 - 30
        # Second damage should NOT reduce condition further
        system["inv"].damage_car(cid)
        condition_after_second = system["inv"].get_car(cid)["condition"]
        assert condition_after_second == 70, (
            f"BUG: Condition dropped to {condition_after_second} "
            f"after double damage (expected to stay at 70)"
        )

    def test_damage_car_three_times_condition_should_not_hit_zero(self, system):
        """Scenario: Damage a car three times consecutively.
        Modules: Inventory.damage_car
        Expected: Should not be possible – car is already damaged.
        Why needed: Without a guard, 4 damage calls would set
        condition to max(0, 100-120) = 0, destroying the car.
        BUG FOUND: No is_damaged check before reducing condition."""
        cid = system["inv"].add_car("Supra", top_speed=250, condition=100)
        system["inv"].damage_car(cid)
        system["inv"].damage_car(cid)
        system["inv"].damage_car(cid)
        car = system["inv"].get_car(cid)
        assert car["condition"] >= 70, (
            f"BUG: Condition is {car['condition']} after triple damage "
            f"(should be 70 – only first damage should apply)"
        )


# ============================================================
# 10. BUG-FINDING TESTS: Race – Duplicate Driver Across Races
#     Bug: enter_race() only checks duplicates within the same
#     race, not across multiple open races. A driver could enter
#     two races simultaneously.
# ============================================================

class TestBugDuplicateDriverAcrossRaces:
    """Tests exposing the cross-race duplicate entry bug."""

    def test_driver_should_not_enter_two_open_races(self, system):
        """Scenario: Enter a driver in Race A, then try Race B (both open).
        Modules: RaceManagement.enter_race → Registration, Crew, Inventory
        Expected: Second entry should be rejected – driver already racing.
        Why needed: A driver can't physically be in two races at once.
        BUG FOUND: enter_race() only checks within the same race."""
        did = system["reg"].register_member("Max", "driver")
        c1 = system["inv"].add_car("Car1", 250)
        c2 = system["inv"].add_car("Car2", 240)
        r1 = system["race"].create_race("Race A", 1000)
        r2 = system["race"].create_race("Race B", 2000)
        system["race"].enter_race(r1, did, c1)
        # Should NOT be allowed – Max is already in Race A
        with pytest.raises(ValueError):
            system["race"].enter_race(r2, did, c2)

    def test_car_should_not_enter_two_open_races(self, system):
        """Scenario: Enter a car in Race A, then try Race B with same car.
        Modules: RaceManagement.enter_race → Inventory
        Expected: Second entry should be rejected – car already in use.
        Why needed: One car can't be in two races simultaneously.
        BUG FOUND: enter_race() doesn't check car usage across races."""
        d1 = system["reg"].register_member("Max", "driver")
        d2 = system["reg"].register_member("Lewis", "driver")
        cid = system["inv"].add_car("SharedCar", 250)
        r1 = system["race"].create_race("Race A", 1000)
        r2 = system["race"].create_race("Race B", 2000)
        system["race"].enter_race(r1, d1, cid)
        # Should NOT be allowed – car is already in Race A
        with pytest.raises(ValueError):
            system["race"].enter_race(r2, d2, cid)


# ============================================================
# 11. BUG-FINDING TESTS: Mission Planning – Duplicate Roles
#     Bug: assign_mission() uses set() subtraction to check
#     if required roles are met. If a mission requires 2 of
#     the same role (e.g., ["driver", "driver"]), assigning
#     just 1 driver satisfies the check because
#     {"driver"} - {"driver"} = empty set!
# ============================================================

class TestBugMissionRoleCount:
    """Tests exposing the role counting bug in Mission Planning."""

    def test_mission_requires_multiple_same_role_allows_single(self, system):
        """Scenario: Mission needs 2 mechanics. Assign only 1.
        Modules: MissionPlanning.assign_mission
        Expected: Should be rejected – missing 1 mechanic.
        Why needed: Strict headcount requirements for missions.
        BUG FOUND: assign_mission uses sets, which collapse duplicates."""
        mech = system["reg"].register_member("Joe", "mechanic")
        mid = system["missions"].create_mission(
            "Big Repair", "rescue", ["mechanic", "mechanic"]
        )
        # We only assign ONE mechanic, but it needs TWO
        system["missions"].assign_mission(mid, [mech])
        mission = system["missions"].get_mission(mid)
        # If execution reaches here, the bug exists
        assert len(mission["assigned_members"]) == 2, (
            "BUG: Mission started with 1 mechanic, but required 2! "
            "assign_mission() failed to count duplicates properly due to set()."
        )


# ============================================================
# 12. BUG-FINDING TESTS: Registration – Removing Active Member
#     Bug: remove_member() deletes a member immediately without
#     checking if they are active in races/missions, leaving
#     dangling IDs in other modules.
# ============================================================

class TestBugRemoveActiveMember:
    """Tests exposing stale data bug when removing members."""

    def test_remove_driver_in_active_race_fails_results(self, system):
        """Scenario: Register driver, enter race, remove driver, finish race.
        Modules: Registration.remove_member → Leaderboard
        Expected: Cannot remove active driver, OR race gracefully handles it.
        Why needed: System must maintain referential integrity.
        BUG FOUND: Removing member leaves stale ID in race, breaking leaderboard."""
        did = system["reg"].register_member("Ghost", "driver")
        cid = system["inv"].add_car("Car", 250)
        rid = system["race"].create_race("Spooky GP", 1000)
        system["race"].enter_race(rid, did, cid)
        system["race"].start_race(rid)

        # Remove driver while race is active
        system["reg"].remove_member(did)

        system["race"].complete_race(rid)
        system["results"].record_result(rid, [did])
        race_results = system["results"].get_race_results(rid)

        # Leaderboard tries to get name of deleted member
        system["lb"].update_standings(race_results)
        stats = system["lb"].get_driver_stats(did)

        assert stats["name"] != "Unknown", (
            "BUG: Removed member left stale data! "
            "Leaderboard recorded result for a non-existent member."
        )

