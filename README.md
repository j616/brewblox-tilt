# BrewBlox Service for the Tilt Hydrometer

The [Tilt hydrometer](https://tilthydrometer.com/) is a wireless hydrometer and thermometer used to gather live readings of specific gravity and temperature when brewing beer.

[BrewBlox](https://brewpi.com/) is a modular brewery control system design to work with the BrewPi controller.

This brewBlox service integrates the Tilt hydrometer into BrewBlox.

## Usage

### Install script

To automatically install a new Tilt, you can use the `install_tilt.py` script.
This will create the ./tilt directory, and edit your `docker-compose.yml` file.

In your BrewBlox directory, run the following commands:

```bash
curl -O https://raw.githubusercontent.com/j616/brewblox-tilt/develop/install_tilt.py
python3 ./install_tilt.py
```

### Or: Deploy the Tilt service on the BrewBlox stack

You need to add the service and set the eventbus port in your `docker-compose.yml` file.

```yaml
  tilt:
    image: j616s/brewblox-tilt:latest
    restart: unless-stopped
    privileged: true
    network_mode: host
    volumes:
        - ./tilt:/share
```

Finally, you'll have to bring up the new service using

```bash
brewblox-ctl up
```

### Add to your graphs

Once the Tilt service receives data from your Tilt(s), it should be available as graph metrics in BrewBlox.

### Calibration

Calibration is optional. While the Tilt provides a good indication of fermentation progress without calibration, it's values can be less accurate than a traditional hydrometer. With calibration its accuracy is approximately that of a traditional hydrometer. If you wish to use your Tilt for anything beyond simple tracking of fermentation progress (e.g. stepping temperatures at a given SG value) it is recommended you calibrate your Tilt.

To calibrate your Tilt, you first need to create a folder for the calibration files to be stored in. The recommended folder is `./tilt` in the BrewBlox directory. You can use other directories but you should change the volume parameter for the Tilt service in your docker compose file accordingly. You can create the `tilt` directory by running the following command in the BrewBlox directory:-

```bash
mkdir tilt
```

**NOTE:** It is recommended you create the `tilt` folder before launching the Tilt service for the first time. Failure to do so will result in the docker service creating the folder as root. If this happens, use `chown` to change the user and group ownership of the `tilt` folder to match the rest of the BrewBlox directory.

If you wish to calibrate your Specific Gravity readings, create a file called `SGCal.csv` in the `tilt` directory with lines of the form:-

```
<colour>, <uncalibrated_value>, <calibrated_value>
```

The uncalibrated values are the raw values from the Tilt. The calibrated values are those from a known good hydrometer or calculated when creating your calibration solution. Calibration solutions can be made by adding sugar/DME to water a little at a time to increase the SG of the solution. You can take readings using a hydrometer and the Tilt app as you go. You can include calibration values for multiple colours of Tilt in the calibration file. A typical calibration file would look something like this:-

```
black, 1.000, 1.001
black, 1.001, 1.002
black, 1.002, 1.003
black, 1.003, 1.004
red, 1.000, 1.010
red, 1.001, 1.011
red, 1.002, 1.012
red, 1.003, 1.013
red, 1.004, 1.014
```

You will need multiple calibration points. We recommend at least 6 distributed evenly across your typical gravity range for each Tilt. For example, if you usually brew with a starting gravity of 1.050, you may choose to calibrate at the values 1.000, 1.010, 1.020, 1.030, 1.040, 1.050, and 1.060. The more calibration points you have, the more accurate the calibrated values the service creates will be. Strange calibrated values from the service are an indication you have used too few or poorly distributed calibration values.

Calibration values for temperature are placed in a file called `tempCal.csv` in the `tilt` directory and have the same structure. Temperature values in the calibration file MUST be in Fahrenheit. The tempCal file can also contain calibration values for multiple Tilts. Again, it should contain at least 6 points distributed evenly across your typical range. A typical tempCal file would look like this:-

```
black,39,40
black,46,48
black,54,55
black,60,62
black,68,70
black,75,76
```

Calibrated values will be logged in BrewBlox separately to uncalibrated values. If you don't provide calibration values for a given colour of Tilt, only uncalibrated values will be logged. You don't need to calibrate both temperature and SG. If you only want to provide calibration values for SG, that works fine. Calibrated temp values would not be generated in this case but calibrate SG values would.

It is also recommended that you re-calibrate SG whenever you change your battery. Different batteries and different placements of the sled inside the Tilt can affect the calibration.

## Limitations

As the Tilt does not talk directly to the BrewPi controller, you cannot use your Tilt to control the temperature of your system. This service currently only allows you to log values from the Tilt. To control your BrewPi/BrewBlox setup you will need a BrewPi temperature sensor.

## Development

To get started:

Install deps & pyenv
```bash
sudo apt update -y
sudo apt install -y \
    libglib2.0-dev \
    libatlas3-base \
    python3-bluez \
    make \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    wget \
    curl \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libffi-dev \
    liblzma-dev \
    python-openssl \
    git
```

Install pyenv
```bash
curl https://pyenv.run | bash
```

Install Python 3.7
```bash
pyenv install 3.7.7
```
After installing, it may suggest to add initialization code to `~/.bashrc`. Do that.

Install Poetry
```bash
pip3 install --user poetry
```

Configure and install the environment used for this project.
__Run in the root of the cloned brewblox-tilt directory__
```bash
pyenv local 3.7.7
poetry install
```

During development, you need to have your environment activated. When it is activated, your terminal prompt is prefixed with (.venv).

Visual Studio code with suggested settings does this automatically whenever you open a .py file. If you prefer using a different editor, you can do it manually by running:
```bash
poetry shell
```

You can build a docker container for x86 using the following:

```bash
brewblox-dev localbuild
```

Or for ARM using the following:

```bash
brewblox-dev localbuild --arch arm
```

You can then run this container using the following:

```bash
docker run --net=host --privileged -v ~/brewblox/tilt:/share j616s/brewblox-tilt:local
```
