import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, FSMBehaviour, State
from spade.template import Template
from spade.message import Message
import json
from player import PlayerAgent
import os
import logging
import asyncio


COMMANDS = '''***COMMANDS***
/bye             - end the game
/vote <username> - vote to execute a player (placeholder)
/help            - list these commands

Any other text will be treated as dialogue by the game.
TIP: press enter to say nothing, and load more dialogue
'''


NAMING_STATE = "UI_NAME_STATE"
ACTION_STATE = "UI_ACTION_STATE"

class UIFSMBehaviour(FSMBehaviour):
    async def on_end(self):
        logging.info(f"FSM finished at state {self.current_state}")
        self.kill(10)
        await self.agent.stop()

class NamingState(State):
    async def run(self):
        try:
            request = await self.receive(timeout=300)
            if request:
                data = json.loads(request.body)
                logging.info(f"received request: {data}")
                print("Please choose a name.", flush=True)

                verify_input = False
                while not verify_input:
                    kb_in = await asyncio.get_event_loop().run_in_executor(None, input, ">> ")
                    if ' ' in kb_in or '/' in kb_in:
                        print("Please choose a name without spaces or the '/' symbol.", flush=True)
                    else:
                        verify_input = True

                response = Message(to=str(request.sender.bare()))

                completion = {"content": kb_in}
                response.body = json.dumps(completion)
                await self.send(response)
                logging.info(f"sent message: {completion}")

                #os.system('clear||cls')
                self.set_next_state(ACTION_STATE)
            else:
                logging.info("timeout - no messages")
                print("timeout")
        except Exception as e:
            logging.exception(e)
            self.kill(exit_code=1)


def print_messages(msg_log):
    for msg in msg_log:
        if msg['role'] != 'assistant':
            try:
                print(msg['content'], flush=True)
            except:
                pass #eh


class ActionState(State):
    async def run(self):
        try:
            req = await self.receive(timeout=2)
            if req:
                data = json.loads(req.body)
                logging.debug(f"userInterface: received request: {data}")

                os.system('clear||cls')
                print_messages(data)
                await asyncio.sleep(5)
                res = Message(to=str(req.sender.bare()))

                verify_input = False
                while not verify_input:
                    kb_in = await asyncio.get_event_loop().run_in_executor(None, input, ">> ")
                    if kb_in.startswith("/"):
                        if kb_in == "/help":
                            print(COMMANDS)
                        elif kb_in in ("/bye", "/exit", "/quit"):
                            self.kill(exit_code=10)
                            await self.agent.stop()
                            return
                        elif kb_in == "/vote":
                            pass #TODO voting
                        else:
                            print("Unknown command - try /help")
                    else:
                        verify_input = True
                        self.set_next_state(ACTION_STATE)

                completion = { "role": "assistant", "content": kb_in }
                res.body = json.dumps(completion)
                print("\nLoading... .. .", flush=True)
                await self.send(res)

                logging.info(f"sent message: {res.body}")
            else:
                logging.info("UI: timeout - no messages")
        except Exception as e:
            logging.exception(e)
            self.kill(exit_code=1)

class userInterfaceAgent(Agent):
    async def setup(self):
        self.game_loop = UIFSMBehaviour()
        self.game_loop.add_state(name=NAMING_STATE, state=NamingState(), initial=True)
        self.game_loop.add_state(name=ACTION_STATE, state=ActionState())
        self.game_loop.add_transition(source=NAMING_STATE, dest=ACTION_STATE)
        self.game_loop.add_transition(source=ACTION_STATE, dest=ACTION_STATE)

        self.add_behaviour(self.game_loop)


async def main():
    useragent = userInterfaceAgent("user@localhost", "user")
    player = PlayerAgent("userplayer@localhost", "userplayer", "user@localhost", "user")
    await useragent.start(auto_register=True)
    await player.start(auto_register=True)

if __name__ == "__main__":
    spade.run(main())