
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
        Cutpath = 3
        Capsule = 4

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
        self.initial_time = game_state.data.timeleft
        self.maxHeld = 4
        

    def food_in_state(self,game_state):
        return len(self.get_food(game_state).as_list())
    
    def DecisionTree(self,game_state):
        Agent2 = self.get_team(game_state)[0]
        Agent2_state = game_state.get_agent_state(Agent2)
        Agent1 = self.get_team(game_state)[1]
        Agent1_state = game_state.get_agent_state(Agent1)
        carring = game_state.get_agent_state(self.index).num_carrying
        defending = self.allies_defending(game_state)
        invaders = self.invaders_present(game_state)
        if Agent1 == self.index:

            if (self.initial_time-game_state.data.timeleft) < 150:        
                return self.Mode.Retreat
            
            if Agent1_state.scared_timer == 0:        
                return self.Mode.Defend
            
            if  Agent1_state.scared_timer > 0 :
                return self.Mode.Attack
            

        
        if Agent2 == self.index:
            
            if carring  > self.maxHeld  and self.scared_time_remaining(game_state) < 10 or (game_state.data.timeleft < 200 and carring > 1):
                return self.Mode.Retreat
            
            capsules = self.get_capsules(game_state)

            if capsules:
                return self.Mode.Capsule

            if self.scared_time_remaining(game_state) > 10:
                return self.Mode.Attack

            if not self.allies_defending(game_state) and self.invaders_present(game_state):
                return self.Mode.Defend
            
            if self.food_in_state(game_state)+3 < len(self.get_food_you_are_defending(game_state).as_list()):
                return self.Mode.Defend

            return self.Mode.Attack


        
        return self.mode  #default: keep doing your thing  
    
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
            scores = [self.close_food_heuristic(game_state, action) for action in legalMoves]
        if self.mode == self.Mode.Defend:
            scores = [self.heuristic_defend(game_state, action) for action in legalMoves]
        if self.mode == self.Mode.Capsule:
            scores = [self.heuristic_get_capsule(game_state, action) for action in legalMoves]
        
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
    def min_distance_from_list(self, lst, position):
        distances = [self.get_maze_distance(position, element) for element in lst]
        min_distance = min(distances)
        min_index = distances.index(min_distance)
        return min_distance, min_index
    
    
    def close_food_heuristic(self, game_state, action):
        my_score = 0
        successor = self.get_successor(game_state, action)
        my_state = successor.get_agent_state(self.index)
        position = my_state.get_position()
        newFood = self.get_food(successor).as_list()
        oldFood = self.get_food(game_state).as_list()
        
        old_my_state = game_state.get_agent_state(self.index)
        oldPos = old_my_state.get_position()
        
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        ghosts = [a for a in enemies if not a.is_pacman and a.get_position() is not None]
        ghost_distance = [self.get_maze_distance(position, ghost.get_position()) for ghost in ghosts]
        foodDistance = self.min_distance_from_list(newFood, position)
        foodDistanceOld = self.min_distance_from_list(oldFood, oldPos)

        if len(foodDistance) > 0:

            if foodDistance < foodDistanceOld:
                my_score += 1000  
            else:
                my_score -= 100 
        if self.scared_time_remaining(game_state) < 5:
            for element in ghost_distance:
                if element < 2:
                    my_score -= 5000  
                else:
                    my_score -=  2*pow(element, 5)  
        return my_score

        
    def heuristic_get_home(self, game_state,action):
        successor = self.get_successor(game_state,action) 
        my_state = successor.get_agent_state(self.index)
        position = my_state.get_position()
        my_score = 0.0

        distance_to_home = self.min_distance_from_list(self.safe_zone,position)
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        ghosts = [a for a in enemies if not a.is_pacman and a.get_position() is not None]
        ghost_distance = [self.get_maze_distance(position, ghost.get_position()) for ghost in ghosts]

        for element in ghost_distance:
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
        successor = self.get_successor(game_state,action) 
        my_state = successor.get_agent_state(self.index)
        position = my_state.get_position()
        my_score = 0.0

        # Evaluate the distance to invaders (enemy Pac-Man)
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        invaders = [enemy for enemy in enemies if enemy.is_pacman and enemy.get_position() is not None]
        if invaders: 
            invader_positions = [invader.get_position() for invader in invaders]
            closest_invader_distance = self.min_distance_from_list(invader_positions, position)[0]

                # Encourage the agent to chase the closest invader
            my_score -= pow(closest_invader_distance,10)  # Positive score to chase invaders
        if position[0] < self.width_half:
            my_score += 10
        return my_score


    def heuristic_get_capsule(self, game_state, action):
        successor = self.get_successor(game_state, action)
        my_state = successor.get_agent_state(self.index)
        position = my_state.get_position()
        my_score = 100.0

        capsules = self.get_capsules(successor)
        if capsules:
            capsule_positions = capsules
            closest_capsule_distance = self.min_distance_from_list(capsule_positions, position)[0]

            my_score -= closest_capsule_distance 

        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        ghosts = [a for a in enemies if not a.is_pacman and a.get_position() is not None]
        ghost_distance = [self.get_maze_distance(position, ghost.get_position()) for ghost in ghosts]

        for distance in ghost_distance:
            if distance < 2:  # If ghost is close, discourage going towards the capsule
                my_score -= 10000  # Set a high penalty to avoid ghosts

        return my_score



    def invaders_present(self, game_state):
        enemies = [game_state.get_agent_state(i) for i in self.get_opponents(game_state)]
        invaders = [enemy for enemy in enemies if enemy.is_pacman]
        return len(invaders) > 0
    
    def scared_time_remaining(self, game_state):
        enemies = [game_state.get_agent_state(i) for i in self.get_opponents(game_state)]
        scared_times = [enemy.scared_timer for enemy in enemies if not enemy.is_pacman and enemy.scared_timer > 0]
        return max(scared_times) if scared_times else 0    
    
    def allies_defending(self, game_state):
        allies = [game_state.get_agent_state(i) for i in self.get_team(game_state)]
        allies_defending = [ally for ally in allies if not ally.is_pacman and ally.get_position() is not None]
        return len(allies_defending) > 1
    
    