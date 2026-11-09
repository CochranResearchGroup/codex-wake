# Preserve saved terminal sessions independently of native liveness

Accepted during the LOCAL-P211 design interview, round1: a terminal session's
saved definition survives losing its final tab, while its native container may
cease to exist. Native-container-only identity would make named destinations such
as `bots` disappear as work finishes; a persistent definition lets them remain
available and recreate the container when needed. Lists must distinguish a saved
empty session from a running one; retaining a definition does not keep or restart
agent processes. Existing native sessions remain discoverable.
