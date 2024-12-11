import spade
from spade.agent import Agent
from llminterface import LLMInterfaceAgent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from spade.template import Template
from chatroom import ChatRoomAgent
import json
from asyncio import sleep
import logging
import random

### FSM STATES
GET_NAME_STATE = "GET_NAME"
JOIN_ROOM_STATE = "JOIN_ROOM"
GET_CHAT_STATE = "GET_CHAT"
PROMPT_STATE = "PROMPT"
SEND_STATE = "SEND"

RANDOM_PERSONALITIES = [
    "silly",
    "grumpy",
    "happy",
    "gloomy",
    "ditzy",
    "nerdy"
]

### PROMPT TEMPLATES
NAME_GEN_PROMPT = "Think of a random name for yourself. Respond using one word, with no punctuation."
CHAT_GEN_PROMPT = "You are in a chat room. Respond in one short sentence. Do not say your own name."
FILLER_PROMPT = "It's pretty quiet over here..."

### TIMERS
CHAT_TIMEOUT = 30
PROMPT_TIMEOUT = 300

### PLAYERAGENT
# houses the framework for any player of the game (human or LLM)
#
# ARGUMENTS
# player_interface:     - stores the JID of the player's "brain"
# max_memory:           - the maximum number of chat logs held within the context
# wait_period:          - the median delay offered to not overwhelm the computer
# wait_variance:        - randomness, to avoid players clashing over resources
#
# ATTRIBUTES
# player_name:          - an identifier chosen by the player at the beginning of
#                         the game: *not* the JID
# chat_index:           - used to avoid pulling the same logs from the chat twice
# chatroom              - JID of the active chat
#
# TODO: dynamically change the chat address from a static to a dynamic one, in 
#       order to facilitate phase changes
class PlayerAgent(Agent):
    def __init__(self, jid, password, player_interface, max_memory = 5, 
                 wait_period = 10, wait_variance = 5, **kwargs):
        super().__init__(jid, password, **kwargs)

        self.player_interface = player_interface
        self.player_name = ""
        self.wait_period = wait_period
        self.wait_variance = wait_variance
        self.memory = []
        self.max_memory = max_memory
        self.chat_index = 0
        self.chatroom = "village@localhost"

        self.personality = RANDOM_PERSONALITIES[random.randint(0,len(RANDOM_PERSONALITIES)-1)]
        self.personality_prompt = f"You have a {self.personality} personality."

    # for formatting
    def log(self, source, message):
        return f"{self.name}: {source}: {message}"
    
    # for dramatic tension
    async def random_sleep(self):
        await sleep(random.randint(self.wait_period - self.wait_variance, 
                                   self.wait_period + self.wait_variance) * 2)

    ### GETNAMESTATE
    # the initial state, queries the player interface for an identifier
    class GetNameState(State):
        async def run(self):
            #sending
            try:
                request = Message(to=self.agent.player_interface)
                request.set_metadata("performative", "query")

                prompt = [{ "role": "user", "content": NAME_GEN_PROMPT + " " + self.agent.personality_prompt }] # NOTE: list!!
                request.body = json.dumps(prompt)

                logging.debug(self.agent.log("GetNameState, sending", request.body))
                await self.send(request)

            except Exception as e:
                logging.error(self.agent.log("GetNameState, sending", e))
                self.kill() # beyond hope

            # receiving
            try:
                response = await self.receive(timeout=PROMPT_TIMEOUT)
                if response:
                    logging.info(self.agent.log(f"GetNameState received name of type: {type(response.body)}", response.body))
                    data = json.loads(response.body)

                    logging.debug(self.agent.log("GetNameState JSON loads", data))
                    self.agent.player_name = data["content"]
                    
                    await self.agent.random_sleep()
                    self.set_next_state(JOIN_ROOM_STATE)

            except Exception as e:
                logging.error(self.agent.log("GetNameState, receiving", e))
                self.kill() # pitiful
    
    ### JOINROOMSTATE
    # sends a notice message to a ChatRoomAgent to inform other players
    # TODO: commented out the announcement, because it makes the AI WEIRD
    class JoinRoomState(State):
        async def run(self):
            try:
                message = Message(to=self.agent.chatroom)
                message.set_metadata("performative", "inform")
                notification = { "role": "system", "content": f"{self.agent.player_name} has entered the room" }
                message.body = json.dumps(notification)

                logging.info(self.agent.log("JoinRoomState", message.body))
                #await self.send(message)
                self.set_next_state(GET_CHAT_STATE)

            except Exception as e:
                logging.error(self.agent.log("JoinRoomState, receiving", e))
                self.kill() # can't even say hi

            self.agent.chat_index = 0 # reset the value

    ### GETCHATSTATE
    # retreieves the newest message from the active chat room and processes them
    class GetChatState(State):
        async def run(self):
            # retrieve
            try:
                request = Message(to=self.agent.chatroom)
                request.set_metadata("performative", "query")
                request.body = str(self.agent.chat_index)

                logging.info(self.agent.log("GetChatState", f"chat index = {request.body}"))
                await self.send(request)

                # process
                try:
                    response = await self.receive(timeout=CHAT_TIMEOUT)
                    if response:
                        new_messages = json.loads(response.body)
                        self.agent.chat_index += len(new_messages)
                        logging.debug(self.agent.log("GetChatState", 
                            f"received data from {self.agent.chatroom}: {new_messages}: {type(new_messages)}"))

                        # add new context
                        if new_messages == []:
                            quiet = {
                                "role": "user", "content": "It's pretty quiet over here..."
                            }
                            self.agent.memory.append(quiet)
                            logging.info(self.agent.log("GetChatState", f"added quiet line = {self.agent.memory}"))
                        else:
                            self.agent.memory = self.agent.memory + new_messages
                    

                        if len(self.agent.memory) > self.agent.max_memory:
                            self.agent.memory = self.agent.memory[-self.agent.max_memory:]
                            logging.info(self.agent.log("GetChatState", 
                                f"memory exeeds {self.agent.max_memory} chats, pruned: {self.agent.memory}"))
                        else:
                            logging.info(self.agent.log("GetChatState", f"current memory {self.agent.memory}"))
                        
                        await self.agent.random_sleep()
                        self.set_next_state(PROMPT_STATE) # continue
                        return

                    else:
                        logging.warning(self.agent.log("GetChatState", 
                            f"response from {self.agent.chatroom} timed out"))

                except Exception as e:
                    logging.error(self.agent.log("GetChatState, processing", e))

            except Exception as e:
                logging.error(self.agent.log("GetChatState, retrieving", e))

            await self.agent.random_sleep()
            self.set_next_state(GET_CHAT_STATE) # retry


    ### PROMPTSTATE
    # prompts the LLM or user interface
    class PromptState(State):
        async def run(self):
            # thinking
            try:
                request = Message(to=self.agent.player_interface)
                request.set_metadata("performative", "query")


                if self.agent.name != "userplayer":
                    context = [
                        { "role": "system", "content": f"Your name is {self.agent.player_name}" },
                        { "role": "system", "content": CHAT_GEN_PROMPT},
                        { "role": "system", "content": self.agent.personality_prompt}
                    ]
                else:
                    context = []

                context = context + self.agent.memory
                request.body = json.dumps(context)

                logging.info(self.agent.log("PromptState", request.body))
                await self.send(request)

                # receiving
                try:
                    response = await self.receive(timeout=PROMPT_TIMEOUT)
                    if response:
                        message = json.loads(response.body)
                        logging.debug(self.agent.log("PromptState", 
                                f"received data from {self.agent.player_interface}: {message}: {type(message)}"))
                        

                        if message["content"] != "":
                            message["content"] = message["content"]
                            self.agent.memory.append(message)
                            self.set_next_state(SEND_STATE) # continue
                            return

                    else:
                        logging.warning(self.agent.log("PromptState", 
                                f"response from {self.agent.player_interface} timed out"))
                        
                except Exception as e:
                    logging.error(self.agent.log("PromptState, receiving", e))

            except Exception as e:
                logging.error(self.agent.log("PromptState, retrieving", e))

            await self.agent.random_sleep()
            self.set_next_state(GET_CHAT_STATE) # turn back

    
    ### SENDSTATE
    # sends a message to the chat room
    class SendState(State):
        async def run(self):
            try:
                inform = Message(to=self.agent.chatroom)
                inform.set_metadata("performative", "inform")
                last = self.agent.memory[-1]

                if last["content"] != FILLER_PROMPT:
                    logging.info(self.agent.log("SendState last", last))

                    message = {
                        "role": "user", "content": f"{self.agent.player_name}: {self.agent.memory[-1]['content']}"
                    }
                    
                    inform.body = json.dumps(message)
                    logging.info(self.agent.log("SendState inform", inform.body))

                    await self.send(inform)
                    await self.agent.random_sleep()

            except Exception as e:
                logging.error(self.agent.log("SendState, retrieving", e))
            
            self.set_next_state(GET_CHAT_STATE) 

    ### VOTESTATE
    # TODO: stub. sends a vote to the GameMaster    
    class VoteState(State):
        async def run():
            pass

    async def setup(self):
        fsm = FSMBehaviour()
        fsm.add_state(name=GET_NAME_STATE, state=self.GetNameState(), initial=True)
        fsm.add_transition(source=GET_NAME_STATE, dest=JOIN_ROOM_STATE)

        fsm.add_state(name=JOIN_ROOM_STATE, state=self.JoinRoomState())
        fsm.add_transition(source=JOIN_ROOM_STATE, dest=GET_CHAT_STATE)

        fsm.add_state(name=GET_CHAT_STATE, state=self.GetChatState())
        fsm.add_transition(source=GET_CHAT_STATE, dest=GET_CHAT_STATE)
        fsm.add_transition(source=GET_CHAT_STATE, dest=PROMPT_STATE)

        fsm.add_state(name=PROMPT_STATE, state=self.PromptState())
        fsm.add_transition(source=PROMPT_STATE, dest=GET_CHAT_STATE)
        fsm.add_transition(source=PROMPT_STATE, dest=SEND_STATE)

        fsm.add_state(name=SEND_STATE, state=self.SendState())
        fsm.add_transition(source=SEND_STATE, dest=GET_CHAT_STATE)

        self.add_behaviour(fsm)

### TESTING
async def main():
    chatroom = ChatRoomAgent("village@localhost", "village", "Village")
    await chatroom.start()

    ai = LLMInterfaceAgent("ai@localhost", "ai")
    await ai.start()

    player = PlayerAgent("aiplayer@localhost", "aiplayer", "ai@localhost")
    await player.start()

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
        
    logging.getLogger("spade.Agent").setLevel(logging.WARNING)
    logging.getLogger("SPADE").setLevel(logging.WARNING)
    logging.getLogger("spade.Message").setLevel(logging.WARNING)
    logging.getLogger("spade.Template").setLevel(logging.WARNING)
    logging.getLogger("spade.Web").setLevel(logging.WARNING)


    spade.run(main())