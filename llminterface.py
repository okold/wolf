from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.agent import Agent
from spade.template import Template
from spade.message import Message
from asyncio import sleep
from openai import OpenAI
import logging
import spade
import json

import logging

LISTEN_TIMEOUT = 10

### LLM
# holds some functions for promting the openAI chat completions API
# defaults to running ollama on localhost
# 
# ARGUMENTS
# model         - the llm to power the ai, defaults to llama
class LLM:
    def __init__(self, model = 'llama3.1'):
        self.client = OpenAI(
            base_url = 'http://localhost:11434/v1',
            api_key='ollama'
        )
        self.model = model

    # expects a list of dictionaries
    async def prompt(self, context):

        response = self.client.chat.completions.create(
            model=self.model,
            messages=context
        )
        logging.debug(f"{self.model}: {response}")
        return response

### LLMINTERFACEAGENT
# the alternative to the user interface, which connects with a player agent
# so that an LLM can interact with the game, instead of a human
#
# ARGUMENTS
# model         - the llm to power the ai, also defaults to llama
class LLMInterfaceAgent(Agent):
    def __init__(self, jid, password, model='llama3.1', **kwargs):
        super().__init__(jid, password, **kwargs)
        self.llm = LLM(model)

   # for formatting
    def log(self, source, message):
        return f"{self.name}: {source}: {message}"
    
    ### PROMPTBEHAVIOUR
    # prompts the LLM and returns its response as an assistant-type message
    class PromptBehaviour(CyclicBehaviour): 
        async def run(self):
            try:
                prompt = await self.receive(timeout=10)
                if prompt:
                    data = json.loads(prompt.body)

                    # query the LLM
                    response = await self.agent.llm.prompt(data)
                    logging.debug(self.agent.log("PromptBehaviour, full response", response))

                    completion = {
                        "role": "assistant", "content": response.choices[0].message.content
                    }
                    logging.info(self.agent.log("PromptBehaviour, return", completion))
                    message = Message(to=str(prompt.sender.bare()))
                    message.body = json.dumps(completion)

                    await self.send(message)

                else:
                    logging.debug(self.agent.log("PromptBehaviour", "timeout"))

            except Exception as e:
                logging.error(self.agent.log("PromptBehaviour, prompting", e))
                # TODO: sending error messages back
    
    async def setup(self):
        prompt_behav = self.PromptBehaviour()
        template = Template()
        template.set_metadata("performative", "query")
        self.add_behaviour(prompt_behav, template)


### TESTING
class MessageTester(Agent):
    class TestBehav(OneShotBehaviour):
        async def run(self):
            messages=[
                    {"role": "user", "content": "Think of a random name for yourself. Use one word, with no punctuation."}
                ]
            
            messages_json = json.dumps(messages)

            test = Message(to="ai@localhost")
            test.set_metadata("performative", "query")
            test.body = messages_json

            await self.send(test)

            response = await self.receive()
            logging.info(f"MessageTester: response: {response}")

            await self.agent.stop()
    
    async def setup(self):
        test_behav = self.TestBehav()
        self.add_behaviour(test_behav)

async def main():
    ai = LLMInterfaceAgent("ai@localhost", "ai")
    await ai.start()

    test = MessageTester("test@localhost", "test")
    await test.start()

    while test.is_alive():
        await sleep(5)

    await ai.stop()

if __name__ == "__main__":
    logging.getLogger("spade.Agent").setLevel(logging.WARNING)
    logging.getLogger("spade.behaviour").setLevel(logging.WARNING)
    logging.getLogger("SPADE").setLevel(logging.WARNING)
    logging.getLogger("spade.Message").setLevel(logging.WARNING)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    spade.run(main())