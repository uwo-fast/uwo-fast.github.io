source "https://rubygems.org"

# The site builds in .github/workflows/jekyll.yml and deploys with
# actions/deploy-pages, not with GitHub's built-in Pages build, so it runs
# plain Jekyll rather than the github-pages gem (#13).
gem "jekyll", "~> 4.4"
gem "just-the-docs"

group :jekyll_plugins do
  gem "jekyll-feed"
  gem "jekyll-seo-tag"
end

# `jekyll serve` needs webrick on Ruby 3.
gem "webrick"

# Windows and JRuby have no zoneinfo files of their own.
gem "tzinfo-data", platforms: [:windows, :jruby]
