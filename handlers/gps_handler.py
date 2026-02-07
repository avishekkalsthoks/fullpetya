"""
GPS Handler for Smart Vision Guide.
Provides GPS-based navigation and emergency help features for Raspberry Pi.

Features:
- Navigation Mode: Turn-by-turn audio guidance to home using OSRM routing
- Ask Help Mode: Send emergency location to relatives via ntfy.sh

GPS is obtained from the Phyphox app running on a smartphone connected via WiFi hotspot.

Requires: requests (pip install requests)
"""

import os
import time
import math
import threading
import requests


class GPSHandler:
    """Handler for GPS-based navigation and emergency help features."""

    def __init__(self, audio_handler, phyphox_url, home_lat, home_lon,
                 ntfy_topic, relatives=None, check_interval=2.0):
        """
        Initialize GPS handler.

        Args:
            audio_handler: AudioHandler instance for TTS
            phyphox_url: URL to Phyphox GPS endpoint (e.g., http://192.168.1.108:8080/get?lat&lon&v)
            home_lat: Home latitude
            home_lon: Home longitude
            ntfy_topic: ntfy.sh topic for notifications
            relatives: List of relative names for notification messages
            check_interval: GPS check interval in seconds
        """
        self.audio = audio_handler
        self.phyphox_url = phyphox_url
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.ntfy_topic = ntfy_topic
        self.ntfy_url = f"https://ntfy.sh/{ntfy_topic}"
        self.relatives = relatives or []
        self.check_interval = check_interval

        # Navigation state
        self.navigation_active = False
        self._stop_navigation = threading.Event()

        print(f"✓ GPS Handler initialized")
        print(f"  Phyphox URL: {phyphox_url}")
        print(f"  Home: {home_lat}, {home_lon}")
        print(f"  ntfy topic: {ntfy_topic}")

    def _safe_beep(self, beep_type='start'):
        """Play beep if audio handler supports it, otherwise skip."""
        try:
            if hasattr(self.audio, 'play_beep'):
                self.audio.play_beep(beep_type)
        except Exception:
            pass  # Beep is optional, don't fail navigation

    # ======================== GPS HELPERS ========================

    def fetch_gps(self):
        """Fetch lat/lon from Phyphox server."""
        try:
            data = requests.get(self.phyphox_url, timeout=5).json()
            buf = data["buffer"]
            lat = buf["lat"]["buffer"]
            lon = buf["lon"]["buffer"]
            if lat and lon:
                return lat[-1], lon[-1]
        except requests.exceptions.Timeout:
            print("GPS Error: Phyphox connection timeout")
        except requests.exceptions.ConnectionError:
            print("GPS Error: Cannot connect to Phyphox. Check WiFi hotspot.")
        except Exception as e:
            print(f"GPS Error: {e}")
        return None, None

    def haversine(self, lat1, lon1, lat2, lon2):
        """Distance between two GPS points in km."""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def bearing(self, lat1, lon1, lat2, lon2):
        """Bearing from point 1 to point 2 in degrees."""
        dlon = math.radians(lon2 - lon1)
        lat1, lat2 = math.radians(lat1), math.radians(lat2)
        x = math.sin(dlon) * math.cos(lat2)
        y = (math.cos(lat1) * math.sin(lat2) -
             math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
        deg = math.degrees(math.atan2(x, y))
        return (deg + 360) % 360

    def compass_direction(self, deg):
        """Convert bearing degrees to compass direction."""
        dirs = ["north", "northeast", "east", "southeast",
                "south", "southwest", "west", "northwest"]
        return dirs[round(deg / 45) % 8]

    def format_distance(self, meters):
        """Format distance for visually impaired — use walking time + meters."""
        if meters < 20:
            return "a few steps"
        elif meters < 50:
            return f"{int(meters)} meters, about half a minute walk"
        elif meters < 100:
            return f"{int(round(meters / 10) * 10)} meters, about 1 minute walk"
        elif meters < 1000:
            mins = max(1, int(meters / 80))  # ~80m per minute walking
            rounded = int(round(meters / 10) * 10)
            return f"{rounded} meters, about {mins} minutes walk"
        else:
            km = meters / 1000
            mins = max(1, int(meters / 80))
            return f"{km:.1f} kilometers, about {mins} minutes walk"

    def google_maps_link(self, lat, lon):
        """Generate Google Maps link."""
        return f"https://www.google.com/maps?q={lat},{lon}"

    def reverse_geocode(self, lat, lon):
        """Convert lat/lon to a place name using OpenStreetMap Nominatim (free)."""
        try:
            url = (f"https://nominatim.openstreetmap.org/reverse"
                   f"?lat={lat}&lon={lon}&format=json&zoom=18&accept-language=en")
            r = requests.get(url, headers={"User-Agent": "SmartVisionGuide/1.0"}, timeout=10)
            data = r.json()
            return data.get("display_name", "Unknown location")
        except Exception as e:
            print(f"Geocoding error: {e}")
            return "Unknown location"

    # ======================== ROUTING ENGINE ========================

    def get_route(self, from_lat, from_lon, to_lat, to_lon):
        """Get turn-by-turn route from OSRM (free, no API key needed)."""
        url = (
            f"http://router.project-osrm.org/route/v1/foot/"
            f"{from_lon},{from_lat};{to_lon},{to_lat}"
            f"?overview=full&steps=true&geometries=geojson"
        )
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if data["code"] != "Ok":
                print(f"Routing error: {data.get('message', 'unknown')}")
                return None
            return data["routes"][0]
        except Exception as e:
            print(f"Route fetch error: {e}")
            return None

    def parse_steps(self, route):
        """Parse OSRM route into navigation steps."""
        steps = []
        for leg in route["legs"]:
            for step in leg["steps"]:
                maneuver = step["maneuver"]
                coords = step["geometry"]["coordinates"]  # [lon, lat] pairs
                start_lon, start_lat = coords[0]
                end_lon, end_lat = coords[-1]

                modifier = maneuver.get("modifier", "")
                mtype = maneuver.get("type", "")

                if mtype == "depart":
                    road = step.get("name", "")
                    instruction = f"Head {modifier}" + (f" on {road}" if road else "")
                elif mtype == "arrive":
                    instruction = "You have arrived at your destination"
                elif mtype == "turn":
                    road = step.get("name", "")
                    instruction = f"Turn {modifier}" + (f" onto {road}" if road else "")
                elif mtype == "new name":
                    road = step.get("name", "")
                    instruction = f"Continue onto {road}" if road else "Continue straight"
                elif mtype == "end of road":
                    instruction = f"At the end of the road, turn {modifier}"
                elif mtype == "fork":
                    instruction = f"At the fork, keep {modifier}"
                elif mtype == "roundabout":
                    road = step.get("name", "")
                    instruction = f"Enter roundabout, take exit" + (f" onto {road}" if road else "")
                elif mtype == "merge":
                    instruction = f"Merge {modifier}"
                elif mtype == "continue":
                    road = step.get("name", "")
                    instruction = f"Continue {modifier}" + (f" on {road}" if road else "")
                else:
                    road = step.get("name", "")
                    instruction = f"{mtype} {modifier}" + (f" on {road}" if road else "")

                steps.append({
                    "instruction": instruction.strip(),
                    "distance": step["distance"],
                    "duration": step["duration"],
                    "lat": start_lat,
                    "lon": start_lon,
                    "end_lat": end_lat,
                    "end_lon": end_lon,
                })
        return steps

    # ======================== NAVIGATION MODE ========================

    def start_navigation(self):
        """Start navigation to home (runs synchronously, caller should use thread)."""
        if self.navigation_active:
            self.audio.say("Navigation is already running.")
            return

        self._stop_navigation.clear()
        self.navigation_active = True
        self._navigation_loop()  # Run synchronously - caller creates thread

    def stop_navigation(self):
        """Stop navigation."""
        if self.navigation_active:
            self._stop_navigation.set()
            self.navigation_active = False
            self.audio.say("Navigation stopped.")

    def _navigation_loop(self):
        """Main navigation loop with turn-by-turn audio guidance."""
        try:
            self.audio.say("Starting navigation to home. Please wait while I find the best route.")

            # Get initial GPS fix
            lat, lon = self.fetch_gps()
            if not lat or not lon:
                self.audio.say("I cannot get your location right now. Please make sure Phyphox is running on your phone.")
                # Retry a few times
                for i in range(5):
                    if self._stop_navigation.is_set():
                        return
                    time.sleep(3)
                    self.audio.say(f"Trying again. Attempt {i + 2}.")
                    lat, lon = self.fetch_gps()
                    if lat and lon:
                        break
                else:
                    self.audio.say("Still no GPS signal. Please check your phone and try again.")
                    self.navigation_active = False
                    return

            # Get route
            route = self.get_route(lat, lon, self.home_lat, self.home_lon)
            if not route:
                self.audio.say("I could not find a walking route. I will guide you using compass direction instead.")
                self._basic_guide()
                return

            total_dist = route["distance"]
            steps = self.parse_steps(route)

            if not steps:
                self.audio.say("No route steps found. Using compass guidance instead.")
                self._basic_guide()
                return

            # Announce route summary
            self.audio.say(f"Route found! Your home is {self.format_distance(total_dist)} away. "
                          f"I will guide you step by step. Let's go!")
            time.sleep(1)

            current_step = 0
            announced_upcoming = False
            announced_now = False
            last_reroute_time = 0
            last_reassurance_time = time.time()
            last_progress_time = time.time()

            REASSURANCE_INTERVAL = 15   # "you're on track" every 15 seconds
            PROGRESS_INTERVAL = 30      # distance update every 30 seconds

            while current_step < len(steps) and not self._stop_navigation.is_set():
                lat, lon = self.fetch_gps()
                if not lat or not lon:
                    self.audio.say("I lost your GPS signal. Please keep your phone in an open area.")
                    time.sleep(3)
                    continue

                step = steps[current_step]
                next_step = steps[current_step + 1] if current_step + 1 < len(steps) else None

                dist_to_step = self.haversine(lat, lon, step["lat"], step["lon"]) * 1000
                dist_to_end = self.haversine(lat, lon, step["end_lat"], step["end_lon"]) * 1000
                dist_home = self.haversine(lat, lon, self.home_lat, self.home_lon) * 1000

                # ===== ARRIVED HOME =====
                if dist_home < 30:
                    self._safe_beep('success')
                    self.audio.say("You have arrived home! You made it safely!")
                    time.sleep(1)
                    self.audio.say("You have arrived home!")
                    print("\n  You have arrived home!")
                    break

                # ===== PASSED THIS STEP =====
                if dist_to_end < 20 or (next_step and self.haversine(lat, lon, next_step["lat"], next_step["lon"]) * 1000 < 30):
                    current_step += 1
                    announced_upcoming = False
                    announced_now = False
                    last_reassurance_time = time.time()
                    continue

                # ===== OFF-ROUTE DETECTION =====
                if dist_to_step > 80 and dist_to_end > 80:
                    now = time.time()
                    if now - last_reroute_time > 25:
                        self._safe_beep('error')
                        self.audio.say("You seem to have gone off the route. "
                                      "Don't worry, I am recalculating a new route for you.")
                        route = self.get_route(lat, lon, self.home_lat, self.home_lon)
                        if route:
                            steps = self.parse_steps(route)
                            current_step = 0
                            announced_upcoming = False
                            announced_now = False
                            new_dist = route["distance"]
                            self.audio.say(f"New route found. Home is now {self.format_distance(new_dist)} away.")
                        else:
                            self.audio.say("I could not find a new route. Switching to compass guidance.")
                            self._basic_guide()
                            return
                        last_reroute_time = now
                        last_reassurance_time = now
                        continue

                # Distance to the next turn
                if next_step:
                    dist_to_turn = self.haversine(lat, lon, next_step["lat"], next_step["lon"]) * 1000
                else:
                    dist_to_turn = dist_home

                # ===== CURRENT STEP — announce once =====
                if not announced_now:
                    self.audio.say(f"Step {current_step + 1}. {step['instruction']}. "
                                  f"Walk for {self.format_distance(step['distance'])}.")
                    print(f"  Step {current_step + 1}: {step['instruction']}")
                    announced_now = True
                    last_reassurance_time = time.time()
                    last_progress_time = time.time()

                # ===== UPCOMING TURN — warn at 80m =====
                if next_step and dist_to_turn < 80 and not announced_upcoming:
                    self._safe_beep('click')
                    self.audio.say(f"Heads up! In {self.format_distance(dist_to_turn)}, "
                                  f"you will need to {next_step['instruction']}.")
                    announced_upcoming = True
                    last_reassurance_time = time.time()

                # ===== TURN NOW — at 25m =====
                if next_step and dist_to_turn < 25 and announced_upcoming:
                    self._safe_beep('click')
                    self.audio.say(f"Now! {next_step['instruction']}.")
                    current_step += 1
                    announced_upcoming = False
                    announced_now = False
                    last_reassurance_time = time.time()
                    continue

                # ===== PERIODIC REASSURANCE =====
                now = time.time()
                if now - last_reassurance_time > REASSURANCE_INTERVAL:
                    self.audio.say("You are on track. Keep walking.")
                    last_reassurance_time = now

                # ===== PERIODIC PROGRESS UPDATE =====
                if now - last_progress_time > PROGRESS_INTERVAL:
                    home_bear = self.bearing(lat, lon, self.home_lat, self.home_lon)
                    direction = self.compass_direction(home_bear)
                    self.audio.say(f"Home is {self.format_distance(dist_home)} to the {direction}. "
                                  f"Step {current_step + 1} of {len(steps)}.")
                    last_progress_time = now

                # Status line
                remaining = self.format_distance(dist_home)
                step_info = step["instruction"][:40]
                print(f"  Step {current_step+1}/{len(steps)} | {step_info:<40} | Home: {remaining}", end="\r")

                time.sleep(self.check_interval)

        except Exception as e:
            print(f"Navigation error: {e}")
            self.audio.say("Navigation encountered an error. Please try again.")
        finally:
            self.navigation_active = False

    def _basic_guide(self):
        """Fallback compass guidance when OSRM unavailable."""
        self.audio.say("I will guide you using compass direction. "
                      "Keep walking and I will tell you which way to go.")
        update_count = 0

        while not self._stop_navigation.is_set():
            lat, lon = self.fetch_gps()
            if lat and lon:
                dist = self.haversine(lat, lon, self.home_lat, self.home_lon)
                home_bear = self.bearing(lat, lon, self.home_lat, self.home_lon)
                direction = self.compass_direction(home_bear)

                if dist < 0.03:
                    self._safe_beep('success')
                    self.audio.say("You have arrived home! Well done!")
                    time.sleep(1)
                    self.audio.say("You have arrived home!")
                    break

                meters = int(dist * 1000)
                msg = f"Home is {self.format_distance(meters)} to the {direction}."

                if update_count % 3 == 0:
                    msg = f"You are on track. {msg}"

                self.audio.say(msg)
                update_count += 1
            else:
                self.audio.say("Waiting for GPS signal. Please keep your phone nearby.")

            time.sleep(4)

        self.navigation_active = False

    # ======================== ASK HELP MODE (NTFY) ========================

    def send_help(self):
        """Send emergency help notification with current location via ntfy.sh."""
        self.audio.say("Sending help request. Please wait.")

        lat, lon = self.fetch_gps()
        if not lat or not lon:
            # Retry a few times
            for _ in range(3):
                time.sleep(2)
                lat, lon = self.fetch_gps()
                if lat and lon:
                    break

        if not lat or not lon:
            self.audio.say("I cannot get your location. Please check Phyphox is running.")
            return False

        try:
            link = self.google_maps_link(lat, lon)
            place = self.reverse_geocode(lat, lon)
            names = ", ".join(self.relatives) if self.relatives else "Emergency contacts"

            message = (
                f"USER NEEDS HELP!\n\n"
                f"Location: {place}\n\n"
                f"Latitude: {lat:.6f}\n"
                f"Longitude: {lon:.6f}\n"
                f"Time: {time.strftime('%H:%M:%S')}\n\n"
                f"Google Maps: {link}\n\n"
                f"Please check on them immediately!"
            )

            r = requests.post(
                self.ntfy_url,
                headers={
                    "Title": "SOS EMERGENCY ALERT",
                    "Priority": "urgent",
                    "Tags": "rotating_light,sos,warning",
                },
                data=message.encode("utf-8"),
                timeout=10,
            )

            if r.ok:
                print(f"SOS sent to ntfy topic: {self.ntfy_topic}")
                self.audio.say(f"Help request sent successfully. Your relatives have been notified.")
                return True
            else:
                print(f"ntfy error: {r.status_code} {r.text}")
                self.audio.say("Failed to send help request. Please try again.")
                return False

        except Exception as e:
            print(f"Help request error: {e}")
            self.audio.say("Failed to send help request. Please check internet connection.")
            return False

    def share_location(self, reason="Location Update"):
        """Share current location with relatives via ntfy.sh."""
        self.audio.say("Sharing your location.")

        lat, lon = self.fetch_gps()
        if not lat or not lon:
            self.audio.say("Cannot get your location. Please check Phyphox.")
            return False

        try:
            link = self.google_maps_link(lat, lon)
            place = self.reverse_geocode(lat, lon)
            names = ", ".join(self.relatives) if self.relatives else "Contacts"

            message = (
                f"Current Location: {place}\n\n"
                f"Latitude: {lat:.6f}\n"
                f"Longitude: {lon:.6f}\n"
                f"Time: {time.strftime('%H:%M:%S')}\n\n"
                f"Google Maps: {link}\n\n"
                f"Shared with: {names}"
            )

            r = requests.post(
                self.ntfy_url,
                headers={
                    "Title": reason,
                    "Priority": "default",
                    "Tags": "round_pushpin",
                },
                data=message.encode("utf-8"),
                timeout=10,
            )

            if r.ok:
                self.audio.say("Location shared successfully.")
                return True
            else:
                self.audio.say("Failed to share location.")
                return False

        except Exception as e:
            print(f"Share location error: {e}")
            self.audio.say("Failed to share location. Please check internet.")
            return False

    def get_distance_to_home(self):
        """Get and announce distance to home."""
        lat, lon = self.fetch_gps()
        if not lat or not lon:
            self.audio.say("Cannot get your location.")
            return None

        dist = self.haversine(lat, lon, self.home_lat, self.home_lon)
        bear = self.bearing(lat, lon, self.home_lat, self.home_lon)
        direction = self.compass_direction(bear)

        if dist < 0.05:
            self.audio.say("You are home.")
        elif dist < 0.5:
            self.audio.say(f"Home is {int(dist * 1000)} meters to the {direction}.")
        else:
            self.audio.say(f"Home is {dist:.1f} kilometers to the {direction}.")

        return dist

    def cleanup(self):
        """Cleanup GPS handler."""
        self.stop_navigation()
