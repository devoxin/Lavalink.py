<img align="right" src="https://serux.pro/9e83af1581.png" height="150" width="150">

# Lavalink.py

Lavalink.py is a wrapper for [Lavalink](https://github.com/Frederikam/Lavalink) which abstracts away most of the code necessary to use Lavalink to allow for easier integration into your bots, while still promising full API coverage and powerful tools to get the most out of it.

# Getting Started
First you need to run a command to install the library,
```shell
pip install lavalink
```

Then you need to setup the Lavalink server, you will need to install Java, and then download the latest [Lavalink.jar] (https://github.com/Frederikam/Lavalink/releases/).
Then place an ``application.yml`` file in the same directory. The file should look like [this] (https://github.com/Frederikam/Lavalink/blob/master/LavalinkServer/application.yml.example/). Finally run `java -jar Lavalink.jar` in the directory of the jar.

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
[Discord Server](https://discord.gg/SbJXU9s) 

[Documentation](https://lavalink.readthedocs.io/en/latest/)
