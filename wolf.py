### MULTI-AGENT WOLF (MAW) - VERSION 0.1
# Olga Koldachenko - olga.koldachenko@ucalgary.ca
# SENG 696 - Agent-Based Software Engineering
# Fall 2024 - University of Calgary
# Dr. Behrouz Far
#
# COMMAND-LINE ARGUMENTS:
# num_ai    - controls the number of bots spawned
################################################################################
from userinterface import userInterfaceAgent, COMMANDS
from player import PlayerAgent
from chatroom import ChatRoomAgent
from llminterface import LLMInterfaceAgent
import logging
import asyncio
import spade
import sys

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

### SETTINGS AND JUNK
DEFAULT_AI = 3
WELCOME_MESSAGE = '''
***Welcome to Multi Agent Wolf (MAW) Version 0.1***
You... won't actually be playing a game of Werewolf, but all the others in the 
chatroom are still AI, which makes for an interesting, if slightly surreal
experience.
'''
LOADING_MESSAGE = '''Loading... Please be patient for the prompt :-)
'''

### MAIN
async def main():

    num_ai = DEFAULT_AI
    try:
        num_ai = sys.argv[i]
    except:
        pass
    ai_list = []

    print(WELCOME_MESSAGE)
    print(COMMANDS)
    print(f"There are {num_ai} AI in the room with you.")
    print(LOADING_MESSAGE)

    useragent = userInterfaceAgent("user@localhost", "user")
    await useragent.start(auto_register=True)

    room = ChatRoomAgent("village@localhost", "village", "Village")
    await room.start(auto_register=True)

    ai = LLMInterfaceAgent("ai@localhost", "ai")
    await ai.start(auto_register=True)

    for i in range(1,num_ai+1):
        aiplayer = PlayerAgent(f"aiplayer{i}@localhost", f"aiplayer{i}", "ai@localhost")
        await aiplayer.start(auto_register=True)
        
        ai_list.append(aiplayer)

    player = PlayerAgent("userplayer@localhost", "userplayer", "user@localhost", wait_period=0, wait_variance=0)
    await player.start(auto_register=True)

    while not useragent.game_loop.is_killed():
        try:
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            break
    
    await useragent.stop()
    await player.stop()
    await room.stop()
    await ai.stop()

    for aiplayer in ai_list:
        await aiplayer.stop()

    print("Bye!")

if __name__ == "__main__":
    spade.run(main())