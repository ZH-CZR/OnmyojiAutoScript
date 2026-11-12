"""反击姑获鸟执行适配：复用交易确认、回收和安全时限。"""
from module.logger import logger
from tasks.Chess.runtime.inventory import BoardUnit
from tasks.Chess.strategy import counter_ubume as plan
from tasks.Chess.strategy.grigri import grigri_bond_name
from tasks.Chess.strategy.shikigami_catalog import SHIKIGAMI_BONDS_BY_ROMAJI, SHIKIGAMI_BY_ROMAJI


class CounterUbumeMixin:
    def _equipment_required_groups(self, level):
        if not self._uses_counter_ubume():
            return super()._equipment_required_groups(level)
        return tuple({frozenset((slot['name'], slot['substitute'])) if slot.get('substitute')
                      else frozenset((slot['name'],))
                      for slot in plan.SLOTS if slot['min_level'] <= level})

    def _uses_counter_ubume(self):
        return getattr(self, '_active_lineup_key', None) == plan.KEY

    def _counter_effective_gold(self, observed):
        if observed is None:
            return None
        if getattr(self, '_counter_budget_round', None) == getattr(self, '_current_round_no', None):
            mode = self._read_chess_mode()
            previous_mode = getattr(self, '_counter_budget_mode', None)
            if (previous_mode is not None and mode in ('备', '战', '待') and mode != previous_mode
                    and getattr(self, '_unconfirmed_experience_round', None) != self._current_round_no
                    and not getattr(self, '_unconfirmed_shop_refresh', False)):
                # 战后/等待阶段结算收入重新按当前余额运营；未确认付费不能借此解锁。
                self._counter_gold_ceiling = None
                self._counter_budget_mode = mode
            ceiling = getattr(self, '_counter_gold_ceiling', None)
            if ceiling is not None:
                return min(observed, ceiling)
        return observed

    def _counter_record_spend(self, before, cost):
        if before is not None:
            self._counter_budget_round = self._current_round_no
            self._counter_budget_mode = self._read_chess_mode()
            self._counter_gold_ceiling = max(0, before - cost)

    @property
    def shikigami_deploy_positions(self):
        positions = super().shikigami_deploy_positions
        if self._uses_counter_ubume():
            positions[plan.KAPPA] = 5
            target = getattr(self, '_counter_deploy_target', None)
            if target is not None:
                positions[target[0]] = target[1]
        return positions

    def _lineup_final_level(self):
        return 8 if self._uses_counter_ubume() else super()._lineup_final_level()

    def _load_strategy_shikigami_rules(self, entries, image_field, threshold):
        if self._uses_counter_ubume():
            entries = {**entries, **self.get_lineup_strategy()['substitutes']}
        return super()._load_strategy_shikigami_rules(entries, image_field, threshold)

    def _inventory_target_star(self, name):
        if self._uses_counter_ubume() and name == plan.KAPPA:
            return 1
        return super()._inventory_target_star(name)

    def _inventory_should_buy(self, name):
        if self._uses_counter_ubume():
            level = self._read_level()
            if level is None:
                return False
            return plan.can_buy(name, self._card_inventory,
                                getattr(self, '_counter_primary_acquired', False), level)
        return super()._inventory_should_buy(name)

    def _shop_purchase_priority(self, name):
        return (plan.purchase_priority(name, self._card_inventory, self._read_level(),
                                        getattr(self, '_counter_primary_acquired', False))
                if self._uses_counter_ubume() else (0,))

    def _economy_sequence_for_level(self, level):
        if self._uses_counter_ubume():
            return (plan.operation(level, self._card_inventory),)
        return super()._economy_sequence_for_level(level)

    def _economy_reserve_for_level(self, level):
        return plan.reserve(level) if self._uses_counter_ubume() else super()._economy_reserve_for_level(level)

    def _next_economy_operation(self, level):
        if self._uses_counter_ubume():
            return plan.operation(level, self._card_inventory)
        return super()._next_economy_operation(level)

    def _can_execute_economy_operation(self, level, gold, operation):
        if self._uses_counter_ubume():
            if (operation != plan.operation(level, self._card_inventory) or operation == 'hold'):
                return False
            cost = self.EXPERIENCE_COST if operation == 'experience' else self.SHOP_REFRESH_COST
            gold = self._counter_effective_gold(gold)
            return gold is not None and gold >= plan.reserve(level) + cost
        return super()._can_execute_economy_operation(level, gold, operation)

    def _can_afford_shop_shikigami(self, slot_index, known_price=None):
        if not self._uses_counter_ubume():
            return super()._can_afford_shop_shikigami(slot_index, known_price)
        if slot_index not in range(1, 6):
            return False
        if known_price is None:
            known_price, _ = self._read_shop_slot_price(slot_index)
        gold = self._counter_effective_gold(self._read_shop_gold())
        return gold is not None and known_price is not None and gold >= known_price

    def _buy_shop_slot(self, slot_index, click_rule, matched_name):
        if not self._uses_counter_ubume():
            return super()._buy_shop_slot(slot_index, click_rule, matched_name)
        price = SHIKIGAMI_BY_ROMAJI[matched_name].cost
        if not self._can_afford_shop_shikigami(slot_index, price):
            return False
        before = self._counter_effective_gold(self._read_shop_gold())
        self._shop_purchase_clicked = False
        result = super()._buy_shop_slot(slot_index, click_rule, matched_name)
        # 只为已确认或确实发出点击的交易预留费用。
        if result or self._shop_purchase_clicked:
            self._counter_record_spend(before, price)
        return result

    def _experience_gold_available(self, gold):
        if self._uses_counter_ubume():
            return self._counter_effective_gold(gold)
        return super()._experience_gold_available(gold)

    def _click_economy_button_and_confirm_gold(self, button, expected_cost, label, allow_hidden, **kwargs):
        if not self._uses_counter_ubume():
            return super()._click_economy_button_and_confirm_gold(button, expected_cost, label, allow_hidden, **kwargs)
        before = self._counter_effective_gold(self._read_shop_gold())
        self._experience_clicks_sent = 0
        uncertain = getattr(self, '_unconfirmed_experience_round', None)
        result = super()._click_economy_button_and_confirm_gold(button, expected_cost, label, allow_hidden, **kwargs)
        if (result == 'success' or (uncertain != self._current_round_no
                and getattr(self, '_unconfirmed_experience_round', None) == self._current_round_no)):
            self._counter_record_spend(before, expected_cost * (self._experience_clicks_sent or 1))
        return result

    def _click_shop_refresh_and_confirm_slots(self, allow_hidden):
        if not self._uses_counter_ubume():
            return super()._click_shop_refresh_and_confirm_slots(allow_hidden)
        before = self._counter_effective_gold(self._read_shop_gold())
        uncertain = getattr(self, '_unconfirmed_shop_refresh', False) and (
            getattr(self, '_unconfirmed_shop_refresh_round', self._current_round_no) == self._current_round_no)
        result = super()._click_shop_refresh_and_confirm_slots(allow_hidden)
        if not uncertain and (result == 'success' or getattr(self, '_unconfirmed_shop_refresh', False)):
            self._counter_record_spend(before, self.SHOP_REFRESH_COST)
        return result

    def _inventory_unit_destination(self, name, position):
        if self._uses_counter_ubume() and name == plan.KUJIRA and position in (4, 6):
            return position
        return super()._inventory_unit_destination(name, position)

    def _counter_substitution_needed(self):
        substitute = self._card_inventory.board.get(5)
        return (substitute is not None and substitute.name == plan.KAPPA
                and any(c.name == plan.JINKOUGYOU and c.star is not None for c in self._card_inventory.hand))

    def _after_lineup_purchase(self, name):
        if self._uses_counter_ubume() and name == plan.JINKOUGYOU:
            self._counter_primary_acquired = True
        return super()._after_lineup_purchase(name)

    def deploy_shikigami_from_hand(self):
        if not self._uses_counter_ubume():
            return super().deploy_shikigami_from_hand()
        deployed = []
        if not self._ensure_shop_closed():
            return deployed
        for _ in range(self.HAND_DEPLOY_SAFETY_LIMIT):
            if not self._inventory_action_allowed(('备',), reserve=3, refresh=False):
                return deployed
            inventory = self._card_inventory
            level = self._read_level()
            if level is None:
                return deployed
            self._counter_primary_acquired = (getattr(self, '_counter_primary_acquired', False)
                                              or plan.has_primary(inventory))
            # 拿到寻香行后回收河童，确认寻香行上阵前不出售过渡战力。
            if self._counter_substitution_needed():
                if not self._recall_inventory_unit(5):
                    return deployed
                continue
            excessive_kujira = next((i for i, u in inventory.board.items()
                                     if u.name == plan.KUJIRA and u.star == 3), None)
            if excessive_kujira is not None and self._chess_sale_allowed():
                if not self._recall_inventory_unit(excessive_kujira):
                    return deployed
                continue
            if self._chess_sale_allowed() and any(c.name == plan.KUJIRA and c.star == 3 for c in inventory.hand):
                self._sell_excess_inventory_cards(('备',))
                continue
            candidates = plan.missing_deployments(level, inventory, self._counter_primary_acquired)
            if not candidates:
                self._sell_excess_inventory_cards(('备',))
                return deployed
            for slot in candidates:
                cards = [c for c in inventory.hand if c.name == slot['name'] and c.star is not None
                         and (c.name != plan.KUJIRA or c.star <= 2)]
                if cards:
                    break
            else:
                return deployed
            card = min(cards, key=lambda c: (-c.star, c.position[0]))
            self._counter_deploy_target = (slot['name'], slot['position'])
            try:
                if not self.deploy_shikigami_hand_card(slot['name'], card.position):
                    return deployed
            finally:
                self._counter_deploy_target = None
            self._sync_inventory_board_names()
            self._board_shikigami_attributes.setdefault(self._counter_unit_key(slot['name'], slot['position']),
                                                        (None, None, None))
            deployed.append(slot['name'])
            logger.info(f'反击姑获鸟上阵: {self._shikigami_display_name(slot["name"])} '
                        f'{card.star}星 -> {slot["position"]}号位')
        return deployed

    def _inventory_card_excess(self, card):
        if not self._uses_counter_ubume():
            return super()._inventory_card_excess(card)
        inventory = self._card_inventory
        if card.name == plan.KAPPA:
            # 只有寻香行已实际在前3站稳，才清掉全部过渡河童。
            unit = inventory.board.get(5)
            return (inventory.ready and card.star is not None and unit is not None
                    and unit.name == plan.JINKOUGYOU and unit.star_confirmed)
        if card.name == plan.KUJIRA:
            # 两张二星都保留；材料数封顶6，不能按单个二星目标清理。
            if inventory.ready and card.star == 3 and card.name not in inventory.uncertain:
                return True
            return inventory.excess(card, 2, target_count=2)
        if card.name == plan.GASHADOKURO:
            level = self._read_level()
            if level is None:
                return False
            return inventory.excess(card, 1 if level < 8 else 3)
        return super()._inventory_card_excess(card)

    def _inventory_needs_upgrade(self, unit, hand):
        if self._uses_counter_ubume() and unit.name == plan.KUJIRA:
            return unit.star == 1 and any(c.name == plan.KUJIRA and c.star == 2 for c in hand)
        return super()._inventory_needs_upgrade(unit, hand)

    def _read_lineup_capacity_status(self):
        if not self._uses_counter_ubume():
            return super()._read_lineup_capacity_status()
        level = self._read_level()
        if level is None:
            return None
        units = [u for u in self._card_inventory.board.values() if not u.special]
        return {'current': len(units), 'capacity': level, 'level': level,
                'deployed_names': {u.name for u in units},
                'player_positions': set(self._card_inventory.board),
                'arakawa_goldfish': False, 'full': len(units) >= level}

    @staticmethod
    def _counter_unit_key(name, position):
        return f'{name}@{position}'

    def _shikigami_name_at_set(self, position):
        if not self._uses_counter_ubume():
            return super()._shikigami_name_at_set(position)
        unit = self._card_inventory.board.get(position)
        return self._counter_unit_key(unit.name, position) if unit is not None and unit.name else None

    def _counter_equipment_attributes(self):
        return {p: self._shikigami_attributes(self._counter_unit_key(u.name, p))
                for p, u in self._card_inventory.board.items() if not u.special and u.name is not None}

    def _soul_hand_priority(self, candidate):
        if not self._uses_counter_ubume():
            return super()._soul_hand_priority(candidate)
        ranks = {'yingshengchong': 0, 'zheng': 1, 'huoling': 2, 'zhaocaimao': 2}
        return ranks.get(candidate['name'], 3), candidate['position'][0]

    def _soul_targets(self, soul_name, category, verified_names):
        if not self._uses_counter_ubume():
            return super()._soul_targets(soul_name, category, verified_names)
        if not self._card_inventory.ready:
            return []
        board = self._card_inventory.board
        attributes = self._counter_equipment_attributes()
        valid = {p: u for p, u in board.items() if not u.special and u.name in verified_names
                 and plan.can_equip(p, soul_name, board, attributes)}
        if category == 'attack':
            order = plan.ATTACK_ORDER
            positions = sorted((p for p, u in valid.items() if u.name in order),
                               key=lambda p: (order.index(valid[p].name), p))
            exclusive = plan.UBUME if soul_name == 'yingshengchong' else None
        elif soul_name == 'zheng' or soul_name in plan.DEFENSIVE_SOULS:
            order = plan.FRONTLINE
            positions = sorted((p for p, u in valid.items() if p % 2 == 1),
                               key=lambda p: (order.index(valid[p].name) if valid[p].name in order else len(order), p))
            exclusive = 'kuro_douji' if soul_name == 'zheng' else None
        elif soul_name in plan.KUJIRA_SOULS:
            positions = sorted((p for p, u in valid.items() if u.name == plan.KUJIRA))
            positions += sorted(p for p, u in valid.items() if p % 2 == 1)
            exclusive = plan.KUJIRA
        else:
            # 魍魉/钓瓶火/木魅等其他功能魂保留原前排站位顺序。
            positions = sorted(p for p in valid if p % 2 == 1)
            exclusive = None
        if exclusive is not None:
            worn = any(u.name == exclusive and soul_name in attributes.get(p, (None, None, None))[1:]
                       for p, u in board.items())
            preferred = [p for p in positions if valid[p].name == exclusive]
            if preferred:
                # 专属尚未装好时先锁定目标；装好后，多余同类再按其余顺序。
                positions = preferred + [p for p in positions if p not in preferred]
            elif not worn:
                count = sum(c['name'] == soul_name for c in self._soul_hand_cards())
                if count <= 1:
                    return []  # 保留最后一张，等待指定单位上阵或装备位恢复。
        return [(p, self._soul_target_position(p)) for p in positions]

    def _emblem_targets(self, emblem_name, verified_names):
        if not self._uses_counter_ubume():
            return super()._emblem_targets(emblem_name, verified_names)
        if not self._card_inventory.ready:
            return []
        bond = grigri_bond_name(emblem_name)
        if bond is None or not any(bond in SHIKIGAMI_BONDS_BY_ROMAJI.get(u.name, ())
                                  for u in self._card_inventory.board.values()):
            return []
        targets = []
        attributes = self._counter_equipment_attributes()
        for position, unit in sorted(self._card_inventory.board.items()):
            if unit.special or unit.name not in verified_names or bond in SHIKIGAMI_BONDS_BY_ROMAJI.get(unit.name, ()):
                continue
            key = self._counter_unit_key(unit.name, position)
            _, first, second = self._shikigami_attributes(key)
            if (first is None or second is None) and plan.can_equip(
                    position, emblem_name, self._card_inventory.board, attributes):
                targets.append((key, position))
        return targets
