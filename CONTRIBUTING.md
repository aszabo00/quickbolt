# Contributing

## Found a Bug?

If you find a bug in the source code, you can help by submitting an issue to the GitHub Repository. Even better, you can submit a Pull Request with a fix.

## Submit an Issue

Please fill the following information in each issue you submit:

* Title: Use a clear and descriptive title for the issue to identify the problem.
* Description: Description of the issue.
* Version: The version under question.
* Repository: Link to the repository you are working with.
* Operating system: The operating system used.
* How often it reproduces?: What percentage of the time does it reproduce?
* Steps to Reproduce: Numbered step by step (1., 2., 3., …).
* Expected behavior: What you expect to happen.
* Actual behavior: What actually happens.
* Additional information: Any additional to help to reproduce (screenshots, animated gifs).

## Pull Requests

1. Fork the project
2. Implement the feature or bug fix
3. Add test cases
4. Run `. scripts/code_quality/linter.sh`
5. Ensure the test cases & static analysis run successfully (`. tests/run_tests.sh`)
6. Submit a pull request to `master` branch
7. Include the test results in the pull request

### The Pull Request scheme:

 * Description: A light story telling of the changes made and why.
 * Ticket: If existing, the ticket for tracking this work.
 * Test Steps: Any special steps or info needed to test the PR. If all there is to do is run the tests, just say so.
 * Run Logs: Proof the changes work and haven't broken anything.
 
## Coding Guidelines

* All features or bug fixes **must be tested**
* All code must follow [Python's PEP 8 style](https://www.python.org/dev/peps/pep-0008/)

## Commit messages

Any line of a commit message cannot be longer than 100 characters! This allows the message to be easier
to read on GitHub as well as in various git tools.

Each commit message consists of a subject, body, and footer.

```
<subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```

### Subject

The subject contains a brief summary of the change.

### Body

The body should include the motivation for the change and a contrast of the previous behavior.

### Footer

The footer should contain any information about **Breaking Changes** and/or reference GitHub issues that this commit **Closes** (it should contain a [closing reference to an issue](https://help.github.com/articles/closing-issues-via-commit-messages/) if applicable).