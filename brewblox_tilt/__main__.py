"""
Brewblox service for Tilt hydrometer
"""
from brewblox_service import events, scheduler, service

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

    return parser


def main():
    app = service.create_app(parser=create_parser())

    # Both tiltScanner and event handling requires the task scheduler
    scheduler.setup(app)

    # Initialize event handling
    events.setup(app)

    # Initialize your feature
    tiltScanner.setup(app)

    # Add all default endpoints
    service.furnish(app)

    # service.run() will start serving clients async
    service.run(app)


if __name__ == "__main__":
    main()
