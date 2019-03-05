# -*- coding: utf-8 -*-
from mahjong.constants import EAST, SOUTH
from mahjong.meld import Meld
from mahjong.tile import TilesConverter

from game.ai.mloop.strategies.main import BaseStrategy


class YakuhaiStrategy(BaseStrategy):
    valued_pairs = None
    has_valued_pon = None

    def __init__(self, strategy_type, player, gpparams):
        super().__init__(strategy_type, player, gpparams)

        self.valued_pairs = []
        self.has_valued_pon = False
        self.last_chance_calls = []

    def should_activate_strategy(self, tiles_136):
        """
        We can go for yakuhai strategy if we have at least one yakuhai pair in the hand
        :return: boolean
        """
        result = super(YakuhaiStrategy, self).should_activate_strategy(tiles_136)
        if not result:
            return False

        tiles_34 = TilesConverter.to_34_array(tiles_136)
        player_hand_tiles_34 = TilesConverter.to_34_array(self.player.tiles)
        player_closed_hand_tiles_34 = TilesConverter.to_34_array(self.player.closed_hand)
        self.valued_pairs = [x for x in self.player.valued_honors if player_hand_tiles_34[x] == 2]

        is_double_east_wind = len([x for x in self.valued_pairs if x == EAST]) == 2
        is_double_south_wind = len([x for x in self.valued_pairs if x == SOUTH]) == 2

        self.valued_pairs = list(set(self.valued_pairs))
        self.has_valued_pon = len([x for x in self.player.valued_honors if player_hand_tiles_34[x] >= 3]) >= 1

        opportunity_to_meld_yakuhai = False

        for x in range(0, 34):
            if x in self.valued_pairs and tiles_34[x] - player_hand_tiles_34[x] == 1:
                opportunity_to_meld_yakuhai = True

        has_valued_pair = False

        for pair in self.valued_pairs:
            # we have valued pair in the hand and there are enough tiles
            # in the wall
            if opportunity_to_meld_yakuhai or self.player.total_tiles(pair, player_closed_hand_tiles_34) < 4:
                has_valued_pair = True
                break

        # we don't have valuable pair or pon to open our hand
        if not has_valued_pair and not self.has_valued_pon:
            return False

        # let's always open double east
        if is_double_east_wind:
            return True

        # let's open double south if we have a dora in the hand
        # or we have other valuable pairs
        if is_double_south_wind and (self.dora_count_total >= 1 or len(self.valued_pairs) >= 2):
            return True

        # If we have 1+ dora in the hand and there are 2+ valuable pairs let's open hand
        if len(self.valued_pairs) >= 2 and self.dora_count_total >= 1:
            return True

        # If we have 2+ dora in the hand let's open hand
        if self.dora_count_total >= 2:
            for x in range(0, 34):
                # we have other pair in the hand
                # so we can open hand for atodzuke
                if player_hand_tiles_34[x] >= 2 and x not in self.valued_pairs:
                    self.go_for_atodzuke = True
            return True

        # If we have 1+ dora in the hand and there is 5+ round step let's open hand
        if self.dora_count_total >= 1 and self.player.round_step > 5:
            return True

        for pair in self.valued_pairs:
            # last chance to get that yakuhai, let's go for it
            if (opportunity_to_meld_yakuhai and
                    self.player.total_tiles(pair, player_closed_hand_tiles_34) == 3 and
                    self.player.ai.shanten >= 1):

                if pair not in self.last_chance_calls:
                    self.last_chance_calls.append(pair)

                return True

        return False

    def determine_what_to_discard(self, discard_options, hand, open_melds):
        is_open_hand = len(open_melds) > 0

        tiles_34 = TilesConverter.to_34_array(hand)

        valued_pairs = [x for x in self.player.valued_honors if tiles_34[x] == 2]

        # closed pon sets
        valued_pons = [x for x in self.player.valued_honors if tiles_34[x] == 3]
        # open pon sets
        valued_pons += [x for x in open_melds if x.type == Meld.PON and x.tiles[0] // 4 in self.player.valued_honors]

        acceptable_options = []
        for item in discard_options:
            if is_open_hand:
                if len(valued_pons) == 0:
                    # don't destroy our only yakuhai pair
                    if len(valued_pairs) == 1 and item.tile_to_discard in valued_pairs:
                        continue
                elif len(valued_pons) == 1:
                    # don't destroy our only yakuhai pon
                    if item.tile_to_discard in valued_pons:
                        continue

                acceptable_options.append(item)

        # we don't have a choice
        if not acceptable_options:
            return discard_options

        preferred_options = []
        for item in acceptable_options:
            # ignore wait without yakuhai yaku if possible
            if is_open_hand and len(valued_pons) == 0 and len(valued_pairs) == 1:
                if item.shanten == 0:
                    if valued_pairs[0] not in item.waiting:
                        continue

            preferred_options.append(item)

        if not preferred_options:
            return acceptable_options

        return preferred_options

    def is_tile_suitable(self, tile):
        """
        For yakuhai we don't have any limits
        :param tile: 136 tiles format
        :return: True
        """
        return True

    def meld_had_to_be_called(self, tile):
        tile //= 4
        tiles_34 = TilesConverter.to_34_array(self.player.tiles)
        valued_pairs = [x for x in self.player.valued_honors if tiles_34[x] == 2]

        # for big shanten number we don't need to check already opened pon set,
        # because it will improve our hand anyway
        if self.player.ai.shanten < 2:
            for meld in self.player.melds:
                # we have already opened yakuhai pon
                # so we don't need to open hand without shanten improvement
                if self._is_yakuhai_pon(meld):
                    return False

        # if we don't have any yakuhai pon and this is our last chance, we must call this tile
        if tile in self.last_chance_calls:
            return True

        # in all other cases for closed hand we don't need to open hand with special conditions
        if not self.player.is_open_hand:
            return False

        # we have opened the hand already and don't yet have yakuhai pon
        # so we now must get it
        for valued_pair in valued_pairs:
            if valued_pair == tile:
                return True

        return False

    def try_to_call_meld(self, tile, is_kamicha_discard, tiles_136, remaining_tiles):
        if self.has_valued_pon:
            return super(YakuhaiStrategy, self).try_to_call_meld(tile, is_kamicha_discard, tiles_136, remaining_tiles)

        tile_34 = tile // 4
        # we will open hand for atodzuke only in the special cases
        if not self.player.is_open_hand and tile_34 not in self.valued_pairs:
            if self.go_for_atodzuke:
                return super(YakuhaiStrategy, self).try_to_call_meld(tile, is_kamicha_discard, tiles_136, remaining_tiles)

            return None, None

        return super(YakuhaiStrategy, self).try_to_call_meld(tile, is_kamicha_discard, tiles_136, remaining_tiles)

    def _is_yakuhai_pon(self, meld):
        return meld.type == Meld.PON and meld.tiles[0] // 4 in self.player.valued_honors
