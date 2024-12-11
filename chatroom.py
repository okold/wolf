import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.template import Template
from spade.message import Message
import json
import os
import logging

MESSAGE_TIMEOUT = 300

class ChatRoomAgent(Agent):
    def __init__(self, jid, password, room_name, **kwargs):
        super().__init__(jid, password, **kwargs)
        self.room_name = room_name
        self.chat_log = []

    # for formatting
    def log(self, source, message):
        return f"{self.name}: {source}: {message}"

    # returns each message as a completion, which can be inserted directly into the context
    class GetMsgBehaviour(CyclicBehaviour):
        async def run(self):
            try:
                message = await self.receive(timeout=MESSAGE_TIMEOUT)
                if message:
                    logging.info(self.agent.log("GetMsgBehaviour", f"received message {message.body}"))
                    data = json.loads(message.body)

                    self.agent.chat_log.append(data)
                    
                else:
                    logging.debug(self.agent.log("GetMsgBehaviour", "timed out"))

            except Exception as e:
                logging.error(self.agent.log("GetMsgBehaviour, receiving", e))

    class ServeChatBehaviour(CyclicBehaviour):
        async def run(self):
            try:
                request = await self.receive(timeout=MESSAGE_TIMEOUT)
                if request:
      
                    index = int(request.body)  # Validate index
                    sender = str(request.sender.bare())
                    logging.info(self.agent.log("ServeChatBehaviour", f"received request from {sender}"))

                    # slice the chat log
                    new_messages = self.agent.chat_log[index:] if index < len(self.agent.chat_log) else []
                    logging.info(self.agent.log("ServeChatBehaviour", f"new messages: {new_messages}"))
                    response = Message(to=sender)
                    response.body = json.dumps(new_messages)
                    await self.send(response)

                else:
                    logging.debug("ChatRoomAgent: ServeChatBehaviour: timeout, so quiet :()")
            
            except Exception as e:
                logging.error(self.agent.log("GetMsgBehaviour, receiving", e))

    async def setup(self):
        msg_loop = self.GetMsgBehaviour()
        msg_template = Template()
        msg_template.set_metadata("performative", "inform")
        self.add_behaviour(msg_loop, msg_template)

        chat_serve = self.ServeChatBehaviour()
        serve_template = Template()
        serve_template.set_metadata("performative", "query")
        self.add_behaviour(chat_serve, serve_template)

### TESTING
if __name__ == "__main__":
    msg_list = ["a", "b", "c", "d", "e"]
    print(msg_list[2:])
    print(len(msg_list))
    print(msg_list[len(msg_list):])
    print(msg_list[2:])
    print(msg_list[-6:])
