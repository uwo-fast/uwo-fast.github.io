---
layout: page
title: "Lab Signs"
permalink: /signs/
---

# Lab Signs

The printed safety signs posted in the FAST lab, published so others can see and adapt
them. Each page carries the status of that sign and who has to review it.

These are written for one lab and its equipment. They are not general safety guidance.
Follow your own workplace procedures wherever you work.

{% assign signs = site.signs | sort: "title" %}
{% for sign in signs %}
- [{{ sign.title }}]({{ sign.url | relative_url }}) — {{ sign.status }}{% if sign.last_updated %}, updated {{ sign.last_updated }}{% endif %}
{% endfor %}

## Equipment records

Longer reference documents for specific equipment. These are not posted on the wall.

{% assign records = site.equipment | sort: "title" %}
{% for record in records %}
- [{{ record.title }}]({{ record.url | relative_url }})
{% endfor %}
