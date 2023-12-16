.. currentmodule:: lavalink

Documentation
=============

.. autofunction:: listener

ABC
---
.. autoclass:: BasePlayer
    :members:

.. autoclass:: DeferredAudioTrack
    :members:

.. autoclass:: Source
    :members:

.. autoclass:: Filter
    :members:

Client
------
.. autoclass:: Client
    :members:

Errors
------
.. autoclass:: ClientError

.. autoclass:: AuthenticationError

.. autoclass:: InvalidTrack

.. autoclass:: LoadError

.. autoclass:: RequestError
    :members:

.. autoclass:: PlayerErrorEvent
    :members:

Events
------
All Events are derived from :class:`Event`

.. autoclass:: Event
    :members:

.. autoclass:: TrackStartEvent
    :members:

.. autoclass:: TrackStuckEvent
    :members:

.. autoclass:: TrackExceptionEvent
    :members:

.. autoclass:: TrackEndEvent
    :members:

.. autoclass:: TrackLoadFailedEvent
    :members:

.. autoclass:: QueueEndEvent
    :members:

.. autoclass:: PlayerUpdateEvent
    :members:

.. autoclass:: NodeConnectedEvent
    :members:

.. autoclass:: NodeDisconnectedEvent
    :members:

.. autoclass:: NodeChangedEvent
    :members:

.. autoclass:: NodeReadyEvent
    :members:

.. autoclass:: WebSocketClosedEvent
    :members:

.. autoclass:: IncomingWebSocketMessage
    :members:

Filters
-------
**All** custom filters must derive from :class:`Filter`

.. autoclass:: Equalizer
    :members:

.. autoclass:: Karaoke
    :members:

.. autoclass:: Timescale
    :members:

.. autoclass:: Tremolo
    :members:

.. autoclass:: Vibrato
    :members:

.. autoclass:: Rotation
    :members:

.. autoclass:: LowPass
    :members:

.. autoclass:: ChannelMix
    :members:

.. autoclass:: Volume
    :members:

.. autoclass:: Distortion
    :members:

Player
------
**All** custom players must derive from :class:`BasePlayer`

.. autoclass:: DefaultPlayer
    :members:

Server
------
.. autoclass:: AudioTrack
    :members:

.. autoenum:: EndReason
    :members:

.. autoenum:: LoadType
    :members:

.. autoenum:: Severity
    :members:

.. autoclass:: PlaylistInfo
    :members:

.. autoclass:: LoadResultError
    :members:

.. autoclass:: LoadResult
    :members:

.. autoclass:: Plugin
    :members:

Node
----
.. autoclass:: Node
    :members:

Node Manager
------------
.. autoclass:: NodeManager
    :members:

Player Manager
--------------
.. autoclass:: PlayerManager
    :members:

Stats
-----
.. autoclass:: Stats
    :members:

.. autoclass:: Penalty
    :members:

Utilities
---------
.. autofunction:: timestamp_to_millis

.. autofunction:: format_time

.. autofunction:: parse_time

.. autofunction:: decode_track

.. autofunction:: encode_track
