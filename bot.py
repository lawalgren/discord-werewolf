# Work with Python 3.6
from discord import *
import random
import math
import signal
import enum
import asyncio


class Phases(enum.Enum):
    Beginning = 0
    First_Night = 1
    Day = 2
    Night = 3


class Roles(enum.Enum):
    Undetermined = 0
    Villager = 1
    Werewolf = 2
    Bodyguard = 3
    Seer = 4
    Mason = 5
    Drunk = 6
    Prince = 7
    Cult_Leader = 8
    PI = 9
    Diseased = 10
    Priest = 11
    Witch = 12
    Aura_Seer = 13
    Tough_Guy = 14
    Mayor = 15
    Apprentice_Seer = 16
    Village_Idiot = 17
    Spellcaster = 18
    Hunter = 19
    Old_Hag = 20
    Vampire = 21
    Fruit_Brute = 22
    Wolf_Cub = 23
    Wolverine = 24
    Dire_Wolf = 25
    Lone_Wolf = 26
    Fang_Face = 27
    Big_Bad_Wolf = 28
    Hoodlum = 29
    Cursed = 30
    Troublemaker = 31
    Sorceress = 32
    Pacifist = 33
    Lycan = 34
    Doppelganger = 35
    Virginia_Woolf = 36
    Minion = 37
    Cupid = 38
    Tanner = 39


class MessageTypes(enum.Enum):
    Target = 0
    Accusation = 1


class Affiliations(enum.Enum):
    Undetermined = 0
    Villagers = 1
    Werewolves = 2
    Vampires = 3
    Tanner = 4
    Lone_Wolf = 5
    Hoodlum = 6
    Cult_Leader = 7


class OneTimeActions(enum.Enum):
    Trouble = 1
    WitchKill = 2
    WitchSave = 3
    Priest = 4
    PI = 5


class Player:
    def __init__(self, object):
        self.object = object
        self.name = object.name.lower()
        self.role = Roles.Undetermined
        self.affiliation = Affiliations.Undetermined
        self.alive = True


class VotingMessage:
    def __init__(self, target, author, message, type):
        self.targeting_wolf = author
        self.target = target
        self.message = message
        self.type = type
        self.confirmations = 0
        self.rejections = 0
        self.voted_players = []


class Werewolf:
    async def accuse(self, message):
        if message.channel == self.channels['town_assembly'] and self.phase == Phases.Day:
            accused_user = self.parse_arguments(message)
            accused_player = self.get_player_by_name(accused_user)
            if accused_player is not None:
                if not accused_player.alive:
                    await self.channels['town_assembly'].send('%s is already dead. Pick someone else' % accused_user)
                    return
                if accused_player.name.lower() == message.author.name.lower():
                    await self.channels['town_assembly'].send('Silly human. You can\'t accuse yourself!')
                    return
                content = "%s has been accused of being a hairy wolf monster. React with 👍 for them to live, " \
                          "💀 for them to die. Poll will close in 30 seconds." % accused_user
                if len(list(filter(lambda x: x.message.content == content, self.messages))) == 0:
                    target_message = await self.channels['town_assembly'].send(content)
                    await target_message.add_reaction('👍')
                    await target_message.add_reaction('💀')
                    self.messages.append(VotingMessage(self.get_player_by_name(accused_user), message.author, target_message,
                                                       MessageTypes.Accusation))
                    await asyncio.sleep(30)
                    if len(list(filter(lambda x: x.message.content == content, self.messages))) != 0:
                        await self.poll_timeout(self.get_message(target_message))

    async def add_user(self, message):
        if self.phase == Phases.Beginning:
            if len(list(filter(lambda x: x.name.lower() == message.author.name.lower(), self.players))) > 0:
                await message.channel.send("A user named %s is already in the game." % message.author.name)
            else:
                self.players.append(Player(message.author))
                await message.channel.send("%s has been successfully added. Number of players: %s" % (
                                           message.author.name, len(self.players)))
        else:
            await message.channel.send("The game has already been started. Wait until a new game is beginning first.")

    async def aura(self, message):
        if self.get_player_by_name(message.author.name).role == Roles.Aura_Seer and Roles.Aura_Seer in \
                self.get_living_roles() and (self.phase == Phases.Night or self.phase == Phases.First_Night) and \
                Roles.Aura_Seer not in self.completed_night_roles:
            target_player = self.get_player_by_name(self.parse_arguments(message))
            if target_player is not None and target_player.alive and target_player.name != message.author.name:
                if target_player.Role != Roles.Villager and target_player.Role != Roles.Werewolf:
                    await message.author.dm_channel.send("%s is not a normal villager or werewolf." %
                                                         target_player.name)
                else:
                    await message.author.dm_channel.send("%s is a normal villager or werewolf." % target_player.name)

                await message.author.dm_channel.send("Join the rest of the town in the town-assembly channel")
                self.completed_night_roles.append(Roles.Aura_Seer)
                await self.check_night_end()

    async def banish(self, message):
        if self.get_player_by_name(message.author.name).role == Roles.Old_Hag and Roles.Old_Hag in \
                self.get_living_roles() and (self.phase == Phases.Night or self.phase == Phases.First_Night) and \
                Roles.Old_Hag not in self.completed_night_roles:
            target_player = self.get_player_by_name(self.parse_arguments(message))
            if target_player is not None and target_player.alive and target_player.name != message.author.name:
                self.banished_player = target_player
                overwrites = PermissionOverwrite()
                overwrites.read_messages = False
                overwrites.send_messages = False
                await target_player.object.dm_channel.send("You have been banished from the town and are no longer "
                                                           "able to read or post in the town assembly for the next "
                                                           "day.")
                await self.channels['town_assembly'].set_permissions(target_player.object, overwrite=None)
                await self.channels['town_assembly'].set_permissions(target_player.object, overwrite=overwrites)

                await message.author.dm_channel.send("%s has been successfully banished.Join the rest of the town in "
                                                     "the town-assembly channel" % target_player.name)

                self.completed_night_roles.append(Roles.Old_Hag)
                await self.check_night_end()

    def check_game_end(self):
        print(self.get_total_living_werewolves(), self.get_total_living_players())
        if self.get_total_living_players() / 2 <= self.get_total_living_werewolves():
            return Affiliations.Werewolves
        elif self.get_total_living_werewolves() <= 0:
            return Affiliations.Villagers
        else:
            return Affiliations.Undetermined

    async def check_day_end(self):
        if self.hunter_killed:
            return
        if not self.villagers_voted:
            return
        await self.night_phase()

    async def check_night_end(self):
        if self.hunter_killed:
            return
        for role in self.get_living_roles():
            if role not in self.completed_night_roles:
                if self.phase == Phases.First_Night:
                    if role == Roles.Bodyguard or role == Roles.Seer or role == Roles.Werewolf or role == Roles.Cupid\
                            or role == Roles.Virginia_Woolf or role == Roles.Sorceress or role == Roles.Dire_Wolf or \
                            role == Roles.Old_Hag or role == Roles.Spellcaster or role == Roles.Aura_Seer:
                        return
                elif self.phase == Phases.Night:
                    if role == Roles.Bodyguard or role == Roles.Seer or role == Roles.Werewolf or role == \
                            Roles.Sorceress or role == Roles.Old_Hag or role == Roles.Spellcaster or role == \
                            Roles.Aura_Seer:
                        return

        await self.day_phase()

    async def companion(self, message):
        if self.get_player_by_name(message.author.name).role == Roles.Dire_Wolf and self.phase == \
                Phases.First_Night and Roles.Dire_Wolf not in self.completed_night_roles:
            target_player = self.get_player_by_name(self.parse_arguments(message))
            if target_player is not None and target_player.name != message.author.name:
                self.direwolf_companion = target_player
                await self.get_player_by_name(message.author.name).object.dm_channel.send("%s is now your companion. "
                                                                                          "If they die, you die." %
                                                                                          target_player.name)
                self.completed_night_roles.append(Roles.Dire_Wolf)
                await self.check_night_end()

    async def day_phase(self):
        if self.tough_guy_wolfed:
            tough_guy = next(self.get_players_by_role(Roles.Tough_Guy))
            await self.channels['town_assembly'].send("%s died last night by wolf fangs." % tough_guy.name)
            self.tough_guy_wolfed = False
            await self.kill_player(tough_guy)

        if Roles.Bodyguard in self.get_living_roles():
            if self.bodyguard_target.name != self.wolf_target.name and self.wolf_target.role != Roles.Tough_Guy and (
                  self.witch_saved is None or (self.witch_saved is not None and self.wolf_target.name !=
                                               self.witch_saved.name)):
                await self.kill_player(self.wolf_target)
                await self.channels['town_assembly'].send(
                    "Day Phase. %s met their end last night by wolf fangs. Whodunit? "
                    "Throw out accusations with !accuse username" % self.wolf_target.name)
                results = self.check_game_end()
                if results is not Affiliations.Undetermined:
                    self.winning_affiliations.append(results)
                    await self.end()
            else:
                if self.wolf_target.role == Roles.Tough_Guy:
                    self.tough_guy_wolfed = True
                await self.channels['town_assembly'].send("Day Phase. The wolves' initial target was saved during the "
                                                          "night. Accuse potential wolves with !accuse username")
#TODO                if self.wolf_target.name != self
        else:
            if self.wolf_target.role != Roles.Tough_Guy:
                await self.kill_player(self.wolf_target)
                await self.channels['town_assembly'].send(
                        "Day Phase. %s met their end last night by wolf fangs. Whodunit? "
                        "Throw out accusations with !accuse username" % self.wolf_target.name)
            else:
                self.tough_guy_wolfed = True
                await self.channels['town_assembly'].send("Day Phase. The wolves' initial target was saved during the "
                                                          "night. Accuse potential wolves with !accuse username")

        if self.second_wolf_target is not None:
            if (Roles.Bodyguard in self.get_living_roles and self.bodyguard_target.name ==
                    self.second_wolf_target.name) or self.second_wolf_target.role == Roles.Tough_Guy:
                await self.channels['town_assembly'].send(
                    "A second person was targeted for death but was saved during the night.")
                if self.second_wolf_target.role == Roles.Tough_Guy:
                    self.tough_guy_wolfed = True
            else:
                await self.channels['town_assembly'].send(
                    "%s died last night by wolf fangs." % self.second_wolf_target.name)
                await self.kill_player(self.second_wolf_target)
            self.second_wolf_target = None

        result = self.check_game_end()
        print(result.name)
        if result != Affiliations.Undetermined:
            self.winning_affiliations.append(result)
            await self.end()

        if Roles.Fang_Face in self.get_living_roles():
            if self.phase == Phases.First_Night:
                overwrites = PermissionOverwrite()
                overwrites.send_messages = False
                overwrites.read_messages = False
                await self.channels['wolf_den'].set_permissions(next(self.get_players_by_role(Roles.Fang_Face)).object,
                                                                overwrite=None)
                await self.channels['wolf_den'].set_permissions(next(self.get_players_by_role(Roles.Fang_Face)).object,
                                                                overwrite=overwrites)
            if self.get_living_werewolves() == 1:
                overwrites = PermissionOverwrite()
                overwrites.send_messages = True
                overwrites.read_messages = True
                await self.channels['wolf_den'].set_permissions(next(self.get_players_by_role(Roles.Fang_Face)).object,
                                                                overwrite=None)
                await self.channels['wolf_den'].set_permissions(next(self.get_players_by_role(Roles.Fang_Face)).object,
                                                                overwrite=overwrites)

        self.wolf_target = ""
        self.bodyguard_target = ""
        self.completed_night_roles = []
        self.phase = Phases.Day

    async def end(self):
        if self.hoodlum_players != () and Roles.Hoodlum in self.get_living_roles() and not \
                self.hoodlum_players[0].alive and not self.hoodlum_players[1].alive:
            self.winning_affiliations.append(Affiliations.Hoodlum)

        if Roles.Lone_Wolf in self.get_living_roles() and self.get_total_living_werewolves() == 1 and Roles.Werewolf \
                in self.winning_affiliations:
            self.winning_affiliations.append(Affiliations.Lone_Wolf)

        for victor in self.winning_affiliations:
            if victor == Affiliations.Werewolves:
                await self.channels['town_assembly'].send(
                    "The werewolves have taken control of the town and can finally start the dentistry shop they always"
                    " wanted. Human meat is a massive pain to remove from your teeth!\nWinning players:")
                for player in self.get_players_by_affiliation(Affiliations.Werewolves):
                    await self.channels['town_assembly'].send(player.name)
            elif victor == Affiliations.Villagers:
                await self.channels['town_assembly'].send(
                    "The townspeople heave a collective sigh of relief as they put down the last hairy abomination. "
                    "This is Medieval Europe, after all. What need have you of dentistry?\nWinning players:")
                for player in self.get_players_by_affiliation(Affiliations.Villagers):
                    await self.channels['town_assembly'].send(player.name)
            elif victor == Affiliations.Tanner:
                await self.channels['town_assembly'].send("The tanner, %s, wanted nothing more than to end his "
                                                          "miserable existence and, lo and behold, he did." %
                                                          next(self.get_players_by_affiliation(
                                                              Affiliations.Tanner)).name)
            elif victor == Affiliations.Hoodlum:
                await self.channels['town_assembly'].send("The hoodlum, %s, had two goals: kill %s and %s, "
                                                          "and stay alive until the end of the game. They managed "
                                                          "both." % (next(self.get_players_by_affiliation(
                                                                     Affiliations.Hoodlum)).name,
                                                                     self.hoodlum_players[0].name,
                                                                     self.hoodlum_players[1].name))

            elif victor == Affiliations.Lone_Wolf:
                await self.channels['town_assembly'].send("The lone wolf, %s, wanted to be the last werewolf alive "
                                                          "during a wolf victory. He managed." %
                                                          next(self.get_players_by_affiliation(
                                                              Affiliations.Lone_Wolf)).name)

    async def ensorcell(self, message):
        if self.get_player_by_name(message.author.name).role == Roles.Sorceress and Roles.Sorceress in \
                self.get_living_roles() and (self.phase == Phases.Night or self.phase == Phases.First_Night) and \
                Roles.Sorceress not in self.completed_night_roles:
            target_player = self.get_player_by_name(self.parse_arguments(message))
            if target_player is not None and target_player.alive and target_player.name != message.author.name:
                if target_player.Role == Roles.Seer:
                    await message.author.dm_channel.send("%s is the Seer." % target_player.name)
                else:
                    await message.author.dm_channel.send("%s is not the Seer." % target_player.name)

                await message.author.dm_channel.send("Join the rest of the town in the town-assembly channel")
                self.completed_night_roles.append(Roles.Sorceress)
                await self.check_night_end()

    def get_total_living_players(self):
        print(len([player for player in self.players if player.alive]))
        return len([player for player in self.players if player.alive])

    def get_total_living_werewolves(self):
        print(len([player for player in self.players if player.role == Roles.Werewolf and player.alive]))
        return len([player for player in self.players if (player.role == Roles.Werewolf or player.role ==
                                                          Roles.Fang_Face or player.role == Roles.Lone_Wolf or
                                                          player.role == Roles.Big_Bad_Wolf or player.role ==
                                                          Roles.Fruit_Brute or player.role == Roles.Wolf_Cub or
                                                          player.role == Roles.Wolverine or player.role ==
                                                          Roles.Dire_Wolf) and player.alive])

    def get_total_living_role(self, role):
        return len([player for player in self.players if player.role == role and player.alive])

    def get_living_roles(self):
        return set([player.role for player in self.players if player.role != Roles.Villager and player.alive])

    def get_role_from_str(self, role_str):
        if role_str == 'Werewolf':
            return Roles.Werewolf
        elif role_str == 'Bodyguard':
            return Roles.Bodyguard
        elif role_str == 'Seer':
            return Roles.Seer
        elif role_str == 'Mason':
            return Roles.Mason
        elif role_str == 'Drunk':
            return Roles.Drunk
        elif role_str == 'Prince':
            return Roles.Prince
        elif role_str == 'Cult Leader':
            return Roles.Cult_Leader
        elif role_str == 'PI':
            return Roles.PI
        elif role_str == "Diseased":
            return Roles.Diseased
        elif role_str == 'Priest':
            return Roles.Priest
        elif role_str == 'Witch':
            return Roles.Witch
        elif role_str == 'Aura Seer':
            return Roles.Aura_Seer
        elif role_str == 'Tough Guy':
            return Roles.Tough_Guy
        elif role_str == 'Mayor':
            return Roles.Mayor
        elif role_str == 'Apprentice Seer':
            return Roles.Apprentice_Seer
        elif role_str == 'Village Idiot':
            return Roles.Village_Idiot
        elif role_str == 'Spellcaster':
            return Roles.Spellcaster
        elif role_str == 'Hunter':
            return Roles.Hunter
        elif role_str == 'Old Hag':
            return Roles.Old_Hag
        elif role_str == 'Vampire':
            return Roles.Vampire
        elif role_str == 'Fruit Brute':
            return Roles.Fruit_Brute
        elif role_str == 'Wolf Cub':
            return Roles.Wolf_Cub
        elif role_str == 'Wolverine':
            return Roles.Wolverine
        elif role_str == 'Dire Wolf':
            return Roles.Dire_Wolf
        elif role_str == 'Lone Wolf':
            return Roles.Lone_Wolf
        elif role_str == 'Fang Face':
            return Roles.Fang_Face
        elif role_str == 'Big Bad Wolf':
            return Roles.Big_Bad_Wolf
        elif role_str == 'Hoodlum':
            return Roles.Hoodlum
        elif role_str == 'Cursed':
            return Roles.Cursed
        elif role_str == 'Troublemaker':
            return Roles.Troublemaker
        elif role_str == 'Sorceress':
            return Roles.Sorceress
        elif role_str == 'Pacifist':
            return Roles.Pacifist
        elif role_str == 'Lycan':
            return Roles.Lycan
        elif role_str == 'Doppelganger':
            return Roles.Doppelganger
        elif role_str == 'Virginia Woolf':
            return Roles.Virginia_Woolf
        elif role_str == 'Minion':
            return Roles.Minion
        elif role_str == 'Cupid':
            return Roles.Cupid
        elif role_str == 'Tanner':
            return Roles.Tanner
        else:
            return None

    def get_living_werewolves(self):
        return [player.name for player in self.players if player.role == Roles.Werewolf and player.alive]

    def get_bodyguard(self):
        return next(filter(lambda x: x.role == Roles.Bodyguard, self.players))

    def get_seer(self):
        return next(filter(lambda x: x.role == Roles.Seer, self.players))

    def get_player_by_name(self, username):
        try:
            return next(filter(lambda x: x.name == username.lower(), self.players))
        except StopIteration:
            pass

    def get_players_by_affiliation(self, affiliation):
        return filter(lambda x: x.affiliation == affiliation, self.players)

    def get_players_by_role(self, role):
        return filter(lambda x: x.role == role, self.players)

    def get_message(self, message):
        try:
            return next(filter(lambda x: x.message.content == message.content, self.messages))
        except StopIteration:
            return None

    async def hood(self, message):
        if self.phase == Phases.First_Night and message.author.name == next(self.get_players_by_role(
                Roles.Hoodlum)).name:
            player_list = message.content.split(';')
            player1 = self.get_player_by_name(player_list[1])
            player2 = self.get_player_by_name(player_list[2])
            if player1 is not None and player2 is not None and player1.name != player2.name:
                self.hoodlum_players = (player1, player2)
                next(self.get_players_by_role(Roles.Hoodlum)).object.dm_channel.send("You have successfully chosen %s "
                                                                                     "and %s for your targets. To win, "
                                                                                     "ensure you live and both these "
                                                                                     "players die. Join the rest of the"
                                                                                     " town in #town-assembly" %
                                                                                     (player1.name, player2.name))
            self.completed_night_roles.append(Roles.Hoodlum)
            await self.check_night_end()

    async def hunt(self, message):
        hunter = next(self.get_players_by_role(Roles.Hunter))
        if message.author.name == hunter.name and self.hunter_killed:
            target_player = self.get_player_by_name(self.parse_arguments(message))
            if target_player is not None and target_player.alive and target_player.name != hunter.name:
                await self.kill_player(target_player)
                next(self.get_players_by_role(Roles.Hunter)).object.dm_channel.send("You have successfully killed "
                                                                                    "%s." % target_player.name)
                self.hunter_killed = False
                if self.phase == Phases.Night or self.phase == Phases.First_Night:
                    await self.check_night_end()
                else:
                    await self.check_day_end()

    async def intimidate(self, message):
        if self.get_player_by_name(message.author.name).role == Roles.Virginia_Woolf and self.phase == \
                Phases.First_Night and Roles.Virginia_Woolf not in self.completed_night_roles:
            target_player = self.get_player_by_name(self.parse_arguments(message))
            if target_player is not None and target_player.name != message.author.name:
                self.intimidated_player = target_player
                await self.get_player_by_name(message.author.name).object.dm_channel.send("You have successfully "
                                                                                          "intimidated %s. Now join "
                                                                                          "the rest of the town in "
                                                                                          "#town-assembly" %
                                                                                          target_player.name)
                self.completed_night_roles.append(Roles.Virginia_Woolf)
                await self.check_night_end()

    async def investigate(self, message):
        if self.get_player_by_name(message.author.name).role == Roles.Seer and Roles.Seer in self.get_living_roles() \
                and (self.phase == Phases.Night or self.phase == Phases.First_Night) and Roles.Seer not in \
                     self.completed_night_roles:
            target_player = self.get_player_by_name(self.parse_arguments(message))
            if target_player is not None and target_player.alive and target_player.name != message.author.name:
                if target_player.role == Roles.Werewolf or target_player.role == Roles.Lycan:
                    await message.author.dm_channel.send("%s is a werewolf." % target_player.name)
                else:
                    await message.author.dm_channel.send("%s is a human." % target_player.name)

                await message.author.dm_channel.send("Join the rest of the town in the town-assembly channel")
                self.completed_night_roles.append(Roles.Seer)
                await self.check_night_end()

    async def kill_player(self, player):
        player.alive = False
        if player.role == Roles.Tanner:
            await player.object.dm_channel.send("You win! Stick around until the end of the game for public "
                                                "acknowledgement of that fact.")
            self.winning_affiliations.append(Affiliations.Tanner)

        read_only = PermissionOverwrite()
        read_only.send_messages = False
        read_only.read_messages = True
        read_only.add_reactions = False

        lock_out = PermissionOverwrite()
        lock_out.send_messages = False
        lock_out.read_messages = False
        lock_out.add_reactions = False

        full = PermissionOverwrite()
        full.send_messages = True
        full.read_messages = True
        full.add_reactions = True

        await player.object.remove_roles(self.roles['player'])
        await player.object.add_roles(self.roles['dead'])
        await self.channels['wolf_den'].set_permissions(player.object, overwrite=None)
        await self.channels['town_assembly'].set_permissions(player.object, overwrite=None)
        await self.channels['astral_plane'].set_permissions(player.object, overwrite=None)
        await self.channels['rock_buddies'].set_permissions(player.object, overwrite=None)
        await self.channels['wolf_den'].set_permissions(player.object, overwrite=read_only)
        await self.channels['town_assembly'].set_permissions(player.object, overwrite=read_only)
        await self.channels['astral_plane'].set_permissions(player.object, overwrite=full)
        await self.channels['rock_buddies'].set_permissions(player.object, overwrite=read_only)
        await player.object.dm_channel.send("You are dead! Say hello to all your ghost friends!")

        if self.linked_players != ():
            (player1, player2) = self.linked_players
            if player.name == player1.name:
                await self.channels['town_assembly'].send("%s was so madly in love with %s that they were no longer "
                                                          "able to continue living." % (player2.name, player1.name))
                self.linked_players = ()
                await self.kill_player(player2)

            elif player.name == player2.name:
                await self.channels['town_assembly'].send("%s was so madly in love with %s that they were no longer "
                                                          "able to continue living." % (player1.name, player2.name))
                self.linked_players = ()
                await self.kill_player(player1)

        if player.role == Roles.Virginia_Woolf and self.intimidated_player is not None:
            await self.channels['town_assembly'].send("%s was so afraid of %s that they died in fright of anything "
                                                      "that could take her out." % (self.intimidated_player.name,
                                                                                    player.name))
            await self.kill_player(self.intimidated_player)

        if Roles.Dire_Wolf in self.get_living_roles() and self.direwolf_companion is not None and player.name == \
                self.direwolf_companion.name:
            direwolf = next(self.get_players_by_role(Roles.Dire_Wolf))
            await self.channels['town_assembly'].send("When %s died, their direwolf companion %s died also." %
                                                      (player.name, direwolf.name))
            await self.kill_player(direwolf)

        if player.role == Roles.Wolf_Cub:
            self.cub_death = True

        if player.role == Roles.Hunter:
            await player.object.dm_channel.send("You have been killed and have gained the ability to kill another "
                                                "player. Do so by replying with the command !hunt username e.g. "
                                                "`!hunt Lucas_Walgren`")
            self.hunter_killed = True

    async def link(self, message):
        if self.phase == Phases.First_Night and message.author.name == next(self.get_players_by_role(Roles.Cupid)).name:
            player_list = message.content.split(';')
            player1 = self.get_player_by_name(player_list[1])
            player2 = self.get_player_by_name(player_list[2])
            print(player1.name, player2.name)
            if player1 is not None and player2 is not None and player1.name != player2.name:
                self.linked_players = (player1, player2)
                await next(self.get_players_by_role(Roles.Cupid)).object.dm_channel.send("You have successfully linked "
                                                                                         "%s and %s. Join the rest of "
                                                                                         "the town in #town-assembly"
                                                                                         % (player1.name, player2.name))
            self.completed_night_roles.append(Roles.Cupid)
            await self.check_night_end()

    async def night_phase(self):
        if self.phase != Phases.First_Night:
            self.phase = Phases.Night

        if self.get_total_living_werewolves() == 1 and Roles.Fruit_Brute in self.get_living_roles():
            await self.channels['wolf_den'].send("The Fruit Brute is the only remaining wolf, so he can no longer "
                                                 "eliminate players at night.")
            self.completed_night_roles.append(Roles.Werewolf)
        else:
            await self.channels['wolf_den'].send("Hello wolves. Pick a target for death by sending a message in this "
                                                 "channel with the command !target username. e.g. "
                                                 "`!target Lucas_Walgren`")

        await self.channels['town_assembly'].send(
            "Night Phase. One of you will die tonight. Best come to terms with that...")

        if self.banished_player is not None and self.banished_player.alive:
            overwrites = PermissionOverwrite()
            overwrites.read_messages = True
            overwrites.send_messages = True
            await self.channels['town_assembly'].set_permissions(self.banished_player.object, overwrite=None)
            await self.channels['town_assembly'].set_permissions(self.banished_player.object, overwrite=overwrites)
            await self.banished_player.object.dm_channel.send("You are now able to access town assembly again.")
            self.banished_player = None

        if self.silenced_player is not None and self.silenced_player.alive:
            overwrites = PermissionOverwrite()
            overwrites.read_messages = True
            overwrites.send_messages = True
            await self.channels['town_assembly'].set_permissions(self.silenced_player.object, overwrite=None)
            await self.channels['town_assembly'].set_permissions(self.silenced_player.object, overwrite=overwrites)
            await self.silenced_player.object.dm_channel.send("You are now able to post in town assembly again.")
            self.silenced_player = None

        if Roles.Bodyguard in self.get_living_roles():
            bodyguard = self.get_bodyguard()
            await bodyguard.object.dm_channel.send("Save someone tonight by replying to this message"
                                                   " with !save username. e.g. `!save Lucas_Walgren` If the wolves "
                                                   "try to kill this person, they will not die. You can save yourself.")
        if Roles.Seer in self.get_living_roles():
            seer = self.get_seer()
            await seer.object.dm_channel.send("Investigate someone tonight by replying to this message"
                                              " with !investigate username. e.g. `!investigate Lucas_Walgren` I will "
                                              "tell you if they are on the side of the wolves or the villagers.")
        if Roles.Sorceress in self.get_living_roles():
            sorc = next(self.get_players_by_role(Roles.Sorceress))
            await sorc.object.dm_channel.send("Investigate someone tonight by replying to this message with "
                                              "!ensorcell username. e.g. `!ensorcell Lucas_Walgren`. I will tell you "
                                              "if that person is the seer.")

        if Roles.Troublemaker in self.get_living_roles() and OneTimeActions.Trouble not in self.one_time_use:
            troub = next(self.get_players_by_role(Roles.Troublemaker))
            await troub.object.dm_channel.send("If you want to call for trouble tonight, use the command `!trouble`. "
                                               "If you do, 2 people will have to be lynched tomorrow before moving "
                                               "on. You can use this command once per game")

        if Roles.Old_Hag in self.get_living_roles():
            hag = next(self.get_players_by_role(Roles.Old_Hag))
            await hag.object.dm_channel.send("Banish someone tonight by replying to this message with "
                                             "!banish username. e.g. `!banish Lucas_Walgren`. That person will not "
                                             "be able to read or participate in the town assembly chat until the "
                                             "next day")

        if Roles.Spellcaster in self.get_living_roles():
            spell = next(self.get_players_by_role(Roles.Spellcaster))
            await spell.object.dm_channel.send("Silence someone tonight by replying to this message with "
                                               "!silence username. e.g. `!silence Lucas_Walgren`. That person will not "
                                               "be able to speak in the town assembly chat until the next day")

        if Roles.Aura_Seer in self.get_living_roles():
            aura = next(self.get_players_by_role(Roles.Aura_Seer))
            await aura.object.dm_channel.send("Investigate someone tonight by replying to this message with !aura "
                                              "username e.g. `!aura Lucas_Walgren` and I will tell you whether that "
                                              "person is a normal villager or werewolf.")

        if Roles.Witch in self.get_living_roles():
            witch = next(self.get_players_by_role(Roles.Aura_Seer))
            if not(OneTimeActions.WitchKill in self.one_time_use or OneTimeActions.WitchSave in self.one_time_use):
                await witch.object.dm_channel.send("Save or kill someone tonight using !witchkill username or !witchsave "
                                                   "username e.g. `!witchkill Lucas_Walgren` to kill Lucas_Walgren or "
                                                   "`!witchsave Lucas_Walgren` to protect Lucas_Walgren")
            elif OneTimeActions.WitchKill in self.one_time_use:
                await witch.object.dm_channel.send("You have already used your kill action this game. You can still "
                                                   "choose to save someone tonight with !witchsave username e.g. "
                                                   "`!witchsave Lucas_Walgren`")
            elif OneTimeActions.WitchSave in self.one_time_use:
                await witch.object.dm_channel.send("You have already used your save action this game. You can still "
                                                   "choose to kill someone tonight with !witchkill username e.g. "
                                                   "`!witchkill Lucas_Walgren`")

    @staticmethod
    def parse_arguments(message):
        first_space = message.content.find(' ')
        return message.content[first_space + 1::]

    async def poll_timeout(self, message):
        if message.rejections > message.confirmations:
            await self.kill_player(message.target)
            await self.channels['town_assembly'].send(
                "You have successfully lynched %s. I bet your parents are proud of "
                "you." % message.target.name)
            self.messages.remove(message)
            if not self.troublemaking:
                result = self.check_game_end()
                if result == Affiliations.Undetermined:
                    self.villagers_voted = True
                    await self.check_day_end()
                else:
                    self.winning_affiliations.append(result)
                    await self.end()
            else:
                await self.channels['town_assembly'].send("The troublemaker has called for a second "
                                                          "elimination to happen today. Eliminate "
                                                          "another person to continue to the next "
                                                          "night.")
                self.troublemaking = False

        else:
            await self.channels['town_assembly'].send(
                "You have failed to lynch %s. How does that make you feel?" % message.target.name)
            self.messages.remove(message)

    async def reaction_handler_add(self, reaction, user):
        message_str = reaction.message
        message = self.get_message(message_str)
        # print(message_str.content)
        print([x.message.content for x in self.messages])
        # print(message.message.content)
        player = self.get_player_by_name(user.name)
        if message is not None:
            if message.type == MessageTypes.Target:
                if player.name.lower() != message.targeting_wolf.name.lower() and player.alive and reaction.emoji == \
                        '👍':
                    message.confirmations += 1
                    message.voted_players.append(player)
                    if message.confirmations >= self.get_total_living_werewolves() - 1:
                        if self.cub_death and self.wolf_target is not None:
                            self.second_wolf_target = message.target
                            self.cub_death = False
                        else:
                            self.wolf_target = message.target
                        self.completed_night_roles.append(Roles.Werewolf)
                        await self.channels['wolf_den'].send(
                            "You have successfully confirmed %s as your target. Good wolfie. Join the rest of the "
                            "town in #town-assembly" %
                            message.target.name)
                        if self.cub_death:
                            await self.channels['wolf_den'].send(
                            "The wolf cub has died, so you get a second target for tonight.")
                            return
                        await self.check_night_end()
                        """
                        await self.kill_player(message.target)
                        await self.channels['wolf_den'].send(
                            "You have successfully mauled %s. Good wolfie." % message.target.name)
                        result = self.check_game_end()
                        if result == Roles.Undetermined:
                            await self.day_phase(message.target)
                        else:
                            await self.end(result)
                        """
            elif message.type == MessageTypes.Accusation:
                print(message.confirmations, message.rejections, len(message.voted_players), reaction.emoji,
                      player.name)
                if player not in message.voted_players and player.alive:
                    if reaction.emoji == '👍':
                        if player.role != Roles.Village_Idiot:
                            if player.role == Roles.Mayor:
                                message.confirmations += 2
                            else:
                                message.confirmations += 1
                            message.voted_players.append(player)
                            print('voted_up')
                    elif reaction.emoji == '💀':
                        if player.role != Roles.Pacifist:
                            if player.role == Roles.Mayor:
                                message.rejections += 2
                            else:
                                message.rejections += 1
                            message.voted_players.append(player)
                        print("voted_down")
                    # else:
                    # await reaction.remove(user)
                    if len(message.voted_players) >= (self.get_total_living_players() if self.banished_player is None
                            else self.get_total_living_players() - 1):
                        if message.rejections > message.confirmations:
                            await self.kill_player(message.target)
                            await self.channels['town_assembly'].send(
                                "You have successfully lynched %s. I bet your parents are proud of "
                                "you." % message.target.name)
                            self.messages.remove(message)
                            if not self.troublemaking:
                                result = self.check_game_end()
                                if result == Affiliations.Undetermined:
                                    self.villagers_voted = True
                                    await self.check_day_end()
                                else:
                                    self.winning_affiliations.append(result)
                                    await self.end()
                            else:
                                await self.channels['town_assembly'].send("The troublemaker has called for a second "
                                                                          "elimination to happen today. Eliminate "
                                                                          "another person to continue to the next "
                                                                          "night.")
                                self.troublemaking = False

                        else:
                            await self.channels['town_assembly'].send(
                                "You have failed to lynch %s. How does that make you feel?" % message.target.name)
                            self.messages.remove(message)

    async def reaction_handler_remove(self, reaction, user):
        message_str = reaction.message
        message = self.get_message(message_str)
        # print(message.message.content)
        player = self.get_player_by_name(user)
        if message is not None:
            if message.type == MessageTypes.Target:
                if player != message.author and reaction.emoji == '👍':
                    message.confirmations -= 1
                    message.voted_players.remove(player)
            elif message.type == MessageTypes.Accusation:
                if reaction.emoji == '👍':
                    message.confirmations -= 1
                    message.voted_players.remove(player)
                elif reaction.emoji == '👎':
                    message.rejections -= 1
                    message.voted_players.remove(player)

    async def reset(self, message):
        if not message.author.guild_permissions.administrator:
            return
        for channel in self.channels.values():
            await channel.delete()
        for role in self.roles.values():
            await role.delete()

    async def save(self, message):
        if self.get_player_by_name(message.author.name).role == Roles.Bodyguard and Roles.Bodyguard in self.get_living_roles()\
                and (self.phase == Phases.Night or self.phase == Phases.First_Night):
            target_player = self.get_player_by_name(self.parse_arguments(message))
            if target_player is not None:
                self.bodyguard_target = target_player
                self.completed_night_roles.append(Roles.Bodyguard)
                await message.author.dm_channel.send("You have chosen to save %s." % target_player.name)
                await self.check_night_end()

    def setup(self, message):
        if message.channel != self.channels['game_setup']:
            return
        message_arr = message.content.split(';')
        role = self.get_role_from_str(message_arr[1])
        num = message_arr[2]
        if role is not None:
            self.desired_roles[role] = int(num)
        if int(num) == 0:
            del(self.desired_roles[role])

    async def silence(self, message):
        if self.get_player_by_name(message.author.name).role == Roles.Spellcaster and Roles.Spellcaster in \
                self.get_living_roles() and (self.phase == Phases.Night or self.phase == Phases.First_Night) and \
                Roles.Spellcaster not in self.completed_night_roles:
            target_player = self.get_player_by_name(self.parse_arguments(message))
            if target_player is not None and target_player.alive and target_player.name != message.author.name:
                self.silenced_player = target_player
                overwrites = PermissionOverwrite()
                overwrites.send_messages = False

                await target_player.object.dm_channel.send("You have been silenced and are no longer "
                                                           "able to post in the town assembly for the next day.")

                await self.channels['town_assembly'].set_permissions(target_player.object, overwrite=None)
                await self.channels['town_assembly'].set_permissions(target_player.object, overwrite=overwrites)

                await message.author.dm_channel.send("%s has been successfully silenced.Join the rest of the town in "
                                                     "the town-assembly channel" % target_player.name)

                self.completed_night_roles.append(Roles.Spellcaster)
                await self.check_night_end()

    async def initialize(self, message):
        if not message.author.guild_permissions.administrator:
            return
        self.players = []
        self.linked_players = ()
        self.hoodlum_players = ()
        self.intimidated_player = None
        self.direwolf_companion = None
        self.banished_player = None
        self.silenced_player = None
        self.cub_death = False
        self.second_wolf_target = None
        self.troublemaking = False
        self.tough_guy_wolfed = False
        self.hunter_killed = False
        self.witch_killed = None
        self.witch_saved = None
        self.villagers_voted = False
        self.one_time_use = []
        self.messages = []
        self.channels = {}
        self.winning_affiliations = []
        self.roles = {}
        self.desired_roles = {Roles.Bodyguard: 1, Roles.Seer: 1, Roles.Werewolf: -1}
        self.phase = Phases.Beginning
        self.guild = message.guild
        self.completed_night_roles = []

        overwrites = PermissionOverwrite()
        overwrites.read_messages = False

        dead = PermissionOverwrite()
        dead.read_messages = True
        dead.send_messages = False
        dead.add_reactions = False

        for player_role in self.guild.roles:
            if player_role.name == 'Werewolf player' or player_role.name == 'Dead person':
                await player_role.delete()
        self.roles['player'] = await self.guild.create_role(name='Werewolf player', hoist=True, color=Color.green())
        self.roles['dead'] = await self.guild.create_role(name='Dead person', hoist=True)

        for channel in self.guild.channels:
            if channel.name == 'the-wolf-den' or channel.name == 'town-assembly' or channel.name == 'the-astral-plane' \
                    or channel.name == 'game-setup' or channel.name == 'rock-buddies':
                await channel.delete()
        self.channels['wolf_den'] = await self.guild.create_text_channel("the-wolf-den", overwrite=None)
        await self.channels['wolf_den'].set_permissions(self.roles['player'], overwrite=overwrites)
        await self.channels['wolf_den'].set_permissions(self.roles['dead'], overwrite=dead)
        self.channels['town_assembly'] = await self.guild.create_text_channel("town-assembly", overwrite=None)
        await self.channels['town_assembly'].set_permissions(self.roles['dead'], overwrite=dead)
        self.channels['astral_plane'] = await self.guild.create_text_channel("the-astral-plane",
                                                                                 overwrite=None)
        await self.channels['astral_plane'].set_permissions(self.roles['player'], overwrite=overwrites)
        await self.channels['astral_plane'].set_permissions(self.roles['dead'], overwrite=None)
        self.channels['game_setup'] = await self.guild.create_text_channel("game-setup", overwrite=None)
        await self.channels['game_setup'].set_permissions(self.roles['player'], overwrite=overwrites)
        await self.channels['game_setup'].set_permissions(self.roles['dead'], overwrite=overwrites)
        await self.channels['game_setup'].set_permissions(self.guild.default_role, overwrite=overwrites)
        self.channels['rock_buddies'] = await self.guild.create_text_channel("rock-buddies", overwrite=None)
        await self.channels['rock_buddies'].set_permissions(self.roles['player'], overwrite=overwrites)
        await self.channels['rock_buddies'].set_permissions(self.roles['dead'], overwrite=dead)

        await message.channel.send(
            "Thanks for trying out my Werewolf bot. To start, everyone who wants to play should run the "
            "command !addme and then someone with admin privileges should run !start")

    async def start(self, message):
        # randomly pick wolves
        if message.channel != self.channels['game_setup']:
            return

        overwrites = PermissionOverwrite()
        overwrites.send_messages = True
        overwrites.read_messages = True

        if self.desired_roles[Roles.Werewolf] < 0:
            if len(self.players) == 3:
                num_wolves = 1
            else:
                num_wolves = len(self.players) // 3
        else:
            num_wolves = self.desired_roles[Roles.Werewolf]
        while self.get_total_living_werewolves() < num_wolves:
            next_wolf = random.choice(self.players)
            next_wolf.role = Roles.Werewolf
            next_wolf.affiliation = Affiliations.Werewolves
            await self.channels['wolf_den'].set_permissions(next_wolf.object, overwrite=None)
            await self.channels['wolf_den'].set_permissions(next_wolf.object, overwrite=overwrites)

        if Roles.Bodyguard in self.desired_roles:
            bodyguard = random.choice(self.players)
            while bodyguard.role != Roles.Undetermined:
                bodyguard = random.choice(self.players)
            bodyguard.role = Roles.Bodyguard
            bodyguard.affiliation = Affiliations.Villagers
            if bodyguard.object.dm_channel is None:
                await bodyguard.object.create_dm()
            await bodyguard.object.dm_channel.send("You are the bodyguard. You are on the side of the villagers. "
                                                   "Every night, choose someone to save from the wolves. If they try "
                                                   "to kill this person, that person will not die. You can choose "
                                                   "yourself.")

        if Roles.Seer in self.desired_roles:
            seer = random.choice(self.players)
            while seer.role != Roles.Undetermined:
                seer = random.choice(self.players)
            seer.role = Roles.Seer
            seer.affiliation = Affiliations.Villagers
            if seer.object.dm_channel is None:
                await seer.object.create_dm()
            await seer.object.dm_channel.send("You are the seer. You are on the side of the villagers. Every night"
                                              " investigate a new player and I will tell you if they are a werewolf")

        if Roles.Mason in self.desired_roles:
            num_masons = self.desired_roles[Roles.Mason]
            while self.get_total_living_role(Roles.Mason) < num_masons:
                mason = random.choice(self.players)
                while mason.role != Roles.Undetermined:
                    mason = random.choice(self.players)
                mason.role = Roles.Mason
                mason.affiliation = Affiliations.Villagers
                if mason.object.dm_channel is None:
                    await mason.object.create_dm()
                await mason.object.dm_channel.send("You are a mason. You are on the side of the villagers. You can "
                                                   "freely talk with other masons in the rock-buddies channel")
                await self.channels['rock_buddies'].set_permissions(mason.object, overwrite=None)
                await self.channels['rock_buddies'].set_permissions(mason.object, overwrite=overwrites)

        if Roles.Tanner in self.desired_roles:
            tanner = random.choice(self.players)
            while tanner.role != Roles.Undetermined:
                tanner = random.choice(self.players)
            tanner.role = Roles.Tanner
            tanner.affiliation = Affiliations.Tanner
            if tanner.object.dm_channel is None:
                await tanner.object.create_dm()
            await tanner.object.dm_channel.send("You are the tanner. You hate your job and your life. You win if you "
                                                "are eliminated")

        if Roles.Cupid in self.desired_roles:
            cupid = random.choice(self.players)
            while cupid.role != Roles.Undetermined:
                cupid = random.choice(self.players)
            cupid.role = Roles.Cupid
            cupid.affiliation = Affiliations.Villagers
            if cupid.object.dm_channel is None:
                await cupid.object.create_dm()
            await cupid.object.dm_channel.send("You are the cupid. The first night, choose two players to be in love. "
                                               "If one of them is eliminated, the other is eliminated as well. Link "
                                               "them now with `!link;player1;player2`\nE.g `!link;Lucas_Walgren;Silver`")

        if Roles.Minion in self.desired_roles:
            minion = random.choice(self.players)
            while minion.role != Roles.Undetermined:
                minion = random.choice(self.players)
            minion.role = Roles.Minion
            minion.affiliation = Affiliations.Werewolves
            if minion.object.dm_channel is None:
                await minion.object.create_dm()
            await minion.object.dm_channel.send("You are the minion. You know who the Werewolves are, but you do not "
                                                "wake up with them at night.")
            for wolf_un in self.get_living_werewolves():
                await minion.object.dm_channel.send("%s is a werewolf" % wolf_un)

        if Roles.Virginia_Woolf in self.desired_roles:
            woolf = random.choice(self.players)
            while woolf.role != Roles.Undetermined:
                woolf = random.choice(self.players)
            woolf.role = Roles.Virginia_Woolf
            woolf.affiliation = Affiliations.Villagers
            if woolf.object.dm_channel is None:
                await woolf.object.create_dm()
            await woolf.object.dm_channel.send("You are Virginia Woolf. The first night, choose a player to be afraid "
                                               "of you. If you are eliminated, that player is also eliminated. "
                                               "Intimidate them now with !intimidate username e.g. `!intimidate "
                                               "Lucas_Walgren`")

        if Roles.Lycan in self.desired_roles:
            lycan = random.choice(self.players)
            while lycan.role != Roles.Undetermined:
                lycan = random.choice(self.players)
            lycan.role = Roles.Lycan
            lycan.affiliation = Affiliations.Villagers
            if lycan.object.dm_channel is None:
                await lycan.object.create_dm()
            await lycan.object.dm_channel.send("You are the Lycan. You are a Villager but appear to the Seer as a "
                                               "Werewolf.")

        if Roles.Pacifist in self.desired_roles:
            pacifist = random.choice(self.players)
            while pacifist.role != Roles.Undetermined:
                pacifist = random.choice(self.players)
            pacifist.role = Roles.Pacifist
            pacifist.affiliation = Affiliations.Villagers
            if pacifist.object.dm_channel is None:
                await pacifist.object.create_dm()
            await pacifist.object.dm_channel.send("You are the Pacifist. You must always vote for players to not be "
                                                  "eliminated")

        if Roles.Sorceress in self.desired_roles:
            sorc = random.choice(self.players)
            while sorc.role != Roles.Undetermined:
                sorc = random.choice(self.players)
            sorc.role = Roles.Sorceress
            sorc.affiliation = Affiliations.Werewolves
            if sorc.object.dm_channel is None:
                await sorc.object.create_dm()
            await sorc.object.dm_channel.send("You are the Sorceress. Each night, look for the Seer. You are on the "
                                              "werewolf team.")

        if Roles.Troublemaker in self.desired_roles:
            troub = random.choice(self.players)
            while troub.role != Roles.Undetermined:
                troub = random.choice(self.players)
            troub.role = Roles.Troublemaker
            troub.affiliation = Affiliations.Villagers
            if troub.object.dm_channel is None:
                await troub.object.create_dm()
            await troub.object.dm_channel.send("You are the Troublemaker. One night per game, stir up trouble by "
                                               "calling for two players to be eliminated the following day.")

        if Roles.Hoodlum in self.desired_roles:
            hood = random.choice(self.players)
            while hood.role != Roles.Undetermined:
                hood = random.choice(self.players)
            hood.role = Roles.Hoodlum
            hood.affiliation = Affiliations.Hoodlum
            if hood.object.dm_channel is None:
                await hood.object.create_dm()
            await hood.object.dm_channel.send("You are the Hoodlum. Choose 2 players on the first night. To win, "
                                              "they must be eliminated and you must still be in the game at the end "
                                              "of the game. Choose those players now with the command "
                                              "!hood;player1;player2 e.g. `!hood;Lucas_Walgren;Silver`")
        if Roles.Fang_Face in self.desired_roles:
            fang = random.choice(self.players)
            while fang.role != Roles.Undetermined:
                fang = random.choice(self.players)
            fang.role = Roles.Fang_Face
            fang.affiliation = Affiliations.Werewolves
            if fang.object.dm_channel is None:
                await fang.object.create_dm()
            await fang.object.dm_channel.send("You are Fang Face. The first night, join the chat with the other "
                                              "Werewolves. After the first night, while there are other werewolves in "
                                              "the game, you will not be able to communicate with the other werewolves."
                                              )
            await self.channels['wolf_den'].set_permissions(fang.object, overwrite=None)
            await self.channels['wolf_den'].set_permissions(fang.object, overwrite=overwrites)

        if Roles.Lone_Wolf in self.desired_roles:
            lone = random.choice(self.players)
            while lone.role != Roles.Undetermined:
                lone = random.choice(self.players)
            lone.role = Roles.Lone_Wolf
            lone.affiliation = Affiliations.Lone_Wolf
            if lone.object.dm_channel is None:
                await lone.object.create_dm()
            await lone.object.dm_channel.send("You are the Lone Wolf. Each night, wake with the other Werewolves. "
                                              "You only win if the werewolves win and you are the last remaining "
                                              "Werewolf.")

        if Roles.Dire_Wolf in self.desired_roles:
            dire = random.choice(self.players)
            while dire.role != Roles.Undetermined:
                dire = random.choice(self.players)
            dire.role = Roles.Dire_Wolf
            dire.affiliation = Affiliations.Werewolves
            if dire.object.dm_channel is None:
                await dire.object.create_dm()
            await dire.object.dm_channel.send("You are the Dire Wolf. Each night, wake with the other Werewolves. The "
                                              "first night, choose a player to be your companion. You are eliminated if "
                                              "that player is eliminated. Choose a companion now with !companion "
                                              "username e.g. `!companion Lucas_Walgren`")

        if Roles.Wolf_Cub in self.desired_roles:
            cub = random.choice(self.players)
            while cub.role != Roles.Undetermined:
                cub = random.choice(self.players)
            cub.role = Roles.Wolf_Cub
            cub.affiliation = Affiliations.Werewolves
            if cub.object.dm_channel is None:
                await cub.object.create_dm()
            await cub.object.dm_channel.send("You are the Wolf Cub. Each night, wake with the Werewolves. If you are "
                                             "eliminated, the Werewolves eliminate two players the following night")

        if Roles.Fruit_Brute in self.desired_roles:
            fruit = random.choice(self.players)
            while fruit.role != Roles.Undetermined:
                fruit = random.choice(self.players)
            fruit.role = Roles.Fruit_Brute
            fruit.affiliation = Affiliations.Werewolves
            if fruit.object.dm_channel is None:
                await fruit.object.create_dm()
            await fruit.object.dm_channel.send("You are the Fruit Brute. Each night, wake with the other Werewolves. "
                                               "If you are the last Werewolf in the game, you do not get to eliminate "
                                               "a player at night.")

        if Roles.Old_Hag in self.desired_roles:
            hag = random.choice(self.players)
            while hag.role != Roles.Undetermined:
                hag = random.choice(self.players)
            hag.role = Roles.Old_Hag
            hag.affiliation = Affiliations.Villagers
            if hag.object.dm_channel is None:
                await hag.object.create_dm()
            await hag.object.dm_channel.send("You are the Old Hag. Each night, choose a player to leave the village ("
                                             "not be able to read or send messages in town assembly) during the "
                                             "next day.")

        if Roles.Hunter in self.desired_roles:
            hunter = random.choice(self.players)
            while hunter.role != Roles.Undetermined:
                hunter = random.choice(self.players)
            hunter.role = Roles.Hunter
            hunter.affiliation = Affiliations.Villagers
            if hunter.object.dm_channel is None:
                await hunter.object.create_dm()
            await hunter.object.dm_channel.send("You are the Hunter. If you are eliminated, you may immediately "
                                                "eliminate another player.")

        if Roles.Spellcaster in self.desired_roles:
            spell = random.choice(self.players)
            while spell.role != Roles.Undetermined:
                spell = random.choice(self.players)
            spell.role = Roles.Spellcaster
            spell.affiliation = Affiliations.Villagers
            if spell.object.dm_channel is None:
                await spell.object.create_dm()
            await spell.object.dm_channel.send("You are the Spellcaster. Each night, choose a player who may not "
                                               "speak in the town-assembly the following day.")

        if Roles.Village_Idiot in self.desired_roles:
            idiot = random.choice(self.players)
            while idiot.role != Roles.Undetermined:
                idiot = random.choice(self.players)
            idiot.role = Roles.Village_Idiot
            idiot.affiliation = Affiliations.Villagers
            if idiot.object.dm_channel is None:
                await idiot.object.create_dm()
            await idiot.object.dm_channel.send("You are the village idiot. You must always vote for players to be "
                                               "eliminated.")

        if Roles.Mayor in self.desired_roles:
            mayor = random.choice(self.players)
            while mayor.role != Roles.Undetermined:
                mayor = random.choice(self.players)
            mayor.role = Roles.Mayor
            mayor.affiliation = Affiliations.Villagers
            if mayor.object.dm_channel is None:
                await mayor.object.create_dm()
            await mayor.object.dm_channel.send("You are the village mayor. Your vote counts twice.")

        if Roles.Tough_Guy in self.desired_roles:
            tough = random.choice(self.players)
            while tough.role != Roles.Undetermined:
                tough = random.choice(self.players)
            tough.role = Roles.Tough_Guy
            tough.affiliation = Affiliations.Villagers
            if tough.object.dm_channel is None:
                await tough.object.create_dm()
            await tough.object.dm_channel.send("You are the tough guy. If the Werewolves attempt to eliminate you, "
                                               "you are not eliminated until the following night.")

        if Roles.Aura_Seer in self.desired_roles:
            aura = random.choice(self.players)
            while aura.role != Roles.Undetermined:
                aura = random.choice(self.players)
            aura.role = Roles.Aura_Seer
            aura.affiliation = Affiliations.Villagers
            if aura.object.dm_channel is None:
                await aura.object.create_dm()
            await aura.object.dm_channel.send("You are the aura seer. Choose a player each night to see if that "
                                              "player is not a regular Werewolf or Villager.")

        if Roles.Witch in self.desired_roles:
            witch = random.choice(self.players)
            while witch.role != Roles.Undetermined:
                witch = random.choice(self.players)
            witch.role = Roles.Witch
            witch.affiliation = Affiliations.Villagers
            if witch.object.dm_channel is None:
                await witch.object.create_dm()
            await witch.object.dm_channel.send("You are the witch. You may save or eliminate a player at night "
                                               "once each per game. You are on the villager team.")

        for player in self.players:
            await player.object.add_roles(self.roles['player'])
            if player.role == Roles.Undetermined:
                player.role = Roles.Villager
                player.affiliation = Affiliations.Villagers
                if player.object.dm_channel is None:
                    await player.object.create_dm()
                await player.object.dm_channel.send("You are a villager. Try to identify and kill the evil werewolves.")
            elif player.role == Roles.Werewolf:
                print(player.name)
                if player.object.dm_channel is None:
                    await player.object.create_dm()
                await player.object.dm_channel.send(
                    "You are a werewolf. Every night, kill one of the villagers"
                    " and try to not be found out during the day.")
                for wolf_un in self.get_living_werewolves():
                    if wolf_un != player.name:
                        await player.object.dm_channel.send("%s is also a werewolf" % wolf_un)
        role_quantities = {}
        for player in self.players:
            if player.role in role_quantities:
                if player.role == Roles.Village_Idiot:
                    role_quantities[Roles.Villager] = role_quantities[Roles.Villager] + 1 if Roles.Villager in role_quantities else 1
                else:
                    role_quantities[player.role] += 1
            else:
                role_quantities[player.role] = 1
        await self.channels['town_assembly'].send("Number of players of each type.")
        for role, quantity in role_quantities.items():
            await self.channels['town_assembly'].send("%s: %s" % (role.name, quantity))
        self.phase = Phases.First_Night
        await self.night_phase()


    async def target(self, message):
        if message.channel == self.channels['wolf_den'] and (self.phase == Phases.Night or self.phase ==
                                                             Phases.First_Night):
            if self.get_total_living_werewolves() == 1 and Roles.Fruit_Brute in self.get_living_roles():
                return

            target_user = self.parse_arguments(message)
            target_player = self.get_player_by_name(target_user)
            if target_player is not None and not target_player.alive:
                await self.channels['wolf_den'].send("%s is already dead. Choose someone else." % target_user)
                return
            elif target_player is not None and target_player.role == Roles.Werewolf:
                await self.channels['wolf_den'].send("%s is a werewolf! Choose someone else." % target_user)
                return
            if target_player is not None and self.get_total_living_werewolves() > 1:
                target_message = await self.channels['wolf_den'].send("%s is targeted for death. All other wolves must "
                                                                      "react with 👍 to this message to "
                                                                      "confirm" % target_user)
                await target_message.add_reaction('👍')
                self.messages.append(
                    VotingMessage(self.get_player_by_name(target_user), message.author, target_message, MessageTypes.Target))
            elif target_player is not None and self.get_total_living_werewolves() == 1:
                await self.channels['wolf_den'].send("You have successfully targeted %s." % target_user)
                self.wolf_target = self.get_player_by_name(target_user)
                self.completed_night_roles.append(Roles.Werewolf)
                await self.check_night_end()
                """
                await self.kill_player(self.get_player(target_user))
                await self.channels['wolf_den'].send(
                    "You have successfully mauled %s. Good wolfie." % self.get_player(target_user).name)
                result = self.check_game_end()
                if result == Roles.Undetermined:
                    await self.day_phase(self.get_player(target_user))
                else:
                    await self.end(result)
                """

    async def trouble(self, message):
        player = self.get_player_by_name(message.author.name)
        if player is not None and player.role == Roles.Troublemaker and OneTimeActions.Trouble not in self.one_time_use:
            self.troublemaking = True
            self.one_time_use.append(OneTimeActions.Trouble)
            await self.check_night_end()

    async def witch(self, message, action):
        target_player = self.get_player_by_name(Werewolf.parse_arguments(message))
        if target_player is not None and target_player.alive and target_player.name != message.author.name:
            pass
        else:
            return

        witch = self.get_player_by_name(message.author.name)
        if witch == Roles.Witch and Roles.Witch in \
                self.get_living_roles() and (self.phase == Phases.Night or self.phase == Phases.First_Night):
            pass
        else:
            return

        if action == 'kill':
            if OneTimeActions.WitchKill in self.one_time_use:
                await witch.object.dm_channel.send("You have already used your kill action this game.")
            else:
                self.witch_killed = target_player
                await witch.object.dm_channel.send("You have successfully targeted %s for death." % target_player.name)
                self.one_time_use.append(OneTimeActions.WitchKill)

        elif action == 'save':
            if OneTimeActions.WitchSave in self.one_time_use:
                await witch.object.dm_channel.send("You have already used your save action this game.")
            else:
                self.witch_saved = target_player
                await witch.object.dm_channel.send("You have successfully saved %s." % target_player.name)
                self.one_time_use.append(OneTimeActions.WitchSave)


with open('key.txt', 'r') as key:
    TOKEN = key.readline()

print(TOKEN)


client = Client()
games = {}


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    elif message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await message.channel.send(msg)

    elif message.content.startswith('!initialize'):
        game = Werewolf()
        await game.initialize(message)
        games[message.guild] = game

    elif message.content.startswith('!addme'):
        await games[message.guild].add_user(message)

    elif message.content.startswith('!setup'):
        games[message.guild].setup(message)

    elif message.content.startswith('!start'):
        await games[message.guild].start(message)

    elif message.content.startswith('!target'):
        await games[message.guild].target(message)

    elif message.content.startswith('!reset'):
        await games[message.guild].reset(message)

    elif message.content.startswith('!accuse'):
        await games[message.guild].accuse(message)

    elif message.content.startswith('!save'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].save(message)

    elif message.content.startswith('!investigate'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].investigate(message)

    elif message.content.startswith('!link'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].link(message)

    elif message.content.startswith('!intimidate'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].intimidate(message)

    elif message.content.startswith('!ensorcell'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].ensorcell(message)

    elif message.content.startswith('!trouble'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].trouble(message)

    elif message.content.startswith('!hood'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].hood(message)

    elif message.content.startswith('!companion'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].companion(message)

    elif message.content.startswith('!banish'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].banish(message)

    elif message.content.startswith('!hunt'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].hunt(message)

    elif message.content.startswith('!silence'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].silence(message)

    elif message.content.startswith('!aura'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].aura(message)

    elif message.content.startswith('!witchkill'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].witch(message, 'kill')

    elif message.content.startswith('!witchsave'):
        guild_list = {member: guild for guild in games.keys() for member in guild.members}
        for member, guild in guild_list.items():
            if member == message.author:
                await games[guild].witch(message, 'save')

@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return
    else:
        await games[reaction.message.guild].reaction_handler_add(reaction, user)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


client.run(TOKEN)
