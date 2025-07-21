#!/bin/bash
sudo mkdir -p /var/lib/ray_shared
sudo chmod 1777 /var/lib/ray_shared
ray start --head --temp-dir=/var/lib/ray_shared
