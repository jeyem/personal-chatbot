#!/usr/bin/env python3
import argparse
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# must be done before importing app
load_dotenv()

from app import init_app
from app.config import Config

parser = argparse.ArgumentParser(prog="serve.py")
parser.add_argument("-c", "--config", default=Path(__file__).parent / "config.yml", metavar="PATH")

args = parser.parse_args()

cfg = Config()

app = init_app(cfg)

uvicorn.run(app, host=cfg.APP.host, port=cfg.APP.port)
