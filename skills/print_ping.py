#!/usr/bin/env python3
import sys
import datetime

name = sys.argv[1] if len(sys.argv) > 1 else "User"
print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🔔 PING! Yo {name}, your 10 seconds are up! 🐼")