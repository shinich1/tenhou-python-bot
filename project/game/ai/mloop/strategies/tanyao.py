# -*- coding: utf-8 -*-
from mahjong.constants import TERMINAL_INDICES, HONOR_INDICES
from mahjong.tile import TilesConverter
from mahjong.utils import is_honor
from mahjong.utils import is_tile_strictly_isolated

from game.ai.mloop.strategies.main import BaseStrategy


class TanyaoStrategy(BaseStrategy):
    min_shanten = 3
    not_suitable_tiles = TERMINAL_INDICES + HONOR_INDICES

    #params for optimization
    kuitan_max_remaining_tiles = 0

    def __init__(self, strategy_type, player, gpparams):
        super(TanyaoStrategy, self).__init__(strategy_type,player,gpparams)
        try: 
            self.kuitan_max_remaining_tiles = gpparams[0] #should change gpparams format to dict
        except:
            self.kuitan_max_remaining_tiles = 10 #this is the default value

    def should_activate_strategy(self, tiles_136):
        """
        Tanyao hand is a hand without terminal and honor tiles, to achieve this
        we will use different approaches
        :return: boolean
        """

        result = super(TanyaoStrategy, self).should_activate_strategy(tiles_136)
        if not result:
            return False

        tiles = TilesConverter.to_34_array(self.player.tiles)

        closed_hand_34 = TilesConverter.to_34_array(self.player.closed_hand)
        isolated_tiles = [x // 4 for x in self.player.tiles
                          if is_tile_strictly_isolated(closed_hand_34, x // 4) or is_honor(x // 4)]

        count_of_terminal_pon_sets = 0
        count_of_terminal_pairs = 0
        count_of_valued_pairs = 0
        count_of_not_suitable_tiles = 0
        count_of_not_suitable_not_isolated_tiles = 0
        for x in range(0, 34):
            tile = tiles[x]
            if not tile:
                continue

            if x in self.not_suitable_tiles and tile == 3:
                count_of_terminal_pon_sets += 1

            if x in self.not_suitable_tiles and tile == 2:
                count_of_terminal_pairs += 1

                if x in self.player.valued_honors:
                    count_of_valued_pairs += 1

            if x in self.not_suitable_tiles:
                count_of_not_suitable_tiles += tile

            if x in self.not_suitable_tiles and x not in isolated_tiles:
                count_of_not_suitable_not_isolated_tiles += tile

        # we have too much terminals and honors
        if count_of_not_suitable_tiles >= 5:
            return False

        # if we already have pon of honor\terminal tiles
        # we don't need to open hand for tanyao
        if count_of_terminal_pon_sets > 0:
            return False

        # with valued pair (yakuhai wind or dragon)
        # we don't need to go for tanyao
        if count_of_valued_pairs > 0:
            return False

        # one pair is ok in tanyao pair
        # but 2+ pairs can't be suitable
        if count_of_terminal_pairs > 1:
            return False

        # 3 or more not suitable tiles that
        # are not isolated is too much
        if count_of_not_suitable_not_isolated_tiles >= 3:
            return False

        # if we are 1 shanten, even 2 tiles
        # that are not suitable and not isolated
        # is too much
        if count_of_not_suitable_not_isolated_tiles >= 2 and self.player.ai.shanten == 1:
            return False

        # 123 and 789 indices
        indices = [
            [0, 1, 2], [6, 7, 8],
            [9, 10, 11], [15, 16, 17],
            [18, 19, 20], [24, 25, 26]
        ]

        for index_set in indices:
            first = tiles[index_set[0]]
            second = tiles[index_set[1]]
            third = tiles[index_set[2]]
            if first >= 1 and second >= 1 and third >= 1:
                return False

        # if we have 2 or more non-central doras
        # we don't want to go for tanyao
        if self.dora_count_not_central >= 2:
            return False

        # if we have less than two central doras
        # let's not consider open tanyao
        if self.dora_count_central < 2:
            return False

        # if we have only two central doras let's
        # wait for 5th turn before opening our hand
        if self.dora_count_central == 2 and self.player.round_step < 5:
            return False

        return True

    def determine_what_to_discard(self, discard_options, hand, open_melds):
        is_open_hand = len(open_melds) > 0

        # our hand is closed, we don't need to discard terminal tiles here
        if not is_open_hand:
            return discard_options

        first_option = sorted(discard_options, key=lambda x: x.shanten)[0]
        shanten = first_option.shanten

        if shanten > 1:
            return super(TanyaoStrategy, self).determine_what_to_discard(
                discard_options,
                hand,
                open_melds
            )

        results = []
        not_suitable_tiles = []
        for item in discard_options:
            if not self.is_tile_suitable(item.tile_to_discard * 4):
                item.had_to_be_discarded = True
                not_suitable_tiles.append(item)
                continue

            # there is no sense to wait 1-4 if we have open hand
            # but let's only avoid atodzuke tiles in tempai, the rest will be dealt with in
            # generic logic
            if item.shanten == 0:
                all_waiting_are_fine = all(
                    [(self.is_tile_suitable(x * 4) or item.wait_to_ukeire[x] == 0) for x in item.waiting])
                if all_waiting_are_fine:
                    results.append(item)

        if not_suitable_tiles:
            return not_suitable_tiles

        # we don't have a choice
        # we had to have on bad wait
        if not results:
            return discard_options

        return results

    def is_tile_suitable(self, tile):
        """
        We can use only simples tiles (2-8) in any suit
        :param tile: 136 tiles format
        :return: True
        """
        tile //= 4
        return tile not in self.not_suitable_tiles

    def try_to_call_meld(self, tile, is_kamicha_discard, new_tiles, remaining_tiles):
        if remaining_tiles < self.kuitan_max_remaining_tiles:
            return super(TanyaoStrategy,self).try_to_call_meld(tile, is_kamicha_discard, new_tiles, remaining_tiles)
        else:
            return None, None