# Multi-Agent Wolf
This has been an interesting project so far. It's nowhere near done: I don't actually have the AI playing the game with each other yet, but I've managed to make a (relatively) stable platform where you can, at the least, sit in a chat room and mingle with some large language models.

I've learned some things for sure, like how I kind of resent dumping and loading JSON data so much. I swear, there's still a bug floating around in there because some functions want strings, while others don't.

It's not entirely polished, but my exception handling and logging has overall improved.

That and, I just really enjoy working with agent. I'm sure I'll continue working on this in the future.

## How to run
wolf.py is your main, and the one command line argument is an int that changes how many bots are spawned.

- The LLMs as they're written are powered by Ollama (the default model is llama3.1, but it's just a string): https://github.com/ollama
  - However, I used OpenAI's completions API, so it's pretty swappable with anything, especially if you have a key.
- You'll need SPADE, as the basis for the MAS: https://github.com/javipalanca/spade
- As an extension of the above, you'll also need some sort of XMPP server. I used Ejabberd, since it was pretty easy to set up: https://www.ejabberd.im/index.html
  - The primary settings I had to keep in mind were enabling in-band registration, and lowering the amount of delay between allowable signups.

Beyond this, I developed this on Linux, so this hasn't been tested on Windows or Mac. There might be even more bugs that I'm not aware of, who knows!
 
Everything here runs on localhost, so the better your computer, the more effective this program will be. I just so happened to run this on a 2020 Lenovo E580 with an i5-8250U, 15.4GB of RAM, and no GPU. Honestly, I'm interested to see what can be done with this sort of framework on an actual powerhouse.
