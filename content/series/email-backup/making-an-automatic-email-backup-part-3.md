+++
title = "Making an Automatic Email Backup - Part 3"
date = 2022-06-22
updated = 2024-04-15
path = "making-an-automatic-email-backup-part-3"
description = "Repackaging the mbsync and Dovecot setup from Parts 1 and 2 into a pair of Docker images, configured entirely through environment variables."

[taxonomies]
category = ["Self Hosting"]
+++

[Part 1](/making-an-automatic-email-backup)

[Part 2](/making-an-automatic-email-backup-part-2)

Initially, I described a solution which required the use of LXC or some full Linux box to install and operate the necessary tools. Recently, however, I repackaged those tools into a couple docker containers, more easily deployable through a docker compose file with configuration done with environment variables.

[https://github.com/jon6fingrs/mbsync-dovecot](https://github.com/jon6fingrs/mbsync-dovecot)

[https://hub.docker.com/repository/docker/thehelpfulidiot/dovecot](https://hub.docker.com/repository/docker/thehelpfulidiot/dovecot)

[https://hub.docker.com/repository/docker/thehelpfulidiot/mbsync](https://hub.docker.com/repository/docker/thehelpfulidiot/mbsync)

Instructions on the github page. Let me know if you have any questions!
