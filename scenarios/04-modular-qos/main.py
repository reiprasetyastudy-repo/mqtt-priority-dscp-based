#!/usr/bin/env python3
"""
Main Entry Point for Scenario 04 - Modular QoS

Usage:
    python3 main.py [--duration SECONDS] [--cli]

Examples:
    python3 main.py --duration 300      # Run for 5 minutes
    python3 main.py --cli               # Run with Mininet CLI
"""

import argparse
import os
import sys
from mininet.log import setLogLevel

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config_loader import load_config
from core.topology import HierarchicalTopology
from utils.logger import ScenarioLogger, get_mininet_logger


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Scenario 04: Modular SDN-based QoS for IoT'
    )
    parser.add_argument(
        '--duration',
        type=int,
        help='Simulation duration in seconds (omit for CLI mode)'
    )
    parser.add_argument(
        '--cli',
        action='store_true',
        help='Start Mininet CLI after MQTT (overrides --duration)'
    )
    parser.add_argument(
        '--config',
        default='config/scenario_config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    return parser.parse_args()


def main():
    """Main execution flow"""
    args = parse_args()

    # Load configuration
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        args.config
    )
    config = load_config(config_path)

    # Create results directory
    os.makedirs(config.paths.results_dir, exist_ok=True)
    os.makedirs(config.paths.log_dir, exist_ok=True)

    # Initialize logger
    logger = ScenarioLogger(
        name="topology",
        log_dir=config.paths.log_dir,
        level=args.log_level,
        log_format=config.logging.format
    )

    # Set Mininet log level
    setLogLevel(get_mininet_logger(args.log_level))

    # Print configuration summary
    logger.separator()
    logger.info(f"Starting {config.name} - {config.description}")
    logger.info(f"Version: {config.version}")
    logger.separator()
    logger.info(f"Network Utilization: {config.calculate_utilization():.1%}")
    logger.info(f"Bandwidth: {config.network.bandwidth_mbps} Mbps")
    logger.info(f"Message Rate: {config.mqtt.message_rate} msg/s per publisher")
    logger.info(f"Total Publishers: {config.mqtt.total_publishers}")
    logger.info(f"Results Directory: {config.paths.results_dir}")
    logger.separator()

    # Determine duration
    duration = None if args.cli else args.duration

    # Create and run topology
    topology = HierarchicalTopology(config, logger)

    try:
        topology.run(duration=duration)
    except KeyboardInterrupt:
        logger.info("\n\nSimulation interrupted by user")
    except Exception as e:
        logger.exception(f"Error during simulation: {e}")
        raise
    finally:
        logger.separator()
        logger.info("Simulation complete")
        logger.separator()


if __name__ == '__main__':
    main()
