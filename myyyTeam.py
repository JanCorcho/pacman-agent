import random
import contest.util as util
import time
from contest.captureAgents import CaptureAgent
from contest.game import Directions,Actions
from contest.util import nearestPoint
import math

#################
# Team creation #
#################
def create_team(firstIndex, secondIndex, isRed, first='AStarOfTheShow', second='DefensiveReflexAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]



##########
# Agents #  
##########
class ReflexCaptureAgent(CaptureAgent):
    """
    A base class for reflex agents that choose score-maximizing actions
    """

    def __init__(self, index, time_for_computing=.1):
        super().__init__(index, time_for_computing)
        self.start = None

    def register_initial_state(self, game_state):
        self.start = game_state.get_agent_position(self.index)
        CaptureAgent.register_initial_state(self, game_state)

    def choose_action(self, game_state):
        """
        Picks among the actions with the highest Q(s,a).
        """
        actions = game_state.get_legal_actions(self.index)

        # You can profile your evaluation time by uncommenting these lines
        # start = time.time()
        values = [self.evaluate(game_state, a) for a in actions]
        # print 'eval time for agent %d: %.4f' % (self.index, time.time() - start)

        max_value = max(values)
        best_actions = [a for a, v in zip(actions, values) if v == max_value]

        food_left = len(self.get_food(game_state).as_list())

        if food_left <= 2:
            best_dist = 9999
            best_action = None
            for action in actions:
                successor = self.get_successor(game_state, action)
                pos2 = successor.get_agent_position(self.index)
                dist = self.get_maze_distance(self.start, pos2)
                if dist < best_dist:
                    best_action = action
                    best_dist = dist
            return best_action

        return random.choice(best_actions)

    def get_successor(self, game_state, action):
        """
        Finds the next successor which is a grid position (location tuple).
        """
        successor = game_state.generate_successor(self.index, action)
        pos = successor.get_agent_state(self.index).get_position()
        if pos != nearestPoint(pos):
            # Only half a grid position was covered
            return successor.generate_successor(self.index, action)
        else:
            return successor

    def evaluate(self, game_state, action):
        """
        Computes a linear combination of features and feature weights
        """
        features = self.get_features(game_state, action)
        weights = self.get_weights(game_state, action)
        return features * weights

    def get_features(self, game_state, action):
        """
        Returns a counter of features for the state
        """
        features = util.Counter()
        successor = self.get_successor(game_state, action)
        features['successor_score'] = self.get_score(successor)
        return features

    def get_weights(self, game_state, action):
        """
        Normally, weights do not depend on the game state.  They can be either
        a counter or a dictionary.
        """
        return {'successor_score': 1.0}


class DefensiveReflexAgent(ReflexCaptureAgent):
    
    def _init_(self, index, time_for_computing=.1):
        super()._init_(index, time_for_computing)
        self.start = None
        
    def register_initial_state(self, game_state):
        self.start  = game_state.get_agent_state(self.index)
        self.location_of_last_eaten_food(game_state)  # detect last eaten food
        actions = game_state.get_legal_actions(self.index)
        values = [self.evaluate(game_state, a) for a in actions]
        enemies = [game_state.get_agent_state(i) for i in self.get_opponents(game_state)]
        invaders = [a for a in enemies if a.is_pacman]
        knowninvaders = [a for a in enemies if a.is_pacman and a.get_position() !=None ]

        if len(invaders) == 0 or game_state.get_agent_position(self.index) == self.lastEatenFoodPosition or len(knowninvaders) > 0:
            self.lastEatenFoodPosition = None
        
        if len(knowninvaders) > 0 and game_state.getAgentState(self.index).scaredTimer == 0:
            return self.heuristic_defend(self, game_state, action)

        maxValue = max(values)
        bestActions = [a for a, v in zip(actions, values) if v == maxValue]
        return random.choice(bestActions)

    def getFeatures(self, gameState, action):
        features = util.Counter()
        successor = self.getSuccessor(gameState, action)

        myState = successor.getAgentState(self.index)
        myPos = myState.getPosition()

        features['dead'] = 0

        # Computes whether we're on defense (1) or offense (0)
        features['onDefense'] = 1
        if myState.isPacman: features['onDefense'] = 0

        # Computes distance to invaders we can see
        enemies = [successor.getAgentState(i) for i in self.getOpponents(successor)]
        invaders = [a for a in enemies if a.isPacman and a.getPosition() != None]
        features['numInvaders'] = len(invaders)
        if len(invaders) > 0 and gameState.getAgentState(self.index).scaredTimer >0:
            dists = [self.getMazeDistance(myPos, a.getPosition()) for a in invaders]
            features['invaderDistance'] = -1/min(dists)


        if action == Directions.STOP: features['stop'] = 1
        rev = Directions.REVERSE[gameState.getAgentState(self.index).configuration.direction]
        if action == rev: features['reverse'] = 1
        features['DistToBoundary'] = - self.distToHome(successor)
        return features
    
    def heuristic_defend(self, game_state, action):
        successor = self.get_successor(game_state, action)
        my_state = successor.get_agent_state(self.index)
        position = my_state.get_position()
        my_score = 0.0

        # Evaluate the distance to invaders (enemy Pac-Man)
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        invaders = [enemy for enemy in enemies if enemy.is_pacman and enemy.get_position() is not None]
        if invaders:
            invader_distances = [self.get_maze_distance(position, invader.get_position()) for invader in invaders]
            closest_invader_distance = min(invader_distances)
            
            # Encourage the agent to chase the closest invader
            my_score += 1000 / closest_invader_distance  # Positive score to chase invaders

        # Evaluate cutting off access to the closest food
        closest_food = self.get_closest_food(successor, position)
        if closest_food:
            food_distance = self.get_maze_distance(position, closest_food)
            
            # Encourage cutting off access to the closest food
            my_score += 500 / food_distance  # Positive score to block access to food

        return my_score
    
    def location_of_last_eaten_food(self, game_state):
        ''''
        return the location of the last eaten food
        '''
        if len(self.observationHistory) > 1:
            prev_state = self.get_previous_observation()
            prev_food_list = self.get_food_you_are_defending(prev_state).as_list()
            current_food_list = self.get_food_you_are_defending(game_state).as_list()
            if len(prev_food_list) != len(current_food_list):
                for food in prev_food_list:
                    if food not in current_food_list:
                        self.last_eaten_food_position = food
        
class AStarOfTheShow(CaptureAgent):

    def _init_(self, index, time_for_computing=.1):
        super()._init_(index, time_for_computing)
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

    def food_in_state(self,game_state):
        
        return len(self.get_food(game_state).as_list())
    
    def choose_action(self, game_state):
        # Collect legal moves and successor states

        legalMoves = game_state.get_legal_actions(self.index)
        
        # Choose one of the best actions
        if self.food_in_state(game_state)+2 < self.initial_food:
            scores = [self.heuristic_get_home(game_state, action) for action in legalMoves]
        else:  
            scores = [self.evaluationFunction(game_state, action) for action in legalMoves]
        
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
    
    
