PYTHON=python
SPHINX_DIR="docs/"
SPHINX_BUILDDIR="${SPHINX_DIR}/_build"
README="README.rst"
README_SRC="docs/templates/readme.txt"
SPHINX2RST="sphinx2rst"

SPHINX_HTMLDIR = "${SPHINX_BUILDDIR}/html"

html:
	(cd "$(SPHINX_DIR)"; $(MAKE) html)
	mv "$(SPHINX_HTMLDIR)" Documentation

docsclean:
	-rm -rf "$(SPHINX_BUILDDIR)"

htmlclean:
	-rm -rf "$(SPHINX)"

apicheck:
	(cd "$(SPHINX_DIR)"; $(MAKE) apicheck)

flakecheck:
	flake8 case

flakediag:
	-$(MAKE) flakecheck

flakepluscheck:
	flakeplus case --2.7

flakeplusdiag:
	-$(MAKE) flakepluscheck

flakes: flakediag flakeplusdiag

readmeclean:
	-rm -f $(README)

readmecheck:
	iconv -f ascii -t ascii $(README) >/dev/null

$(README):
	$(SPHINX2RST) $(README_SRC) --ascii > $@

readme: readmeclean $(README) readmecheck

test:
	nosetests -x

cov:
	nosetests -x --with-coverage --cover-html --cover-branch

removepyc:
	-find . -type f -a \( -name "*.pyc" -o -name "*$$py.class" \) | xargs rm
	-find . -type d -name "__pycache__" | xargs rm -r

gitclean: removepyc
	git clean -xdn

gitcleanforce:
	git clean -xdf

tox: removepyc
	tox

distcheck: flakecheck apicheck readmecheck test gitclean

dist: readme docsclean gitcleanforce removepyc
