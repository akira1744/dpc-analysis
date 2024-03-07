#!/bin/bash

echo "python 3.9.18" > ./.tool-versions
echo "poetry 1.7.1" >> ./.tool-versions

asdf install python 3.9.18
asdf install poetry 1.7.1

poetry init

sed -i -e 's/^python = .*/python = "3.9.18"/' pyproject.toml

poetry config virtualenvs.in-project true --local

poetry env use $(which python)

poetry run python --version

poetry add streamlit@1.3.1
poetry add pandas@1.3.5
poetry add altair@4.2.0
poetry add toolz@0.11.1
poetry add numpy@1.20.3


poetry add --group dev ipykernel@6.29.3
poetry add --group dev black@21.12b0
poetry add --group dev ruff@0.1.9
