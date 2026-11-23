"""The host (boundaries §2.2, layer 8): the process that owns the world and talks to clients.

In this step it holds the per-launch tokens, the sessions and their time authority, and the WebSocket server's
handshake (boundaries §5.3). The pacing loop, lanes and the log writer join at their steps. Beside the verification
harness in one layer, it never imports it; nothing below imports the host.
"""
