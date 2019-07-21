# Work with Python 3.6
from discord import *
import random

class Phases(Enum):
	Beginning = 0
	Night = 1
	Day = 2

class Roles(Enum):
	Undetermined = 0
	Villager = 1
	Werewolf = 2

class MessageTypes(Enum):
	Target = 0
	Accusation = 1

class Player:
	def __init__(self, object):
		self.object = object
		self.name = object.name
		self.role = Roles.Undetermined
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
			accused_user = message.content.split(' ')[1]
			if self.get_player(accused_user) != None:
				target_message = await self.channels['town_assembly'].send("%s has been accused of being a hairy wolf monster. React with 👍 for them to live, 👎 for them to die." % accused_user)
				self.thumbsup = await target_message.add_reaction('👍')
				self.thumbsdown = await target_message.add_reaction('👎')
				self.messages.append(VotingMessage(self.get_player(accused_user), message.author, target_message, MessageTypes.Accusation))

	async def add_user(self, message):
		if self.phase == Phases.Beginning:
			self.players.append(Player(message.author))
			await message.channel.send("%s has been successfully added." % message.author.name)
		else:
			await message.channel.send("The game has already been started. Wait until a new game is beginning first.")

	def check_end(self):
		if self.get_total_living_players() / 2 <= self.get_total_living_werewolves():
			return Roles.Werewolf
		elif self.get_total_living_werewolves() <= 0:
			return Roles.Villager
		else: 
			return Roles.Undetermined

	async def day_phase(self, killed_player):
		await self.channels['town_assembly'].send("Day Phase. %s met their end last night by wolf fangs. Whodunit? Throw out accusations with !accuse username" % killed_player.name)
		self.phase = Phases.Day

	async def end(self, victor):
		if victor == Roles.Werewolf:
			message = await self.channels['town_assembly'].send("The werewolves have taken control of the town and can finally start the dentistry shop they always wanted. Human meat is a massive pain to remove from your teeth!")
		elif victor == Roles.Villager:
			message = await self.channels['town_assembly'].send("The townspeople heave a collective sigh of relief as they put down the last hairy abomination. This is Medieval Europe, after all. What need have you of dentistry?")
		await self.setup(message)

	def get_total_living_players(self):
		print(len([player for player in self.players if player.alive]))
		return len([player for player in self.players if player.alive])
	
	def get_total_living_werewolves(self):
		print(len([player for player in self.players if player.role == Roles.Werewolf and player.alive]))
		return len([player for player in self.players if player.role == Roles.Werewolf and player.alive])

	def get_living_werewolves(self):
		return [player.name for player in self.players if player.role == Roles.Werewolf and player.alive]

	def get_player(self, username):
		try:
			return next(filter(lambda x: x.name == username, self.players))
		except StopIteration:
			pass

	def get_message(self, message):
		try:
			return next(filter(lambda x: x.message.content == message.content, self.messages))
		except StopIteration:
			return None

	async def kill_player(self, player):
		player.alive = False

		read_only = PermissionOverwrite()
		read_only.send_messages = False
		read_only.read_messages = True
		read_only.add_reactions = False

		full = PermissionOverwrite()
		full.send_messages = True
		full.read_messages = True
		full.add_reactions = True

		await self.channels['wolf_den'].set_permissions(player.object, overwrite=None)
		await self.channels['town_assembly'].set_permissions(player.object, overwrite=None)
		await self.channels['astral_plane'].set_permissions(player.object, overwrite=None)
		await self.channels['wolf_den'].set_permissions(player.object, overwrite=read_only)
		await self.channels['town_assembly'].set_permissions(player.object, overwrite=read_only)
		await self.channels['astral_plane'].set_permissions(player.object, overwrite=full)
	
	async def night_phase(self):
		self.phase = Phases.Night
		await self.channels['wolf_den'].send("Hello wolves. Pick a target for death with the command !target username")
		await self.channels['town_assembly'].send("Night Phase. One of you will die tonight. Best come to terms with that...")

	async def reaction_handler_add(self, reaction, user):
		message_str = reaction.message
		message = self.get_message(message_str)
		# print(message_str.content)
		print([x.message.content for x in self.messages])
		# print(message.message.content)
		player = self.get_player(user.name)
		if message is not None:
			if message.type == MessageTypes.Target:
				if player != message.author and reaction.emoji == '👍':
					message.confirmations += 1
					message.voted_players.append(player)
					if message.confirmations >= self.get_total_living_werewolves() - 1:
						await self.kill_player(message.target)
						await self.channels['wolf_den'].send("You have successfully mauled %s. Good wolfie." % message.target.name)
						result = self.check_end()
						if result == Roles.Undetermined:
							await self.day_phase(message.target)
						else:
							await self.end(result)
				else:
					await reaction.remove(user)
			elif message.type == MessageTypes.Accusation:
				print(message.confirmations, message.rejections, len(message.voted_players), reaction.emoji, player.name)
				if player not in message.voted_players:
					if reaction.emoji == '👍':
						message.confirmations += 1
						message.voted_players.append(player)
					elif reaction.emoji == '👎':
						message.rejections += 1
						# print("voted_down")
						message.voted_players.append(player)
					# else:
						#await reaction.remove(user)
					if len(message.voted_players) >= self.get_total_living_players():
						if message.rejections > message.confirmations:
							await self.kill_player(message.target)
							await self.channels['town_assembly'].send("You have successfully lynched %s. I bet your parents are proud of you." % message.target.name)
							result = self.check_end()
							if result == Roles.Undetermined:
								await self.night_phase()
							else:
								await self.end(result)
						else:
							await self.channels['town_assembly'].send("You have failed to lynch %s. How does that make you feel?" % message.target.name)
				#elif player in message.voted_players:
					#await reaction.remove(user)

	async def reaction_handler_remove(self, reaction, user):
		message_str = reaction.message
		message = self.get_message(message_str)
		# print(message.message.content)
		player = self.get_player(user)
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

	async def reset(self):
		for channel in self.channels.values():
			await channel.delete()

	async def setup(self, message):
		self.players = []
		self.messages = []
		self.channels = {}
		self.phase = Phases.Beginning
		self.guild = message.guild

		overwrites = PermissionOverwrite()
		overwrites.read_messages = False 
		for channel in self.guild.channels:
			if channel.name == 'the-wolf-den':
				self.channels['wolf_den'] = channel
				await channel.set_permissions(self.guild.default_role, overwrite=None)
				await channel.set_permissions(self.guild.default_role, overwrite=overwrites)
			elif channel.name == 'town-assembly':
				self.channels['town_assembly'] = channel
				await channel.set_permissions(self.guild.default_role, overwrite=None)
			elif channel.name == 'the-astral-plane':
				self.channels['astral_plane'] = channel
				await channel.set_permissions(self.guild.default_role, overwrite=None)
				await channel.set_permissions(self.guild.default_role, overwrite=overwrites)
		if len(self.channels) < 3:
			for channel in self.channels.values():
				await channel.delete()
			self.channels['wolf_den'] = await self.guild.create_text_channel("the-wolf-den", overwrite=None)
			await self.channels['wolf_den'].set_permissions(self.guild.default_role, overwrite=overwrites)
			self.channels['town_assembly'] = await self.guild.create_text_channel("town-assembly", overwrite=None)
			self.channels['astral_plane'] = await self.guild.create_text_channel("the-astral-plane", overwrite=None)
			await self.channels['astral_plane'].set_permissions(self.guild.default_role, overwrite=overwrites)
		await message.channel.send("Thanks for trying out my Werewolf bot. To start, everyone who wants to play should run the command !addme and then someone with admin privileges should run !start")
	
	async def start(self):
		# randomly pick wolves
		num_wolves = len(self.players) // 3
		while self.get_total_living_werewolves() < num_wolves:
			next_wolf = random.randrange(len(self.players))
			self.players[next_wolf].role = Roles.Werewolf
			overwrites = PermissionOverwrite()
			overwrites.send_messages = True
			overwrites.read_messages = True
			await self.channels['wolf_den'].set_permissions(self.players[next_wolf].object, overwrite=None)
			await self.channels['wolf_den'].set_permissions(self.players[next_wolf].object, overwrite=overwrites)
		for player in self.players:
			if player.role != Roles.Werewolf:
				player.role = Roles.Villager
				if player.object.dm_channel is None:
					await player.object.create_dm()
				await player.object.dm_channel.send("You are a villager. Try to identify and kill the evil werewolves.")
			else:
				print(player.name)
				if player.object.dm_channel is None:
					await player.object.create_dm()
				await player.object.dm_channel.send("You are a werewolf. Every night, kill one of the villagers and try to not be found out during the day.")
				for wolf_un in self.get_living_werewolves():
					if wolf_un != player.name:
						await player.object.dm_channel.send("%s is also a werewolf")
		await self.night_phase()

	async def target(self, message):
		if message.channel == self.channels['wolf_den'] and self.phase == Phases.Night:
			target_user = message.content.split(' ')[1]
			if self.get_player(target_user) != None and self.get_total_living_werewolves() > 1:
				target_message = await self.channels['wolf_den'].send("%s is targeted for death. All other wolves must react with 👍 to this message to confirm" % target_user)
				self.thumbsup = await target_message.add_reaction('👍')
				self.messages.append(VotingMessage(self.get_player(target_user), message.author, target_message, MessageTypes.Target))
			elif self.get_total_living_werewolves() == 1:
				await self.kill_player(self.get_player(target_user))
				await self.channels['wolf_den'].send("You have successfully mauled %s. Good wolfie." % self.get_player(target_user).name)
				result = self.check_end()
				if result == Roles.Undetermined:
					await self.day_phase(self.get_player(target_user))
				else:
					await self.end(result)
			

TOKEN = 'NjAwOTEwMzA5MjYzMjc4MDk1.XS60Hw.cBJDqrfBBaLDyK7so6L4qzvl9_M'

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
	
	elif message.content.startswith('!setup'):
		game = Werewolf()
		await game.setup(message)
		games[message.guild] = game

	elif message.content.startswith('!addme'):
		await games[message.guild].add_user(message)
	
	elif message.content.startswith('!start'):
		await games[message.guild].start()
			
	elif message.content.startswith('!target'):
		await games[message.guild].target(message)
		
	elif message.content.startswith('!reset'):
		await games[message.guild].reset()

	elif message.content.startswith('!accuse'):
		await games[message.guild].accuse(message)
			
@client.event
async def on_reaction_add(reaction, user):
	if user == client.user:
		return
	else:
		await games[reaction.message.guild].reaction_handler_add(reaction, user)

"""
@client.event
async def on_reaction_remove(reaction, user):
	if user == client.user:
		return
	else:
		await games[reaction.message.guild].reaction_handler_remove(reaction, user)
"""

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')

client.run(TOKEN)