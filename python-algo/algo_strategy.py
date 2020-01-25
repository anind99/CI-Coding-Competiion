import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER, BITS, CORES
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        BITS = 1
        CORES = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.sent_emp = False

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def strategy(self, game_state):
        # Place basic defences
        self.build_basic_defences(game_state)
        # Place basic units
        self.offence(game_state)
        # Place advnaced units
        self.simple_additional_defence(game_state)
        # Place additional encryptors
        self.add_encryptor(game_state)

    def build_basic_defences(self, game_state):
        # Build the main encryptor
        main_encryptor = [[14, 1]]
        game_state.attempt_spawn(ENCRYPTOR, main_encryptor)
        # After the first turn check for the main wall placements and main cannon placements
        if game_state.turn_number >= 1:

            main_destructor = [[27, 13], [24, 12], [22, 11]]
            game_state.attempt_spawn(DESTRUCTOR, main_destructor)

            main_filters = [[0, 13], [26, 13], [1, 12], [22, 12], [23, 12], [2, 11], [21, 11], [3, 10], [20, 10], [4, 9], [19, 9], [5, 8], [18, 8], [6, 7], [17, 7], [7, 6], [16, 6], [8, 5], [15, 5], [9, 4], [14, 4], [10, 3], [13, 3], [11, 2], [12, 2]]
            game_state.attempt_spawn(FILTER, main_filters)

    def simple_additional_defence(self, game_state):
        if game_state.turn_number >= 1:
            additional_destructors = [[21, 12], [26, 12], [19, 11], [20, 11], [23, 11], [19, 10]]
            for spot in additional_destructors:
                game_state.attempt_spawn(DESTRUCTOR, spot)
            additional_filter = [[17, 12], [18, 12], [19, 12], [20, 12], [17, 11], [18, 11], [18, 10]]
            for spot in additional_filter:
                game_state.attempt_spawn(FILTER, spot)

    def add_encryptor(self, game_state):
        if game_state.turn_number >= 1:
            additional_encryptors = [[19, 6], [20, 6], [18, 5], [19, 5], [17, 4], [18, 4], [16, 3], [17, 3], [15, 2], [16, 2], [15, 1]]
            for spot in additional_encryptors:
                game_state.attempt_spawn(ENCRYPTOR, spot)
    
    def offence(self, game_state):
        attack_pos = [[13,0]]
        if game_state.turn_number == 0:
            while game_state.can_spawn(PING, attack_pos[0], 1):
                game_state.attempt_spawn(PING, attack_pos)
        # check number of bits, save for 4 emp then spam pings repeat
        if not self.sent_emp:
            # wait till num bits > 12
            if game_state.get_resource(BITS) >= 21:
                while game_state.can_spawn(EMP, attack_pos[0]):
                    game_state.attempt_spawn(EMP, attack_pos[0])
                self.sent_emp = True
        else:
            if self.sent_emp and game_state.get_resource(BITS) >= 16:
                while game_state.can_spawn(PING, attack_pos[0], 1):
                    game_state.attempt_spawn(PING, attack_pos[0])
                self.sent_emp = False

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build destructor one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(DESTRUCTOR, build_location)

    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own firewalls 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining bits to spend lets send out scramblers randomly.
        while game_state.get_resource(BITS) >= game_state.type_cost(SCRAMBLER)[BITS] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            """
            We don't have to remove the location since multiple information 
            units can occupy the same space.
            """

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.BITS] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.BITS]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
