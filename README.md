# dray

Implementation of [Raymond's algorithm](https://en.wikipedia.org/wiki/Raymond%27s_algorithm) for mutual exclusion.

To run, first update ips.json with the ip addresses of all clients. Then run `raymond.py <id_number>` on each client. Each client may create, append to, read, or delete files with the syntax `command> <filename> [<contents>]`.

Pair programmed by Adam Freeman and Malcolm Lorber.
