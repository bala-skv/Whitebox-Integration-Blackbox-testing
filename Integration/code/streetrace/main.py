"""StreetRace Manager – Command-line interface.

Ties all modules together and provides an interactive menu.
"""

from registration import Registration
from crew_management import CrewManagement
from inventory import Inventory
from race_management import RaceManagement
from results import Results
from mission_planning import MissionPlanning
from garage import Garage
from leaderboard import Leaderboard


class StreetRaceManager:
    """Facade that wires all modules together."""

    def __init__(self):
        self.registration = Registration()
        self.crew = CrewManagement(self.registration)
        self.inventory = Inventory(starting_cash=10000)
        self.race_mgmt = RaceManagement(
            self.registration, self.crew, self.inventory
        )
        self.results = Results(self.race_mgmt, self.inventory)
        self.missions = MissionPlanning(self.registration, self.crew)
        self.garage = Garage(self.inventory, self.crew)
        self.leaderboard = Leaderboard(self.registration)


def print_menu():
    """Print the main menu."""
    print("\n" + "=" * 50)
    print("       STREETRACE MANAGER")
    print("=" * 50)
    print("1.  Register Crew Member")
    print("2.  List Crew Members")
    print("3.  Assign Role")
    print("4.  Set Skill Level")
    print("5.  Add Car")
    print("6.  List Cars")
    print("7.  Add Cash")
    print("8.  Create Race")
    print("9.  Enter Race")
    print("10. Start & Complete Race")
    print("11. Record Race Results")
    print("12. Create Mission")
    print("13. Assign Mission")
    print("14. Complete Mission")
    print("15. View Missions")
    print("16. Schedule Repair")
    print("17. Complete Repair")
    print("18. Upgrade Car")
    print("19. View Leaderboard")
    print("20. View Inventory")
    print("21. Add Spare Part")
    print("22. View Races")
    print("0.  Exit")
    print("-" * 50)


def main():
    """Main loop for the StreetRace Manager CLI."""
    mgr = StreetRaceManager()
    print("Welcome to StreetRace Manager!")

    while True:
        print_menu()
        choice = input("Enter choice: ").strip()

        try:
            if choice == "1":
                name = input("  Name: ").strip()
                print(f"  Valid roles: {Registration.VALID_ROLES}")
                role = input("  Role: ").strip()
                mid = mgr.registration.register_member(name, role)
                print(f"  ✓ Registered '{name}' as {role} (ID: {mid})")

            elif choice == "2":
                members = mgr.registration.list_members()
                if not members:
                    print("  No members registered.")
                for m in members:
                    skill = mgr.crew.get_skill_level(m["id"])
                    print(
                        f"  [{m['id']}] {m['name']} "
                        f"– {m['role']} (skill: {skill}) "
                        f"| Cash: ${mgr.inventory.get_cash()}"
                    )

            elif choice == "3":
                mid = input("  Member ID: ").strip()
                role = input("  New role: ").strip()
                mgr.crew.assign_role(mid, role)
                print(f"  ✓ Role updated to '{role}'.")

            elif choice == "4":
                mid = input("  Member ID: ").strip()
                level = int(input("  Skill level (1-10): ").strip())
                mgr.crew.set_skill_level(mid, level)
                print(f"  ✓ Skill level set to {level}.")

            elif choice == "5":
                name = input("  Car name: ").strip()
                speed = int(input("  Top speed: ").strip())
                cid = mgr.inventory.add_car(name, top_speed=speed)
                print(f"  ✓ Added car '{name}' (ID: {cid})")

            elif choice == "6":
                cars = mgr.inventory.list_cars()
                if not cars:
                    print("  No cars in inventory.")
                for c in cars:
                    status = "DAMAGED" if c["is_damaged"] else "OK"
                    print(
                        f"  [{c['id']}] {c['name']} "
                        f"– {c['top_speed']}mph, cond:{c['condition']}, "
                        f"{status}"
                    )

            elif choice == "7":
                amount = int(input("  Amount to add: ").strip())
                mgr.inventory.add_cash(amount)
                print(f"  ✓ Cash balance: ${mgr.inventory.get_cash()}")

            elif choice == "8":
                name = input("  Race name: ").strip()
                prize = int(input("  Prize money: ").strip())
                rid = mgr.race_mgmt.create_race(name, prize)
                print(f"  ✓ Created race '{name}' (ID: {rid})")

            elif choice == "9":
                rid = input("  Race ID: ").strip()
                did = input("  Driver ID: ").strip()
                cid = input("  Car ID: ").strip()
                mgr.race_mgmt.enter_race(rid, did, cid)
                print("  ✓ Entry added to race.")

            elif choice == "10":
                rid = input("  Race ID: ").strip()
                mgr.race_mgmt.start_race(rid)
                print("  Race started!")
                damaged = mgr.race_mgmt.complete_race(rid)
                print("  Race completed!")
                if damaged:
                    for car_id in damaged:
                        car = mgr.inventory.get_car(car_id)
                        car_name = car["name"] if car else car_id
                        print(f"  ⚠ Car '{car_name}' was DAMAGED in the race!")
                else:
                    print("  All cars survived unscathed!")

            elif choice == "11":
                rid = input("  Race ID: ").strip()
                race = mgr.race_mgmt.get_race(rid)
                if race is None:
                    print("  Race not found.")
                    continue
                print("  Enter driver IDs in finishing order (comma-sep):")
                order = input("  ").strip().split(",")
                order = [d.strip() for d in order]
                mgr.results.record_result(rid, order)
                payouts = mgr.results.calculate_prize(rid)
                race_results = mgr.results.get_race_results(rid)
                mgr.leaderboard.update_standings(race_results)
                print("  ✓ Results recorded. Payouts:")
                for did, amt in payouts.items():
                    print(f"    {did}: ${amt}")
                print(f"  Cash balance: ${mgr.inventory.get_cash()}")

            elif choice == "12":
                name = input("  Mission name: ").strip()
                mtype = input(
                    "  Type (delivery/rescue/escort/sabotage/recon): "
                ).strip()
                roles = input("  Required roles (comma-sep): ").strip()
                roles = [r.strip() for r in roles.split(",")]
                mid = mgr.missions.create_mission(name, mtype, roles)
                print(f"  ✓ Mission created (ID: {mid})")

            elif choice == "13":
                mid = input("  Mission ID: ").strip()
                members = input("  Member IDs (comma-sep): ").strip()
                members = [m.strip() for m in members.split(",")]
                mgr.missions.assign_mission(mid, members)
                print("  ✓ Mission assigned and active.")

            elif choice == "14":
                mid = input("  Mission ID: ").strip()
                mgr.missions.complete_mission(mid)
                print("  ✓ Mission completed.")

            elif choice == "15":
                missions = mgr.missions.list_missions()
                if not missions:
                    print("  No missions created.")
                for ms in missions:
                    members_str = ", ".join(
                        ms["assigned_members"]
                    ) if ms["assigned_members"] else "none"
                    print(
                        f"  [{ms['id']}] {ms['name']} "
                        f"({ms['type']}) – {ms['status']} "
                        f"| Roles: {ms['required_roles']} "
                        f"| Crew: {members_str}"
                    )

            elif choice == "16":
                cid = input("  Car ID: ").strip()
                mid = input("  Mechanic ID: ").strip()
                mgr.garage.schedule_repair(cid, mid)
                print("  ✓ Repair scheduled.")

            elif choice == "17":
                cid = input("  Car ID: ").strip()
                mgr.garage.complete_repair(cid)
                print(
                    f"  ✓ Repair complete. "
                    f"Cash: ${mgr.inventory.get_cash()}"
                )

            elif choice == "18":
                cid = input("  Car ID: ").strip()
                pname = input("  Part name: ").strip()
                boost = int(input("  Speed boost: ").strip())
                mgr.garage.upgrade_car(cid, pname, boost)
                print("  ✓ Car upgraded.")

            elif choice == "19":
                standings = mgr.leaderboard.get_standings()
                if not standings:
                    print("  No standings yet.")
                for rank, (did, stats) in enumerate(standings, 1):
                    member = mgr.registration.get_member(did)
                    name = member["name"] if member else did
                    streak = mgr.leaderboard.get_streak(did)
                    print(
                        f"  #{rank} {name} – "
                        f"{stats['points']}pts, "
                        f"{stats['wins']}W {stats['podiums']}P "
                        f"({stats['races']} races) "
                        f"| streak: {streak['type']}x{streak['count']}"
                    )

            elif choice == "20":
                print(f"  Cash: ${mgr.inventory.get_cash()}")
                parts = mgr.inventory._parts
                tools = mgr.inventory._tools
                if parts:
                    print("  Parts:", dict(parts))
                else:
                    print("  Parts: none")
                if tools:
                    print("  Tools:", dict(tools))
                else:
                    print("  Tools: none")

            elif choice == "21":
                name = input("  Part name: ").strip()
                qty = int(input("  Quantity: ").strip())
                mgr.inventory.add_part(name, qty)
                print(f"  ✓ Added {qty}x {name}.")

            elif choice == "22":
                races = mgr.race_mgmt.list_races()
                if not races:
                    print("  No races created.")
                for r in races:
                    entries_count = len(r["entries"])
                    print(
                        f"  [{r['id']}] {r['name']} "
                        f"– ${r['prize_money']} prize "
                        f"| {r['status']} "
                        f"| {entries_count} entries"
                    )

            elif choice == "0":
                print("Goodbye!")
                break

            else:
                print("  Invalid choice.")

        except ValueError as e:
            print(f"  ✗ Error: {e}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
