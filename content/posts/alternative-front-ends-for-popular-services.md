+++
title = "Alternative Front-ends for Popular Services"
date = 2024-04-09
path = "alternative-front-ends-for-popular-services"
draft = true
description = "It's no secret that the websites we all use each day extract more information from us than we often care to recognize. I am still not sure exactly the…"

[taxonomies]
category = ["Self Hosting"]
+++

It's no secret that the websites we all use each day extract more information from us than we often care to recognize. I am still not sure exactly the ramifications of so much information about me being held by tech giants, but whatever they are, they are likely not going to benefit me. Even if my personal information is being idly held in a "vault" for now, what will happen in a year? 10 years? 30 years? What I didn't realize at first when the internet was young, and Facebook, Twitter, Google, etc were seen as innovative, hopeful companies, guiding our society forward, is that this information isn't going anywhere. The more these companies gain, the more of an advantage they can have over me in manipulating me to buy something or vote for someone.

Obviously, a way to prevent this would be to disconnect myself from the internet and find a nice cave to make my home. Seeing as how I am sharing these thoughts through a blog, that isn't what I want to do, nor is it realistic. I enjoy browsing Reddit, watching funny TikTok videos my friends send me.

That's why this recent discovery for me has been so exciting.

## Privacy Respecting Front-ends

There is a growing list of self-hostable projects which communicate with the remote service in question (Twitter, Reddit, Instagram, etc.).

[https://github.com/mendel5/alternative-front-ends](https://github.com/mendel5/alternative-front-ends)

Here is one of the more comprehensive lists I have come across. Basically, you install one of these applications, typically using docker. You set up a local hostname on your LAN, and can use certain browser extensions to redirect any of your Twitter links to your Nitter instance, or any Reddit links to your Libreddit instance.

The alternative frontend communicates directly with the website in question, and then serves the cookie-less, java-less, privacy-respecting content to your web browser for easy viewing.

I haven't tried all of the available options, but have set up many of the front-ends I have come across and am always on the lookout for more. Below, I wanted to share a summary/review of the services I have been using daily.

## Whoogle

[https://hub.docker.com/r/benbusby/whoogle-search](https://hub.docker.com/r/benbusby/whoogle-search)

In my opinion, this is the best/most important front-end on the list. Google likely knows more about each of us than our own mothers.

Whoogle returns those same search results, but does so anonymously and does not allow Google to communicate directly with the client computer. The service is easily deployable through docker and can be set as a default search engine just like any other.

![](/wp-content/uploads/2022/06/image-1.png)
*Google*

![](/wp-content/uploads/2022/06/image-2.png)
*Whoogle*

As you can see, the results are extremely similar, except that Whoogle does not need me to sign in so that I can open speedtest.net.

## Nitter

[https://github.com/zedeus/nitter](https://github.com/zedeus/nitter)

## Invidious

## Libreddit

## Bibliogram

## Proxitok

## Libremdb

## Quetre

## Wikiless

## Rimgo

## Neuters
