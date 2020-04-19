.. currentmodule:: lavalink

Documentation
=============

.. autofunction:: enable_debug_logging

.. autofunction:: add_event_hook

Client
------
.. autoclass:: Client
    :members:

Events
------
All Events are derived from :class:`Event`

.. autoclass:: Event
    :members:

.. autoclass:: TrackStartEvent
    :members:

.. autoclass:: TrackEndEvent
    :members:

.. autoclass:: TrackStuckEvent
    :members:

.. autoclass:: TrackExceptionEvent
    :members:

.. autoclass:: QueueEndEvent
    :members:

.. autoclass:: NodeConnectedEvent
    :members:

.. autoclass:: NodeChangedEvent
    :members:

.. autoclass:: NodeDisconnectedEvent
    :members:

.. autoclass:: WebSocketClosedEvent
    :members:

Models
------
**All** custom players must derive from :class:`BasePlayer`

.. autoclass:: AudioTrack
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
.. autofunction:: format_time

.. autofunction:: parse_time

.. autofunction:: decode_track