# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINX_OPTIONS ?=
SPHINX_BUILD   ?= sphinx-build
SOURCE_DIR      = doc
BUILD_DIR       = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINX_BUILD) -M help "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTIONS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINX_OPTIONS).
%: Makefile
	@$(SPHINX_BUILD) -M $@ "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTIONS) $(O)
