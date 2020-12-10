test:
	@blender --window-geometry 0 0 1 1 --no-window-focus -P tests/__main__.py

web-serve:
	@(cd docs && bundle exec jekyll server --watch)

web-install-deps-linux:
	@sudo apt-get update
	@sudo apt-get install ruby ruby-dev rubygems
	@sudo gem install bundler github-pages
