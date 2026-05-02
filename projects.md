---
layout: page
title: "Projects"
permalink: /projects/
---

# Our Projects

At the Free Appropriate Sustainability Technology (FAST) Research Group, we are involved in a variety of exciting projects that focus on sustainable technology and open-source hardware.

{% for project in site.data.projects %}
- [{{ project.name }}](/projects/{{ project.repo | split: "/" | last }}/): {{ project.description }}
{% endfor %}
