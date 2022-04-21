.. currentmodule:: lavalink

Documentation
=============

.. autofunction:: enable_debug_logging

.. autofunction:: listener

.. autofunction:: add_event_hook

Client
------
.. autoclass:: Client
    :members:

Errors
------
.. autoclass:: NodeError

.. autoclass:: AuthenticationError

.. autoclass:: InvalidTrack

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

.. autoclass:: WebSocketClosedEvent
    :members:

Filters
-------
**All** custom filters must derive from :class:`Filter`

.. autoclass:: Filter
    :members:

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

Models
------
**All** custom players must derive from :class:`BasePlayer`

.. autoclass:: AudioTrack
    :members:

.. autoclass:: DeferredAudioTrack
    :members:

.. autoenum:: LoadType
    :members:

.. autoclass:: PlaylistInfo
    :members:

.. autoclass:: LoadResult
    :members:

.. autoclass:: Source
    :members:

.. autoclass:: BasePlayer
    :members:

.. autoclass:: DefaultPlayer
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
