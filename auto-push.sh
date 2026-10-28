#!/bin/bash

# Auto push script for Train-Delay-Predictor
echo "Checking for changes..."

git add -A

# Check if there are staged changes
if [ -z "$(git diff --cached --name-only)" ]; then
  echo "No changes to push."
  exit 0
fi

# Ask for commit message or use timestamp
echo "Enter commit message (leave blank for auto message):"
read -r msg

if [ -z "$msg" ]; then
  TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
  msg="update: $TIMESTAMP"
fi

git commit -m "$msg"
echo "Committed: $msg"

git push origin main
echo "✅ Pushed to GitHub successfully!"
