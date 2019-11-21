.. currentmodule:: lavalink

Changelog
=========

3.1.0
-----
Breaking Changes
~~~~~~~~~~~~~~~~
* ``Client.players`` is now :attr:`Client.player_manager`, to be more consistent
* Removed ``AudioTrack.preferences`` as it's replaced by :attr:`AudioTrack.extras`
* Removed ``pool_size`` parameter from :attr:`Client`

Bug Fixes
~~~~~~~~~
* Fixed :attr:`DefaultPlayer.set_gains` conditional, as before it could never be true when checking for invalid bands.
* :attr:`Client.get_tracks`, :attr:`Client.decode_track`, and :attr:`Client.decode_tracks` now throw errors if no nodes are available for it to search through tracks.
* :attr:`BasePlayer.cleanup` is now called when :attr:`PlayerManager.destroy` is called.

New Features
~~~~~~~~~~~~
* Added `event` and `hooks` parameter to :attr:`Client.add_event_hook`. `hooks` parameter may now be an iterable.
* Added `connect_back` parameter to :attr:`Client`, which connects a player back to its original node from its current node.
* Added `end_time` and `no_replace` parameters to :attr:`DefaultPlayer.play`.
* Added :attr:`AudioTrack` as a parameter to :attr:`DefaultPlayer.add`.
* Added India to :attr:`NodeManager.regions`.
* Added a new event
    * Added :attr:`WebSocketClosedEvent` that is dispatched when the audio websocket to Discord is closed.
* Added new exceptions
    * Added :attr:`NodeException`.
    * Added :attr:`Unauthorized`.
    * Added :attr:`InvalidTrack`.
    * Added :attr:`TrackNotBuilt`.

Extras
~~~~~~
* :attr:`AudioTrack` is now subscriptable once the track is built, so you can access the track's attributes like a dictionary.
* :attr:`lavalink.enable_debug_logging` now shows the version of Lavalink.py to make it easier to diagnose bugs.
* Players that have a dead node will be moved to a queue, once a new node is available it will auto connect.
* Performance
    * Better memory handling as :attr:`Stats`, :attr:`Penalty`, and all event classes use ``__slots__``.
    * Changed :attr:`DefaultPlayer.queue` to ``collections.deque`` object.
* Documentation & Diagnosis
    * More actions are logged to help diagnose bugs.
    * Clearer and better documentations for objects and functions.