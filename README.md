# twincat-libMBIDivB

Collection of function blocks for data acquisition and experiment control.

## Developer setup

Formatting and repository hygiene are enforced by [pre-commit](https://pre-commit.com)
hooks (see `.pre-commit-config.yaml`). They run on Windows and Linux and do not
need TwinCAT.

1. Install pre-commit once per machine (Python 3.9 or later):

   ```sh
   pip install pre-commit
   ```

2. Install the hooks once per clone:

   ```sh
   git clone https://github.com/MBI-Div-B/twincat-libMBIDivB.git
   cd twincat-libMBIDivB
   pre-commit install
   ```

   From then on the hooks run on every `git commit`. If a hook changes a file,
   the commit is aborted: review the change, `git add` the file and commit again.

3. Check the whole repository at any time:

   ```sh
   pre-commit run --all-files
   ```

   The same check runs in GitHub Actions on every push and pull request.

4. Configure TwinCAT XAE to indent with spaces, so files look the same in XAE,
   on GitHub and on Linux: in *Tools → Options → TwinCAT → PLC Environment →
   Text editor*, set the tab width and indent width to 4 and enable
   **Insert spaces**.

Editor settings (indentation, encoding, final newline, trailing whitespace) are
defined in `.editorconfig`, which the twincat-tools formatter also reads.
