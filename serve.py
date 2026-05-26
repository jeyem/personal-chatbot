#!/usr/bin/env python3
import os
import argparse
import uvicorn
from pathlib import Path


os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"]  = "1"
os.environ["HF_HUB_OFFLINE"]       = "1"

from app.config import Config
from app import init_app



parser = argparse.ArgumentParser(prog="serve.py")
parser.add_argument("-c", "--config", default=Path(__file__).parent / "config.yml", metavar="PATH")

args = parser.parse_args()

cfg = Config()

app = init_app(cfg)

uvicorn.run(app, host=cfg.APP.host, port=cfg.APP.port)