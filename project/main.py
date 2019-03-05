# -*- coding: utf-8 -*-
"""
Endpoint to run bot. It will play a game on tenhou.net
"""
from optparse import OptionParser

from tenhou.main import connect_and_play
from utils.logger import set_up_logging, terminate_logging
from utils.settings_handler import settings

import mloop.interfaces as mli
import mloop.controllers as mlc
import mloop.visualizations as mlv
import numpy as np
import time

def parse_args_and_set_up_settings():
    parser = OptionParser()

    parser.add_option('-u', '--user_id',
                      type='string',
                      default=settings.USER_ID,
                      help='Tenhou\'s user id. Example: IDXXXXXXXX-XXXXXXXX. Default is {0}'.format(settings.USER_ID))

    parser.add_option('-g', '--game_type',
                      type='string',
                      default=settings.GAME_TYPE,
                      help='The game type in Tenhou.net. Examples: 1 or 9. Default is {0}'.format(settings.GAME_TYPE))

    parser.add_option('-l', '--lobby',
                      type='string',
                      default=settings.LOBBY,
                      help='Lobby to play. Default is {0}'.format(settings.LOBBY))

    parser.add_option('-t', '--timeout',
                      type='int',
                      default=settings.WAITING_GAME_TIMEOUT_MINUTES,
                      help='How much minutes bot will looking for a game. '
                           'If game is not started in timeout, script will be ended. '
                           'Default is {0}'.format(settings.WAITING_GAME_TIMEOUT_MINUTES))

    parser.add_option('-c', '--championship',
                      type='string',
                      help='Tournament lobby to play.')

    parser.add_option('-a', '--ai',
                      type='string',
                      default=settings.AI_PACKAGE,
                      help='AI package')

    parser.add_option('-s', '--settings',
                      type='string',
                      default=None,
                      help='Settings file name (without path, just file name without extension)')

    opts, _ = parser.parse_args()

    settings.USER_ID = opts.user_id
    settings.GAME_TYPE = opts.game_type
    settings.LOBBY = opts.lobby
    settings.WAITING_GAME_TIMEOUT_MINUTES = opts.timeout
    settings.AI_PACKAGE = opts.ai

    if opts.settings:
        module = __import__(opts.settings)
        for key, value in vars(module).items():
            # let's use only upper case settings
            if key.isupper():
                settings.__setattr__(key, value)

    # it is important to reload bot class
    settings.load_ai_class()

    if opts.championship:
        settings.IS_TOURNAMENT = True
        settings.LOBBY = opts.championship


class CustomInterface(mli.Interface):

        def __init__(self):
                super(CustomInterface,self).__init__()

        def get_next_cost_dict(self,params_dict):

                #Get parameters from the dictionary provided by the learner
                print('\n\n\n\n\n')
                params = params_dict['params']

                #start a game
                parse_args_and_set_up_settings()
                handlers=set_up_logging()
                cost, bad = connect_and_play(params)                
                terminate_logging(handlers)
                #keep the uncertainty relatively large, because of the random nature of mahjong
                uncer = 5

                #The cost, uncertainty and bad boolean must all be returned as a dictionary
                #You can include other variables you want to record as well if you want
                cost_dict = {'cost':cost, 'uncer':uncer, 'bad':bad}
                return cost_dict


def main():
    parse_args_and_set_up_settings()
    set_up_logging()

    connect_and_play([10])


def mloop():

    #First create your interface
    interface = CustomInterface()
    #Next create the controller, provide it with your controller and any options you want to set
    controller = mlc.create_controller(interface, max_num_runs = 50, target_cost = -100, num_params = 1, min_boundary = [3], max_boundary = [68])
    #To run M-LOOP and find the optimal parameters just use the controller method optimize
    controller.optimize()

    #The results of the optimization will be saved to files and can also be accessed as attributes of the controller.
    print('Best parameters found:')
    print(controller.best_params)

    #You can also run the default sets of visualizations for the controller with one command
    mlv.show_all_default_visualizations(controller)    

if __name__ == '__main__':
    mloop()
