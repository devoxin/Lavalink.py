<img align="left" src="https://serux.pro/9e83af1581.png" height="150" width="150">

# Lavalink.py

Lavalink.py is a wrapper for [Lavalink](https://github.com/Frederikam/Lavalink) which abstracts away most of the code necessary to use Lavalink to allow for easier integration into your bots, while still promising full API coverage and powerful tools to get the most out of it.

# Getting Started
First you need to run a command to install the library,
```shell
pip install lavalink
```

Then you need to setup the Lavalink server, you will need to install Java and run this [jar](https://ci.fredboat.com/guestAuth/repository/download/Lavalink_Build/.lastSuccessful/Lavalink.jar?branch=refs%2Fheads%2Fmaster), 
with a file called `application.yml` in the same directory which you find [here](https://github.com/Frederikam/Lavalink/blob/master/LavalinkServer/application.yml.example)

Additionally, there is an [example cog](lavalink/examples). It should be noted that the example cog is oriented towards usage with Discord.py rewrite and Lavalink v3.1+, although backwards
compatibility may be possible, it's not encouraged nor is support guaranteed.

## Features
- Regions
- Multi-Node Support
- Load Balancing (this includes region-based load balancing)
- Equalizer

## Optional Dependencies

`aiodns`   - Speed up DNS resolving.

`cchardet` - A faster alternative to `chardet`.

## Need Further Help? 
If you need further help check these links out, 

[Discord Server](https://discord.gg/SbJXU9s) 

[Documentation](https://lavalink.readthedocs.io/en/latest/)
