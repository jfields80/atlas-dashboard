# ATLAS-THROUGHPUT-004 — concurrency proof

Two simultaneous same-key requests (stub builder, 1 s): statuses ['HIT_AFTER_WAIT', 'MISS'], BUILD_EXECUTED = 1, REUSE_AFTER_WAIT = 1,
digests equal = True. Two different keys: statuses ['MISS', 'MISS'], BUILD_EXECUTED = 2, builds overlapped = True (wall 1.794 s).

Mechanism: a per-key thread lock plus a per-key `O_EXCL` lock file (holder pid, run id, time); a waiter
re-looks-up after the holder releases and verifies the published artifact before reusing it; a lock older
than the timeout is broken (a dead holder). No global cache lock; no distributed locking.
