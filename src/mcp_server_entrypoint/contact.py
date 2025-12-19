#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import sys
sys.path.append(os.getcwd())
from src.mcp.server.contact import main as server_main


def main():
    server_main()


if __name__ == "__main__":
    main()
