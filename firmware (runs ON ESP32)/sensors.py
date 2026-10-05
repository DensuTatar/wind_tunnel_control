from config import DEMO_SENSOR_MODE


def read_air_speed():

    if DEMO_SENSOR_MODE:
        return 0.0

    # --------------------------------------------------------
    # TODO:
    # Read the actual air-speed sensor / flow module.
    #
    # This function should eventually:
    #
    # 1. Read sensor signal
    # 2. Convert ADC reading to voltage if required
    # 3. Apply calibration equation
    # 4. Return speed in m/s
    # set known wind-tunnel speed -> measure reference air speed -> record
    #sensor voltage -> repeat @ many speeds -> plot voltage vs air speed -> fit an equation 
    # put that equation in here. 
    # a hot-wire annemometer often follows this:
    # E^2 = A + BU^n
    # the constants A, B, and n are found experimentally from callibration.
    #then set it into the code
    # --------------------------------------------------------

    raise NotImplementedError(
        "Air-speed sensor not yet implemented"
    )


def read_pressure():

    if DEMO_SENSOR_MODE:
        return 0.0

    # --------------------------------------------------------
    # TODO:
    # Implement exact pressure sensor interface
    # and calibration.
    # pressure diff -> pressure sensor -> electrical output ->
    # ESP32 reads signal -> convert signal to pressure -> return pressure
    # might en up with a relation like delta p = aV + b, but ofc check
    # --------------------------------------------------------

    raise NotImplementedError(
        "Pressure sensor not yet implemented"
    )


def read_temperature():

    if DEMO_SENSOR_MODE:
        return 0.0

    # --------------------------------------------------------
    # TODO:
    # Implement exact temperature sensor interface
    # and calibration.
    # --------------------------------------------------------

    raise NotImplementedError(
        "Temperature sensor not yet implemented"
    )


def read_all():

    speed = read_air_speed()

    pressure = read_pressure()

    temperature = read_temperature()

    return (
        speed,
        pressure,
        temperature
    )