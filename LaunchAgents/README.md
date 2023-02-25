# To use

1. For easiness, install lunchy: `gem install lunchy`
2. Edit a copy of this file for use filling in the path to Python, the script, server host, and path to search
3. Add the port argument (`-P`) if necessary
4. Add any other arguments you would like _except_ `-d` (debug) or `-v` (verbose), unless you add keys `StandardOutPath` and `StandardErrorPath` with paths to valid files to write to.
5. Put your copy of the plist file into `~/Library/LaunchAgents`
6. If you kept the name of the agent the same, you can enable and start it with: `lunchy start -w sh.tat.XirvikStartTorrents`, otherwise fix the service name.
