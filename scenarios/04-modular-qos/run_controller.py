#!/usr/bin/env python3
"""
Controller Entry Point for Scenario 04

This is the entry point for running the Ryu controller.

Usage:
    ryu-manager run_controller.py
    ryu-manager run_controller.py ryu.app.ofctl_rest

Note: This should be started BEFORE running main.py
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controller.qos_controller import QoSController


# Export app for ryu-manager
app_manager = QoSController
