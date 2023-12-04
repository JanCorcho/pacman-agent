
import random
import contest.util as util
import time
from contest.captureAgents import CaptureAgent
from contest.game import Directions,Actions
from contest.util import nearestPoint

#################
# Team creation #
#################
def create_team(firstIndex, secondIndex, isRed, first='AStarOfTheShow', second='AStarOfTheShow'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]

##########
# Agents #
##########


class AStarOfTheShow(CaptureAgent):
    class Mode:
        Attack = 0
        Defend = 1
        Retreat = 2

    def __init__(self, index, time_for_computing=.1):
        super().__init__(index, time_for_computing)
        self.start = None
        
    def register_initial_state(self, game_state):
        self.start = game_state.get_agent_position(self.index)
        CaptureAgent.register_initial_state(self, game_state)
        self.initial_food = self.food_in_state(game_state)
        self.width = game_state.data.layout.width
        self.width_half = self.width/2
        self.height = game_state.data.layout.height
        self.height_half = self.height/2
        self.safe_zone = self.safe_zone_limit(game_state)
        self.mode = self.Mode.Attack
        

    def food_in_state(self,game_state):
        return len(self.get_food(game_state).as_list())
    
    def DecisionTree(self,game_state):
        Agent2 = self.get_team(game_state)[0]
        Agent1 = self.get_team(game_state)[1]
        carring = game_state.get_agent_state(self.index).num_carrying

        if carring  > 3:
            return self.Mode.Retreat
        
        if not self.invaders_present(game_state):
            return self.Mode.Attack

        if self.food_in_state(game_state)+1 < len(self.get_food_you_are_defending(game_state).as_list()):
            return self.Mode.Defend
        if not self.allies_defending(game_state) and self.invaders_present(game_state) and self.index == Agent1:
            return self.Mode.Defend
        
        return self.mode    
    
    def invaders_present(self, game_state):
        enemies = [game_state.get_agent_state(i) for i in self.get_opponents(game_state)]
        invaders = [enemy for enemy in enemies if enemy.is_pacman and enemy.get_position() is not None]
        return len(invaders) > 0

    def choose_action(self, game_state):
        # Collect legal moves and successor states
        legalMoves = game_state.get_legal_actions(self.index)
        self.mode = self.DecisionTree(game_state)
        # Choose one of the best actions
        if self.mode == self.Mode.Retreat:
            scores = [self.heuristic_get_home(game_state, action) for action in legalMoves]
        if self.mode == self.Mode.Attack:  
            scores = [self.evaluationFunction(game_state, action) for action in legalMoves]
        if self.mode == self.Mode.Defend:
            scores = [self.heuristic_defend(game_state, action) for action in legalMoves]
        
        bestScore = max(scores)
        bestIndices = [index for index in range(len(scores)) if scores[index] == bestScore]
        chosenIndex = random.choice(bestIndices) # Pick randomly among the best

        return legalMoves[chosenIndex]
    
    def get_successor(self, game_state, action):

        successor = game_state.generate_successor(self.index, action)
        pos = successor.get_agent_state(self.index).get_position()
        if pos != nearestPoint(pos):
            # Only half a grid position was covered
            return successor.generate_successor(self.index, action)
        else:
            return successor

    def min_distance_from_list(self, lst, position):
        distances = [self.get_maze_distance(position, element) for element in lst]
        min_distance = min(distances)
        min_index = distances.index(min_distance)
        return min_distance, min_index
    
    def evaluationFunction(self, game_state, action):
    
        
        # Useful information you can extract from a GameState (pacman.py)
        my_score = 0
        successor = self.get_successor(game_state,action) 
        my_state = successor.get_agent_state(self.index)
        position = my_state.get_position()
        newFood = self.get_food(successor).as_list()
        oldFood = self.get_food(game_state).as_list()
        

        old_my_state = game_state.get_agent_state(self.index)
        oldPos = old_my_state.get_position()
        
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        ghosts = [a for a in enemies if not a.is_pacman and a.get_position() is not None]
        ghost_distance = [self.get_maze_distance(position, ghost.get_position()) for ghost in ghosts]
        foodDistance = self.min_distance_from_list(newFood,position)
        foodDistanceOld = self.min_distance_from_list(oldFood,oldPos)

        for element in ghost_distance:
            my_score += 0.5 * pow(element, 1.5)
            if element < 2:
                my_score -= 10000

        if foodDistance < foodDistanceOld:
                my_score += 2000

        for element in ghost_distance:
            my_score += 0.5*pow(element,1.5)
            if(element < 2):
                my_score -= 10000
        return successor.get_score() + my_score
        
    def heuristic_get_home(self, game_state,action):
        successor = self.get_successor(game_state,action) 
        my_state = successor.get_agent_state(self.index)
        position = my_state.get_position()
        my_score = 0.0
        # Calculate distance to home base or starting position
        distance_to_home = self.min_distance_from_list(self.safe_zone,position)
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        ghosts = [a for a in enemies if not a.is_pacman and a.get_position() is not None]
        ghost_distance = [self.get_maze_distance(position, ghost.get_position()) for ghost in ghosts]

        for element in ghost_distance:
            my_score += 0.5*pow(element,1.5)
            if(element < 2):
                my_score -= 10000
        return my_score-distance_to_home[0]  
    
    def safe_zone_limit(self,game_state):
        limit = []
        no_walls = []
        if self.red:
            i = self.width_half - 1
        else:
            i = self.width_half + 1
        limit = [(i,float(j)) for j in  range(self.height)]
        for i in limit:

            if not game_state.data.layout.walls[int(i[0])][int(i[1])]:
                no_walls.append(i)
        return no_walls
    def heuristic_defend(self, game_state, action):
        successor = game_state
        my_state = successor.get_agent_state(self.index)
        position = my_state.get_position()
        my_score = 0.0

        # Evaluate the distance to invaders (enemy Pac-Man)
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        invaders = [enemy for enemy in enemies if enemy.is_pacman and enemy.get_position() is not None]
        if invaders:
            invader_positions = [invader.get_position() for invader in invaders]
            closest_invader_distance = self.min_distance_from_list(invader_positions, position)[0]
            print(invader_positions)
            print(position)

            # Encourage the agent to chase the closest invader
            my_score -= closest_invader_distance  # Positive score to chase invaders

        # Evaluate cutting off access to the closest food
        #    food = self.get_food_you_are_defending(successor).as_list()
         #   closest_food = self.min_distance_from_list(food, position)[0]
          #  if closest_food is not None:
                # Encourage cutting off access to the closest food
           #     my_score += 50 - closest_food  # Positive score to block access to food

            return my_score




    def allies_defending(self, game_state):
        allies_positions = [game_state.get_agent_position(index) for index in self.get_team(game_state)]
        allies_defending = [pos for pos in allies_positions if pos[0] < self.width_half]
        return len(allies_defending) > 1
    
    