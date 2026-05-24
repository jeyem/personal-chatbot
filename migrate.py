#!/usr/bin/env python3
import os
import subprocess
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(prog="migrate.py")
parser.add_argument("-c", "--config", default=Path(__file__).parent / "config.yml", metavar="PATH")

sub = parser.add_subparsers(dest="command", required=True)
sub.add_parser("upgrade")
sub.add_parser("downgrade")
sub.add_parser("history")
revision = sub.add_parser("revision")
revision.add_argument("-m", "--message", required=True)

args = parser.parse_args()

env = os.environ.copy()
env["CONFIG_PATH"] = str(args.config)

if args.command == "upgrade":
    cmd = ["alembic", "upgrade", "head"]
elif args.command == "downgrade":
    cmd = ["alembic", "downgrade", "-1"]
elif args.command == "history":
    cmd = ["alembic", "history"]
elif args.command == "revision":
    cmd = ["alembic", "revision", "--autogenerate", "-m", args.message]

subprocess.run(cmd, env=env, check=True)