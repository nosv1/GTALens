import json
import logging
from datetime import datetime
from difflib import get_close_matches
import requests

ALIASES = ["car", "truck", "vehicle"]


class Vehicle:
    def __init__(
            self,
            name: str = None,
            vehicle_class: str = None,
            drivetrain: str = None,
            seats: str = None,
            manufacturer: str = None,
            race_tier: str = None,
            spoiler: str = None,
            off_roads: str = None,
            suspension: str = None,
            boost: str = None,
            drift_tyres: str = None,
            source: str = None,
            cost: str = None,
            storage: str = None,
            upgrade: str = None,
            date_added: datetime = None,
            dlc: str = None,
            other_notes: str = None,
            engine_stock: float = None,
            level_4_upgrade: int = None,
            engine_max: float = None,
            drag: float = None,
            max_speed: float = None,
            power_to_front: int = None,  # as %, so 100% is 100
            gears: int = None,
            upshift_rate: float = None,
            downshift_rate: float = None,
            brake_force: float = None,
            brake_bias: float = None,
            cornering_grip: float = None,
            straight_line_grip: float = None,
            off_road_grip_loss: float = None,
            weight_kg: int = None,
            flags_bouncy: str = None,
            flags_engine: str = None,
            pos_overall: int = None,
            pos_class: int = None,
            lap_time: str = None,  # m:ss.000
            top_speed_mph: float = None
    ):
        self.name = name
        self.vehicle_class = vehicle_class

        # Key Attributes
        self.drivetrain = drivetrain
        self.seats = seats
        self.manufacturer = manufacturer
        self.race_tier = race_tier

        # Performance Improvements
        self.spoiler = spoiler
        self.off_roads = off_roads
        self.suspension = suspension
        self.boost = boost
        self.drift_tyres = drift_tyres

        # Buying, Storing, & Upgrading
        self.source = source
        self.cost = cost
        self.storage = storage
        self.upgrade = upgrade

        # Added to GTA Online
        self.date_added = date_added
        self.dlc = dlc

        self.other_notes = other_notes

        # Speed
        self.engine_stock = engine_stock
        self.level_4_upgrade = level_4_upgrade
        self.engine_max = engine_max  # = stock + (stock * lvl4 * .0002)
        self.drag = drag
        self.max_speed = max_speed

        # Acceleration
        self.power_to_front = power_to_front
        self.gears = gears
        self.upshift_rate = upshift_rate
        self.downshift_rate = downshift_rate

        # Braking
        self.brake_force = brake_force
        self.brake_bias = brake_bias

        # Traction
        self.cornering_grip = cornering_grip
        self.straight_line_grip = straight_line_grip
        self.off_road_grip_loss = off_road_grip_loss

        # Collisions
        self.weight_kg = weight_kg

        # AH Flag Issues
        self.flags_bouncy = flags_bouncy
        self.flags_engine = flags_engine

        self.pos_overall = pos_overall
        self.pos_class = pos_class
        self.lap_time = lap_time
        self.top_speed_mph = top_speed_mph


def get_vehicle(name: str) -> Vehicle:
    vehicles = get_vehicles()

    if not vehicles:  # get_vehicles() failed
        logging.info("vehicles.get_vehicles failed")
        # TODO error message
        return

    vehicle_names = vehicles.keys()
    poss_vehicles = get_close_matches(name.lower(), [v.lower() for v in vehicle_names])

    for i, pv in enumerate(poss_vehicles):  # fix vehicle names to be proper
        for v in vehicle_names:
            if pv == v.lower():
                poss_vehicles[i] = vehicles[v]

    # TODO ... the rest, currently have a list of vehicles that are close matches


def update_vehicles():
    vehicles = {}

    page = 1
    vehicle_count = 0
    do_loop = True
    while do_loop:
        response = requests.get("https://gtalens.com/api/v1/vehicles", params={
            "page": page, "sorting": 'alphabet'
        })
        response_dict = json.loads(response.text)
        vehicle_list_len = len()

        if response_dict['success']:
            for vehicle in response_dict['payload']['vehicles']:
                print(vehicle['meta']['name'])
                vehicles.update({vehicle['meta']['name']: vehicle})
                vehicle_count += 1

                if vehicle_count == response_dict['payload']['vehiclesCountTotal']:
                    json.dump(vehicles, open("vehicles.json", "w"), indent=4)
                    do_loop = False
                    break

        else:
            logging.info("Update vehicles failed")
            break

        page += 1


update_vehicles()

