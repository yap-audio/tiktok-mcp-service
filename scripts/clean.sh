#!/bin/bash
# kill_chromium.sh: Kills all Chromium processes on macOS

# List all processes with "chromium" (case-insensitive), excluding the grep process itself,
# then extract the PID (the second field from ps aux output).
PIDS=$(ps aux | grep -i chromium | grep -v grep | awk '{print $2}')

# Check if any PIDs were found
if [ -z "$PIDS" ]; then
  echo "No Chromium processes found."
  exit 0
fi

# Loop over each PID and kill it forcefully.
for PID in $PIDS; do
  echo "Killing process with PID: $PID"
  kill -9 "$PID"
done

echo "All Chromium processes have been killed."