+++
title = "Making an Automatic Email Backup (Updated 9/15/2024)"
date = 2024-09-15
updated = 2024-09-16
path = "making-an-automatic-email-backup-updated-9-15-2024"
description = "This is basically an update to the project I discussed in these three previous posts:"

[taxonomies]
category = ["Self Hosting"]
+++

This is basically an update to the project I discussed in these three previous posts:

Part 1 - [https://thehelpfulidiot.com/making-an-automatic-email-backup](/making-an-automatic-email-backup)

Part 2 -[https://thehelpfulidiot.com/making-an-automatic-email-backup-part-2](/making-an-automatic-email-backup-part-2)

Part 3 - [https://thehelpfulidiot.com/making-an-automatic-email-backup-part-3](/making-an-automatic-email-backup-part-3)

I have been using this method of backing up emails for the past several years and have been very please with the reliability. It has not required any modification or tinkering and has just seemed to work.

Having said that, even though it works reliably and doesn't need to be fixed, that doesn't mean I shouldn't try.

[https://github.com/jon6fingrs/mbsync-dovecot](https://github.com/jon6fingrs/mbsync-dovecot)

Enter this newest interation of my docker images for Mbsync and Dovecot. It uses updated versions of the software of course, but I have also made a few big changes which may be of use to some of you.

## Solr

Now includes Solr integration!

[Solr](https://solr.apache.org/) is an indexing and search platform. Previously, if performing a remote IMAP search through a generic IMAP client (some search their offline index), it would search each email sequentially and so could take a LONG time. Now, by deploying Solr at the same time, the search is MARKEDLY improved when I search using the Apple Mail app.

The solr docker container I have made includes the necessary setup for Dovecot, and the Dovecot container will look for the Solr container and so neither will now work without the other.

The solr container also includes cron and will write commits every 5 minutes and will optimize the database each night.

## Mbsync Timing

Previously, the mbsync container would run once and then quit. Now, it will run to synchronize the mailbox, and then afterwards, it will open cron as the primary process, which will check for mail each 5 minutes. This avoids having to set a manual cronjob and keeps the container running.

If you want your own sync schedule, you can deactivate the built in cron with an environment variable and use whatever interval you would like.

## Better Environment Variables

Some of the environment variables are now optional, and more intuitive. The run scripts are more robust.

## What's the point?

But why did I do this? What's the point? Well, I would love to have my own mail server, but I am too worried about the administrative burden and dropped emails. This way, I feel like I am able to offload some of my dependence on the cloud by downloading and archiving every email, and just periodically purging my cloud provide inbox.

I have a complete email archive with all emails since my accounts opened. This is offline and does not require increasing my available cloud storage more and more.

Also, because I could.

So check it out if that sounds interesting and let me know how it works:

[https://github.com/jon6fingrs/mbsync-dovecot](https://github.com/jon6fingrs/mbsync-dovecot)
