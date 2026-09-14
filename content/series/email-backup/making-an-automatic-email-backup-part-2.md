+++
title = "Making an Automatic Email Backup - Part 2"
date = 2021-10-09
updated = 2024-04-15
path = "making-an-automatic-email-backup-part-2"
description = "Adding self-signed SSL certificates to Dovecot and installing Roundcube, so the local mail archive is reachable from any browser on the network."

[taxonomies]
category = ["Self Hosting"]
tag = ["data hoarder", "email"]
+++

### UPDATE: [PART 3 ](/making-an-automatic-email-backup-part-3)has instructions for email backup using pre-made docker images based on this post and Part 1.

[<--- Part 1](/making-an-automatic-email-backup)

## Summary so far

Ok, so if you have gone through Part 1 already, you have Mbsync set up to sync all emails from your remote IMAP server and then Dovecot set up to host those emails on a local SMTP server, but without SSL.

That may be enough for many, but we can take things a step further. In this part, we will add self-signed SSL certificates for Dovecot, and we will install [Roundcube](https://roundcube.net/). Roundcube is an open sourced webmail client. We will configure it to access our local email server and then to send emails through our remote server.

Now one thing I would highly highly recommend to get the most out of this setup is to install Wireguard on your network and to set up a split-tunnel on your devices so that wherever you are, you always have access to all your local services. There are likely many of these tutorials on the internet and the instructions may vary a bit with the exact Wireguard instance you decide to use. Once you have it set up though, you will have access to all home hosted services - Pihole is always blocking ads for me on my cell phone, even on mobile, I can access router settings, Proxmox, whatever.

In this case, I can also access my "local" IMAP server from anywhere in the world without exposing the IMAP server to the wide scary internet. Of course, if you wanted, I'm sure you could also expose whatever services you want using a reverse proxy, but to me that just seems like a little less secure.

## Installing SSL

So in my home, I have created a root Certificate Authority and have many server certificates for the various services on my network, mostly used with Nginx Reverse Proxy. There are several ways to do this, but if you have Pfsense or OPNsense, it comes with a way to create and manage these certificates using a graphical format. Below is a link to the OPNsense website detailing the creation of these certificates and a great video by Allen Sampsell.

[OPNsense documentation](https://docs.opnsense.org/manual/how-tos/self-signed-chain.html)

[Youtube video by Allen Sampsell](https://www.youtube.com/watch?v=6aaSjwJhOog)

If you don't have OPNsense or PFsense, this is the website I previously followed. Everything is done by the command line so a little more work, but with good instructions:

[Self-signed SSL certificate command line instructions](https://deliciousbrains.com/ssl-certificate-authority-for-local-https-development/)

Now, pick a local DNS name for your IMAP server. For example, imap.thehelpfulidiot.lan. Use whatever router software you have to create a local DNS entry pointing to your email backup server. Once you have the server name, you can create the Server Certificate for the server.

By now you should have three things:

1. Certificate Authority Certificate
2. IMAP Server Certificate
3. IMAP Server Key

SSH into your email backup server.

Copy over your server certificate and keys. Go to the Dovecot directory and make a directory to store SSL certificates.

```bash
cd /etc/dovecot
sudo mkdir ssl
cd ssl
```

```bash
sudo nano email.pem
```

If your certificate has a "\*.crt" extension, you will need to convert it to "\*.pem" with the following command.

```bash
openssl x509 -in email.crt -out email.pem -outform PEM
```

In the new file that opens, copy and paste the contents of your server certificate file.

Ctrl+X, Y, enter.

Next, do the same with your key file.

```bash
sudo nano email.key
```

Paste the contents of your key file.

Ctrl+X, Y, enter.

Now your certificate and key files are at the following locations, respectively:

```
/etc/dovecot/ssl/email.pem
/etc/dovecot/ssl/email.key
```

Ok, so now we have to tell Dovecot where the files are and what its server name is.

```bash
cd /etc/dovecot/conf.d
```

```bash
sudo nano 10-auth.conf
```

Remove the line "disable_plaintext_auth = no" we placed in part 1 so that the default to not accept plaintext authentication will be reinstated.

Now let's edit the SSL file.

```bash
sudo nano 10-ssl.conf
```

Change "ssl = yes" to "ssl = required" towards the top.

Then you should see "ssl_cert" and "ssl_key" entries near the top as well. Change those to the appropriate file locations, but do not remove the "<" before each file path as this tells Dovecot to read the contents of the files and not just the file names.

```
ssl_cert = </etc/dovecot/ssl/email.pem
ssl_key = </etc/dovecot/ssl/email.key
```

Finally, we have to tell Dovecot what its sever name is so it knows to trust connections to it:

```bash
sudo nano /usr/share/dovecot/dovecot-openssl.cnf
```

Change the following line from:

```
commonName = @commonName@
```

to:

```
commonName = imap.thehelpfulidiot.lan
```

Now, assuming you have installed your root certificate on your devices, connecting to this IMAP server should be like connecting to any server.

## Installing Roundcube

Next, wouldn't it be cool to be able to access this email from a nice Web GUI? Roundcube is a great way to do that and is something else which can be hosted internally. Even better, it comes as a [Docker](https://hub.docker.com/r/roundcube/roundcubemail/)[ ](https://hub.docker.com/r/roundcube/roundcubemail/)[image](https://hub.docker.com/r/roundcube/roundcubemail/).

I use [Portainer ](https://docs.portainer.io/v/ce-2.9/start/intro)to easily spin up docker compose files and recommend it to anyone for simple Docker management.

Create a new stack called "Roundcube" and use the following docker compose file, edited as necessary for your setup:

```
version: '2'

services:
  roundcubemail:
    image: roundcube/roundcubemail:latest
    container_name: roundcubemail
    restart: unless-stopped
    volumes:
      - /path/to/roundcube/www:/var/www/html
      - /path/to/roundcube/ssl:/var/ssl
    ports:
      - 9002:80
    depends_on:
      - "roundcubedb"
    environment:
      - ROUNDCUBEMAIL_DB_TYPE=pgsql
      - ROUNDCUBEMAIL_DB_HOST=roundcubedb # same as pgsql container name
      - ROUNDCUBEMAIL_DB_NAME=roundcube # same as pgsql POSTGRES_DB env name
      - ROUNDCUBEMAIL_DB_USER=roundcube # same as pgsql POSTGRES_USER env name
      - ROUNDCUBEMAIL_DB_PASSWORD=roundcube # same as pgsql POSTGRES_PASSWORD env name
      - ROUNDCUBEMAIL_DB_PORT=5432
      - ROUNDCUBEMAIL_SKIN=elastic
      - ROUNDCUBEMAIL_DEFAULT_HOST=ssl://<localserver>
      - ROUNDCUBEMAIL_DEFAULT_PORT=993
      - ROUNDCUBEMAIL_SMTP_SERVER=tls://<remoteserver>
      - ROUNDCUBEMAIL_SMTP_PORT=587
     
  roundcubedb:
    image: postgres:latest
    container_name: roundcubedb
    restart: unless-stopped
    volumes:
      - /path/to/db/postgres:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=roundcube
      - POSTGRES_USER=roundcube
      - POSTGRES_PASSWORD=roundcube
```

Save your root Certificate Authority to the SSL folder you have mapped for Roundcube.

Spin that up, but don't worry about logging in just yet. Go to the folder you used for '/path/to/www'.

There should now be a bunch of files and folders generated by Roundcube's first run.

```bash
cd config
```

Edit config.inc.php

```bash
sudo nano config.inc.php
```

you should see the following:

```
<?php
    $config['plugins'] = [];
    $config['log_driver'] = 'stdout';
    $config['zipdownload_selection'] = true;
    $config['des_key'] = 'some_key';
    include(__DIR__ . '/config.docker.inc.php');
```

Just below that, add the following:

```
    $config['enable_caching'] = false;
    $config['imap_conn_options'] = array(
      'ssl'         => array(
         'verify_peer'  => true,
         'verify_depth' => 3,
         'cafile'       => '/var/ssl/rootCA.pem',
         'allow_self_signed' => true,
         'verify_peer_name' => true,
       ),
     );
     $config['smtp_user'] = 'remote_user';
     $config['smtp_pass'] = 'remote_pass';
```

Ctrl+x, y, enter.

Almost done.

Now log into Roundcube using the credentials for your Linux username and password from your email backup container.

![](/wp-content/uploads/2021/10/image-12.png)
*Roundcube Login Screen*

Go to Settings --> Identities --> and select the User which is probably something like "thehelpfulidiot@imap.thehelpfulidiot.lan". If we send an email from roundcube, we don't want that to be the identity the recipients see.

Change the Display Name and Email to your actual name and email addresses.

## Closing

That's it! Now you can log in to Roundcube as if you were using a commercial email service. You can view your emails neatly organized and send emails directly from your remote email address!

If you were so inclined, you could set up a reverse proxy and put Roundcube behind it and maybe something like [Authelia](https://github.com/authelia/authelia) and you could access your email inbox from anywhere. Personally, I'll leave something as sensitive as email safe behind my Wireguard server though.

Please let me know if you have any questions!
