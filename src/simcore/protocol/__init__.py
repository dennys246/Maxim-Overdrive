"""What the client receives: rendering tiers (``tiers``) and display quantization (``encoding``).

The wire protocol (decode, encode, the frame grammar) joins this layer in plan step 7. The core never imports it, so
nothing a client is shown can feed back into the physics.
"""
