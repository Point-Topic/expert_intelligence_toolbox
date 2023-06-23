## Internal:
Follow this:
https://packaging.python.org/en/latest/tutorials/packaging-projects/

A package needs:

- pyproject.toml (used to define the metadata and configuration for your package. It provides information such as the package name, version, dependencies, and other details required for installation and distribution.)
- README.md: This file contains the documentation and information about your package. It is commonly written in Markdown format and serves as the main entry point for users and developers to understand how to use your package.

- LICENSE: This file includes the license under which your package is distributed. It is important to choose and include the appropriate license file, as we discussed in the previous response.

- requirements.txt or pyproject.toml: These files are used to specify the dependencies required by your package. requirements.txt is a common format that lists the package names and versions, while pyproject.toml is used in the context of projects using the Poetry dependency manager.


# How to get the package ready.

**For Unix/MacOS**: see this https://packaging.python.org/en/latest/tutorials/packaging-projects/

1 - Make a 'wheel' and source distribution file (you pack the source code as binary and tar file)
`python3 -m pip install --upgrade build`
`py -m pip install --upgrade build`
`py -m build`

2 - go to https://test.pypi.org/account/register/ and complete the steps on that page. Verify your email address.

3 - To securely upload your project, you’ll need a PyPI API token. Create one at https://test.pypi.org/manage/account/#api-tokens, setting the “Scope” to “Entire account”. Don’t close the page until you have copied and saved the token — you won’t see that token again.

4 - Upload to PyPI test index (windows)
`py -m pip install --upgrade twine`
`py -m twine upload --repository testpypi dist/*`

4 - Upload to PyPI test index (Mac)
`python3 -m pip install --upgrade twine`
`python3 -m twine upload --repository testpypi dist/*`


Username: __token__
PW: enter your token here (WARNING - CTRL-V WILL NOT WORK. IN VSCODE: Edit --> Paste)
**Note**: 
- Be carefull to check whether you're using the `pypi` or `test.pypi` to access the package.
This tutorial is for `test.pypi`, so if you're using `pypi`, please change from `--repository testpypi` into `--repository pypi`
- If you can't not get to the package using `API key`, using (not recommend, may cause leak private information)
```bash
twine upload -u YOUR-USERNAME -p YOUR-PASSWORD --repository testpypi dist/*
```

5 - you can pull your own package from 
py -m pip install --index-url https://test.pypi.org/simple/ --no-deps expert_intelligence_toolbox

6 - make a real package
delete `dist` directory
`py -m build`
`py -m twine upload dist/*`
Username: __token__
PW: enter your token here (WARNING - CTRL-V WILL NOT WORK. IN VSCODE: Edit --> Paste)


5 - What if you make any changes? Just repeat.

Change version number in pyproject.toml

Then, For Windows:
`py -m pip install --upgrade build`
`py -m build`
Or, for Mac:
`python3 -m pip install --upgrade build`
`python3 -m build`

Finally, for both:
`twine upload --skip-existing dist/*` (for real package)
`twine upload --skip-existing --repository testpypi dist/*` (for testpypi)