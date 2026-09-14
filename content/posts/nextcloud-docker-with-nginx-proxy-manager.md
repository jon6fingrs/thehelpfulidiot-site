+++
title = "Nextcloud Docker with Nginx Proxy Manager"
date = 2024-03-31
updated = 2024-04-09
path = "nextcloud-docker-with-nginx-proxy-manager"
description = "Nextcloud has become an integral part of my work flow these days. I love having a \"place\" to go that's totally mine. I have been running it from a docker…"

[taxonomies]
category = ["Self Hosting"]
+++

Nextcloud has become an integral part of my work flow these days. I love having a "place" to go that's totally mine. I have been running it from a [docker container](https://hub.docker.com/_/nextcloud) since before the[ AIO images](https://github.com/nextcloud/all-in-one) were available and so have not had a reason to change.

The container comes in two flavors- Apache vs php-fpm. The I had been running the Apache version since it is generally easier, but always hated the idea of using Nginx Proxy Manager in front of Apache. It just seemed like a redundancy. Finally, I started to get some weird behaviors in Nextcloud which I tracked down as some webserver problem.

So now I have the perfect opportunity to fix something that really isn't breaking by doing wayyyy too much work.

I decided to try the php-fpm version and really wanted to take advantage of Nginx Proxy Manager and not have to use a second Nginx container!

Looking far and wide on the internet, most people said it was impossible, but I found really this single post that laid is out pretty nicely.

[https://help.nextcloud.com/t/docker-nextcloud-fpm-behind-nginx-proxy-manager-do-i-need-another-nginx-container/133431/6](https://help.nextcloud.com/t/docker-nextcloud-fpm-behind-nginx-proxy-manager-do-i-need-another-nginx-container/133431/6)

It turned out to be much easier than expected and I was essentially able to seamlessly swap out the Apache image for the php-fpm image by updating the docker compose file.

I did, however, update the nginx proxy configuration a bit from what was in that link to resolve various errors, to add the built-in collabora server, and to add push notifications.

```
	# set max upload size
        client_max_body_size 512M;
        fastcgi_buffers 64 4K;



	include mime.types;
	types 
	{
		application/javascript mjs;
	}

        # Enable gzip but do not remove ETag headers
        gzip on;
        gzip_vary on;
        gzip_comp_level 4;
        gzip_min_length 256;
        gzip_proxied expired no-cache no-store private no_last_modified no_etag auth;
        gzip_types application/atom+xml application/javascript application/json application/ld+json application/manifest+json application/rss+xml application/vnd.geo+json application/vnd.ms-fontobject application/x-font-ttf application/x-web-app-manifest+json application/xhtml+xml application/xml font/opentype image/bmp image/svg+xml image/x-icon text/cache-manifest text/css text/plain text/vcard text/vnd.rim.location.xloc text/vtt text/x-component text/x-cross-domain-policy;

        # Pagespeed is not supported by Nextcloud, so if your server is built
        # with the `ngx_pagespeed` module, uncomment this line to disable it.
        #pagespeed off;

        # HTTP response headers borrowed from Nextcloud `.htaccess`
        add_header Referrer-Policy                      "no-referrer"       always;
        add_header X-Content-Type-Options               "nosniff"           always;
        add_header X-Download-Options                   "noopen"            always;
        add_header X-Frame-Options                      "SAMEORIGIN"        always;
        add_header X-Permitted-Cross-Domain-Policies    "none"              always;
        add_header X-Robots-Tag                         "noindex, nofollow" always;
        add_header X-XSS-Protection                     "1; mode=block"     always;

        # Remove X-Powered-By, which is an information leak
        fastcgi_hide_header X-Powered-By;

        # Path to the root of your installation
        root /var/www/html;

        # Specify how to handle directories -- specifying `/index.php$request_uri`
        # here as the fallback means that Nginx always exhibits the desired behaviour
        # when a client requests a path that corresponds to a directory that exists
        # on the server. In particular, if that directory contains an index.php file,
        # that file is correctly served; if it doesn't, then the request is passed to
        # the front-end controller. This consistent behaviour means that we don't need
        # to specify custom rules for certain paths (e.g. images and other assets,
        # `/updater`, `/ocm-provider`, `/ocs-provider`), and thus
        # `try_files $uri $uri/ /index.php$request_uri`
        # always provides the desired behaviour.
        index index.php index.html /index.php$request_uri;

        # Rule borrowed from `.htaccess` to handle Microsoft DAV clients
        location = / {
            if ( $http_user_agent ~ ^DavClnt ) {
                return 302 /remote.php/webdav/$is_args$args;
            }
        }

        location = /robots.txt {
            allow all;
            log_not_found off;
            access_log off;
        }

        # Make a regex exception for `/.well-known` so that clients can still
        # access it despite the existence of the regex rule
        # `location ~ /(\.|autotest|...)` which would otherwise handle requests
        # for `/.well-known`.
        location ^~ /.well-known {
            # The rules in this block are an adaptation of the rules
            # in `.htaccess` that concern `/.well-known`.

            location = /.well-known/carddav { return 301 /remote.php/dav/; }
            location = /.well-known/caldav  { return 301 /remote.php/dav/; }

            location /.well-known/acme-challenge    { try_files $uri $uri/ =404; }
            location /.well-known/pki-validation    { try_files $uri $uri/ =404; }

            # Let Nextcloud's API for `/.well-known` URIs handle all other
            # requests by passing them to the front-end controller.
            return 301 /index.php$request_uri;
        }

        # Rules borrowed from `.htaccess` to hide certain paths from clients
        location ~ ^/(?:build|tests|config|lib|3rdparty|templates|data)(?:$|/)  { return 404; }
        location ~ ^/(?:\.|autotest|occ|issue|indie|db_|console)                { return 404; }



        # Ensure this block, which passes PHP files to the PHP process, is above the blocks
        # which handle static assets (as seen below). If this block is not declared first,
        # then Nginx will encounter an infinite rewriting loop when it prepends `/index.php`
        # to the URI, resulting in a HTTP 500 error response.
        location ~ \.php(?:$|/) {
            # Required for legacy support
            rewrite ^/(?!index|remote|public|cron|core\/ajax\/update|status|ocs\/v[12]|updater\/.+|oc[ms]-provider\/.+|.+\/richdocumentscode\/proxy) /index.php$request_uri;

            fastcgi_split_path_info ^(.+?\.php)(/.*)$;
            set $path_info $fastcgi_path_info;

            try_files $fastcgi_script_name =404;

            include fastcgi_params;
            fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
            fastcgi_param PATH_INFO $path_info;
            #fastcgi_param HTTPS on;

            fastcgi_param modHeadersAvailable true;         # Avoid sending the security headers twice
            fastcgi_param front_controller_active true;     # Enable pretty urls
            fastcgi_pass nextcloud-nextcloud-1:9000;

            fastcgi_intercept_errors on;
            fastcgi_request_buffering off;
        }

    	location ~ \.(?:css|js|mjs|svg|gif|png|jpg|ico|wasm|tflite|map|ogg|flac)$ {
            try_files $uri /index.php$request_uri;
            expires 6M;         # Cache-Control policy borrowed from `.htaccess`
            access_log off;     # Optional: Don't log access to assets
    	}

        location ~ \.woff2?$ {
            try_files $uri /index.php$request_uri;
            expires 7d;         # Cache-Control policy borrowed from `.htaccess`
            access_log off;     # Optional: Don't log access to assets
        }

        # Rule borrowed from `.htaccess`
        location /remote {
            return 301 /remote.php$request_uri;
        }

	location ^~ /push/ {
        	proxy_pass http://nextcloud_notify:7867/;
        	proxy_http_version 1.1;
        	proxy_set_header Upgrade $http_upgrade;
        	proxy_set_header Connection "Upgrade";
        	proxy_set_header Host $host;
        	proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        	}




        location / {
            try_files $uri $uri/ /index.php$request_uri;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_set_header X-Forwarded-Host $server_name;
        }
```

This has worked for Nextcloud 28.

Otherwise, the post pretty much explains everything else!
