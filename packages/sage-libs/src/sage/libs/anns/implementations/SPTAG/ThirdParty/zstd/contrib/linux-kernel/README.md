# Zstd in the Linux Kernel

This directory contains the scripts needed to transform upstream zstd into the version imported into
the kernel. All the transforms are automated and tested by our continuous integration.

## Upgrading Zstd in the Linux Kernel

1. `cd` into this directory.
1. Run `make libzstd` and read the output. Make sure that all the diffs printed and changes made by
   the script are correct.
1. Run `make test` and ensure that it passes.
1. Import zstd into the Linux Kernel `make import LINUX=/path/to/linux/repo`
1. Inspect the diff for sanity.
1. Check the Linux Kernel history for zstd. If any patches were made to the kernel version of zstd,
   but not to upstream zstd, then port them upstream if necessary.
1. Test the diff. Benchmark if necessary. Make sure to test multiple architectures: At least x86,
   i386, and arm.
1. Submit the patch to the LKML.
