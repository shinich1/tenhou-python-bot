# -*- coding: utf-8 -*-
from mahjong.constants import AKA_DORA_LIST
from mahjong.tile import TilesConverter
from mahjong.utils import is_honor, simplify, plus_dora, is_aka_dora, is_sou, is_man, is_pin

from game.ai.mloop.strategies.main import BaseStrategy


class DiscardOption(object):
    DORA_VALUE = 10000
    DORA_FIRST_NEIGHBOUR = 1000
    DORA_SECOND_NEIGHBOUR = 100

    player = None

    # in 34 tile format
    tile_to_discard = None
    # array of tiles that will improve our hand
    waiting = None
    # how much tiles will improve our hand
    ukeire = None
    ukeire_second = None
    # number of shanten for that tile
    shanten = None
    # sometimes we had to force tile to be discarded
    had_to_be_discarded = False
    # special cases where we had to save tile in hand (usually for atodzuke opened hand)
    had_to_be_saved = False
    # calculated tile value, for sorting
    valuation = None
    # how danger this tile is
    danger = None
    # wait to ukeire map
    wait_to_ukeire = None
    # second level cost approximation for 1-shanten hands
    second_level_cost = None

    def __init__(self, player, tile_to_discard, shanten, waiting, ukeire, danger=100, wait_to_ukeire=None):
        """
        :param player:
        :param tile_to_discard: tile in 34 format
        :param waiting: list of tiles in 34 format
        :param ukeire: count of tiles to wait after discard
        """
        self.player = player
        self.tile_to_discard = tile_to_discard
        self.shanten = shanten
        self.waiting = waiting
        self.ukeire = ukeire
        self.ukeire_second = 0
        self.count_of_dora = 0
        self.danger = danger
        self.had_to_be_saved = False
        self.had_to_be_discarded = False
        self.wait_to_ukeire = wait_to_ukeire

        self.calculate_value()

    def __unicode__(self):
        tile_format_136 = TilesConverter.to_one_line_string([self.tile_to_discard*4])
        return 'tile={}, shanten={}, ukeire={}, ukeire2={}, valuation={}'.format(
            tile_format_136,
            self.shanten,
            self.ukeire,
            self.ukeire_second,
            self.valuation
        )

    def __repr__(self):
        return '{}'.format(self.__unicode__())

    def find_tile_in_hand(self, closed_hand):
        """
        Find and return 136 tile in closed player hand
        """

        if self.player.table.has_aka_dora:
            tiles_five_of_suits = [4, 13, 22]
            # special case, to keep aka dora in hand
            if self.tile_to_discard in tiles_five_of_suits:
                aka_closed_hand = closed_hand[:]
                while True:
                    tile = TilesConverter.find_34_tile_in_136_array(self.tile_to_discard, aka_closed_hand)

                    # we have only aka dora in the hand, without simple five
                    if not tile:
                        break

                    # we found aka in the hand,
                    # let's try to search another five tile
                    # to keep aka dora
                    if tile in AKA_DORA_LIST:
                        aka_closed_hand.remove(tile)
                    else:
                        return tile

        return TilesConverter.find_34_tile_in_136_array(self.tile_to_discard, closed_hand)

    def calculate_value(self):
        # base is 100 for ability to mark tiles as not needed (like set value to 50)
        value = 100
        honored_value = 20

        if is_honor(self.tile_to_discard):
            if self.tile_to_discard in self.player.valued_honors:
                count_of_winds = [x for x in self.player.valued_honors if x == self.tile_to_discard]
                # for west-west, east-east we had to double tile value
                value += honored_value * len(count_of_winds)
        else:
            # aim for tanyao
            if self.player.ai.current_strategy and self.player.ai.current_strategy.type == BaseStrategy.TANYAO:
                suit_tile_grades = [10, 20, 30, 50, 40, 50, 30, 20, 10]
            # usual hand
            else:
                suit_tile_grades = [10, 20, 40, 50, 30, 50, 40, 20, 10]

            simplified_tile = simplify(self.tile_to_discard)
            value += suit_tile_grades[simplified_tile]

            for indicator in self.player.table.dora_indicators:
                indicator_34 = indicator // 4
                if is_honor(indicator_34):
                    continue

                # indicator and tile not from the same suit
                if is_sou(indicator_34) and not is_sou(self.tile_to_discard):
                    continue

                # indicator and tile not from the same suit
                if is_man(indicator_34) and not is_man(self.tile_to_discard):
                    continue

                # indicator and tile not from the same suit
                if is_pin(indicator_34) and not is_pin(self.tile_to_discard):
                    continue

                simplified_indicator = simplify(indicator_34)
                simplified_dora = simplified_indicator + 1
                # indicator is 9 man
                if simplified_dora == 9:
                    simplified_dora = 0

                # tile so close to the dora
                if simplified_tile + 1 == simplified_dora or simplified_tile - 1 == simplified_dora:
                    value += DiscardOption.DORA_FIRST_NEIGHBOUR

                # tile not far away from dora
                if simplified_tile + 2 == simplified_dora or simplified_tile - 2 == simplified_dora:
                    value += DiscardOption.DORA_SECOND_NEIGHBOUR

        count_of_dora = plus_dora(self.tile_to_discard * 4, self.player.table.dora_indicators)

        tile_136 = self.find_tile_in_hand(self.player.closed_hand)
        if is_aka_dora(tile_136, self.player.table.has_aka_dora):
            count_of_dora += 1

        self.count_of_dora = count_of_dora
        value += count_of_dora * DiscardOption.DORA_VALUE

        if is_honor(self.tile_to_discard):
            # depends on how much honor tiles were discarded
            # we will decrease tile value
            discard_percentage = [100, 75, 20, 0, 0]
            discarded_tiles = self.player.table.revealed_tiles[self.tile_to_discard]

            value = (value * discard_percentage[discarded_tiles]) / 100

            # three honor tiles were discarded,
            # so we don't need this tile anymore
            if value == 0:
                self.had_to_be_discarded = True

        self.valuation = int(value)
