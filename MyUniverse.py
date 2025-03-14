#!/usr/bin/env python3

import sys
from src import app
from src.Configuration import Configuration

if __name__ == "__main__":
	config = Configuration()
	app.main(sys.argv)
	#test(sys.argv)
