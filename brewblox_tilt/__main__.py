"""
Brewblox service for Tilt hydrometer
"""
from brewblox_service import mqtt, scheduler, service

from brewblox_tilt import tiltScanner


def create_parser(default_name="tilt"):
    parser = service.create_parser(default_name=default_name)

    parser.add_argument("--lower-bound",
                        help="Lower bound of acceptable SG values. "
                        "Out-of-bounds measurement values will be discarded. [%(default)s]",
                        type=float,
                        default=0.5)
    parser.add_argument("--upper-bound",
                        help="Upper bound of acceptable SG values. "
                        "Out-of-bounds measurement values will be discarded. [%(default)s]",
                        type=float,
                        default=2)

    # Assumes a default configuration of running with --net=host
    parser.set_defaults(mqtt_protocol="wss", mqtt_host="172.17.0.1")
    return parser


def main():
    app = service.create_app(parser=create_parser())

    # Both tiltScanner and event handling requires the task scheduler
    scheduler.setup(app)

    # Initialize event handling
    mqtt.setup(app)

    # Initialize your feature
    tiltScanner.setup(app)

    # Add all default endpoints
    service.furnish(app)

    # service.run() will start serving clients async
    service.run(app)


if __name__ == "__main__":
    main()
